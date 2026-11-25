"""Read-only remote Linux metrics over SSH (key auth, host key checks, timeouts)."""

from __future__ import annotations

import os
import socket
from typing import Any

import paramiko

from app.config import ssh_command_timeout, ssh_connect_timeout
from app.monitoring.local_collector import _format_bytes, _format_rate, _format_uptime
from app.monitoring.payloads import collected_now, offline_payload

# Read-only remote probe. No writes, no package installs, no service changes.
READ_ONLY_SCRIPT = r"""
hostname
printf '\n__SEP__\n'
uname -sr
printf '\n__SEP__\n'
awk '{print $1}' /proc/uptime
printf '\n__SEP__\n'
awk '{print $1,$2,$3}' /proc/loadavg
printf '\n__SEP__\n'
nproc
printf '\n__SEP__\n'
free -b | awk '/^Mem:/ {print $2,$3,$7}'
printf '\n__SEP__\n'
df -B1 / | awk 'NR==2 {print $2,$3,$4}'
printf '\n__SEP__\n'
awk '/^cpu /{print $2,$3,$4,$5,$6,$7,$8; exit}' /proc/stat
sleep 0.2
awk '/^cpu /{print $2,$3,$4,$5,$6,$7,$8; exit}' /proc/stat
printf '\n__SEP__\n'
awk 'NR>2 {rx+=$2; tx+=$10} END {print tx+0, rx+0}' /proc/net/dev
printf '\n__SEP__\n'
ss -lntuH 2>/dev/null || true
"""

_prev_net: dict[int, tuple[float, float]] = {}


def _cpu_percent(first: str, second: str) -> float:
    def parts(line: str) -> list[int]:
        return [int(x) for x in line.split()]

    a = parts(first)
    b = parts(second)
    if len(a) < 4 or len(b) < 4:
        return 0.0
    idle_a, idle_b = a[3], b[3]
    total_a, total_b = sum(a), sum(b)
    total_d = total_b - total_a
    idle_d = idle_b - idle_a
    if total_d <= 0:
        return 0.0
    return round(max(0.0, min(100.0, 100.0 * (1.0 - idle_d / total_d))), 1)


def _ports(blob: str) -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for line in blob.splitlines():
        bits = line.split()
        if len(bits) < 5:
            continue
        proto = bits[0].lower()
        if "tcp" not in proto and "udp" not in proto:
            continue
        if "tcp" in proto and "LISTEN" not in line.upper():
            continue
        address = bits[4] if "tcp" in proto else bits[4]
        port_txt = address.rsplit(":", 1)[-1]
        try:
            port = int(port_txt)
        except ValueError:
            continue
        kind = "udp" if proto.startswith("udp") else "tcp"
        key = (kind, port)
        if key in seen:
            continue
        seen.add(key)
        ports.append({"port": port, "proto": kind, "status": "LISTEN"})
    ports.sort(key=lambda item: (item["proto"], item["port"]))
    return ports


def parse_remote_output(
    text: str,
    *,
    server_id: int | None,
    name: str,
    host: str,
) -> dict[str, Any]:
    parts = [p.strip() for p in text.split("__SEP__")]
    if len(parts) < 10:
        raise ValueError("incomplete remote output")

    hostname, os_pretty, uptime_raw, load_raw, nproc_raw = parts[:5]
    mem_raw, disk_raw, cpu_raw, net_raw, ports_raw = parts[5:10]
    uptime_seconds = float(uptime_raw.split()[0])
    load_bits = load_raw.split()
    mem_bits = mem_raw.split()
    disk_bits = disk_raw.split()
    cpu_lines = [ln for ln in cpu_raw.splitlines() if ln.strip()]
    net_bits = net_raw.split()
    mem_total, mem_used, mem_avail = (int(mem_bits[0]), int(mem_bits[1]), int(mem_bits[2]))
    disk_total, disk_used, disk_avail = (int(disk_bits[0]), int(disk_bits[1]), int(disk_bits[2]))
    mem_pct = round(100.0 * mem_used / mem_total, 1) if mem_total else 0.0
    disk_pct = round(100.0 * disk_used / disk_total, 1) if disk_total else 0.0
    cpu = _cpu_percent(cpu_lines[0], cpu_lines[1]) if len(cpu_lines) >= 2 else 0.0
    sent = float(net_bits[0]) if net_bits else 0.0
    recv = float(net_bits[1]) if len(net_bits) > 1 else 0.0
    sent_rate = recv_rate = 0.0
    if server_id is not None and server_id in _prev_net:
        prev_sent, prev_recv = _prev_net[server_id]
        sent_rate = max(0.0, sent - prev_sent)
        recv_rate = max(0.0, recv - prev_recv)
    if server_id is not None:
        _prev_net[server_id] = (sent, recv)

    return {
        "server_id": server_id,
        "name": name,
        "server_type": "remote",
        "simulated": False,
        "status": "online",
        "error": None,
        "hostname": hostname or host,
        "ip_address": host,
        "os": {"system": "Linux", "release": os_pretty, "version": os_pretty, "pretty": os_pretty},
        "cpu_percent": cpu,
        "cpu_count": int(nproc_raw),
        "memory": {
            "total": mem_total,
            "used": mem_used,
            "available": mem_avail,
            "percent": mem_pct,
            "total_human": _format_bytes(mem_total),
            "used_human": _format_bytes(mem_used),
            "available_human": _format_bytes(mem_avail),
        },
        "disk": {
            "total": disk_total,
            "used": disk_used,
            "available": disk_avail,
            "percent": disk_pct,
            "total_human": _format_bytes(disk_total),
            "used_human": _format_bytes(disk_used),
            "available_human": _format_bytes(disk_avail),
            "mount": "/",
        },
        "network": {
            "bytes_sent": int(sent),
            "bytes_recv": int(recv),
            "bytes_sent_per_sec": round(sent_rate, 2),
            "bytes_recv_per_sec": round(recv_rate, 2),
            "upload": _format_rate(sent_rate),
            "download": _format_rate(recv_rate),
        },
        "listening_ports": _ports(ports_raw),
        "uptime_seconds": int(uptime_seconds),
        "uptime_human": _format_uptime(uptime_seconds),
        "load_average": {
            "1m": round(float(load_bits[0]), 2),
            "5m": round(float(load_bits[1]), 2),
            "15m": round(float(load_bits[2]), 2),
        },
        "collected_at": collected_now(),
    }


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "SSH connection timed out"
    if isinstance(exc, paramiko.BadHostKeyException):
        return "Host key verification failed"
    text = str(exc).lower()
    if "known_hosts" in text or "host key" in text:
        return "Host key verification failed"
    if "timed out" in text or "timeout" in text:
        return "SSH connection timed out"
    if "authentication" in text:
        return "SSH authentication failed"
    return "SSH connection failed"


def collect_remote_metrics(server) -> dict[str, Any]:
    """Collect metrics with key-based SSH only. Never uses password authentication."""
    server_id = server["id"]
    name = server["name"]
    host = (server["host"] or "").strip()
    username = (server["ssh_username"] or "").strip()
    key_path = (server["ssh_key_path"] or "").strip()
    port = int(server["ssh_port"] or 22)

    if not host or not username or not key_path:
        return offline_payload(
            server_id=server_id,
            name=name,
            server_type="remote",
            error="SSH host, username, and key path are required",
            hostname=host or None,
            ip_address=host or None,
        )
    if not os.path.isfile(os.path.expanduser(key_path)):
        return offline_payload(
            server_id=server_id,
            name=name,
            server_type="remote",
            error="SSH private key file is missing",
            hostname=host,
            ip_address=host,
        )

    client = paramiko.SSHClient()
    try:
        client.load_system_host_keys()
        known_hosts = os.path.expanduser(os.environ.get("SSH_KNOWN_HOSTS", "~/.ssh/known_hosts"))
        if os.path.isfile(known_hosts):
            client.load_host_keys(known_hosts)
        # Reject unknown or changed host keys. Do not use AutoAddPolicy.
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        connect_timeout = ssh_connect_timeout()
        client.connect(
            hostname=host,
            port=port,
            username=username,
            key_filename=os.path.expanduser(key_path),
            look_for_keys=False,
            allow_agent=False,
            timeout=connect_timeout,
            banner_timeout=connect_timeout,
            auth_timeout=connect_timeout,
        )
        _stdin, stdout, _stderr = client.exec_command(
            READ_ONLY_SCRIPT,
            timeout=ssh_command_timeout(),
        )
        text = stdout.read().decode("utf-8", errors="replace")
        return parse_remote_output(text, server_id=server_id, name=name, host=host)
    except Exception as exc:  # noqa: BLE001 — mapped to a short offline reason
        return offline_payload(
            server_id=server_id,
            name=name,
            server_type="remote",
            error=_safe_error(exc),
            hostname=host,
            ip_address=host,
        )
    finally:
        client.close()
