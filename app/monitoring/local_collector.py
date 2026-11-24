"""Read-only local Linux metrics via psutil (no root/sudo required)."""

from __future__ import annotations

import platform
import socket
import time
from datetime import datetime, timezone
from typing import Any

import psutil

# Module-level cache for network throughput (bytes/sec)
_prev_net: dict[str, float] | None = None


def _primary_ip() -> str:
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass

    for _iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                return addr.address
    return "127.0.0.1"


def _format_bytes(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num:.0f} B"


def _format_rate(bytes_per_sec: float) -> str:
    return f"{_format_bytes(bytes_per_sec)}/s"


def _format_uptime(seconds: float) -> str:
    secs = int(seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _listening_ports() -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return ports

    for conn in connections:
        if conn.status != psutil.CONN_LISTEN or not conn.laddr:
            continue
        port = int(conn.laddr.port)
        proto = "tcp" if conn.type == socket.SOCK_STREAM else "udp"
        key = (proto, port)
        if key in seen:
            continue
        seen.add(key)
        ports.append({"port": port, "proto": proto, "status": "LISTEN"})

    ports.sort(key=lambda item: (item["proto"], item["port"]))
    return ports


def _network_throughput() -> dict[str, Any]:
    global _prev_net
    counters = psutil.net_io_counters()
    now = time.monotonic()
    sent_rate = 0.0
    recv_rate = 0.0

    if _prev_net is not None:
        elapsed = max(now - _prev_net["ts"], 0.001)
        sent_rate = max(0.0, (counters.bytes_sent - _prev_net["sent"]) / elapsed)
        recv_rate = max(0.0, (counters.bytes_recv - _prev_net["recv"]) / elapsed)

    _prev_net = {
        "ts": now,
        "sent": float(counters.bytes_sent),
        "recv": float(counters.bytes_recv),
    }

    return {
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
        "bytes_sent_per_sec": round(sent_rate, 2),
        "bytes_recv_per_sec": round(recv_rate, 2),
        "upload": _format_rate(sent_rate),
        "download": _format_rate(recv_rate),
    }


def collect_local_metrics(server_id: int | None = None, name: str | None = None) -> dict[str, Any]:
    """
    Collect read-only local metrics.
    On success status is online; on failure returns offline with error (never raises to caller).
    """
    collected_at = datetime.now(timezone.utc).isoformat()
    base = {
        "server_id": server_id,
        "name": name or socket.gethostname(),
        "server_type": "local",
        "simulated": False,
        "collected_at": collected_at,
    }

    try:
        # Short interval for a usable first sample without long blocking
        cpu_percent = float(psutil.cpu_percent(interval=0.1))
        cpu_count = int(psutil.cpu_count(logical=True) or 0)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = psutil.boot_time()
        uptime_seconds = max(0.0, time.time() - boot)
        try:
            load_1, load_5, load_15 = os_getloadavg()
        except OSError:
            load_1 = load_5 = load_15 = 0.0

        network = _network_throughput()
        ports = _listening_ports()
        hostname = socket.gethostname()
        ip_address = _primary_ip()

        return {
            **base,
            "status": "online",
            "error": None,
            "hostname": hostname,
            "ip_address": ip_address,
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "pretty": f"{platform.system()} {platform.release()}",
            },
            "cpu_percent": round(cpu_percent, 1),
            "cpu_count": cpu_count,
            "memory": {
                "total": mem.total,
                "used": mem.used,
                "available": mem.available,
                "percent": round(float(mem.percent), 1),
                "total_human": _format_bytes(mem.total),
                "used_human": _format_bytes(mem.used),
                "available_human": _format_bytes(mem.available),
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "available": disk.free,
                "percent": round(float(disk.percent), 1),
                "total_human": _format_bytes(disk.total),
                "used_human": _format_bytes(disk.used),
                "available_human": _format_bytes(disk.free),
                "mount": "/",
            },
            "network": network,
            "listening_ports": ports,
            "uptime_seconds": int(uptime_seconds),
            "uptime_human": _format_uptime(uptime_seconds),
            "load_average": {
                "1m": round(load_1, 2),
                "5m": round(load_5, 2),
                "15m": round(load_15, 2),
            },
        }
    except Exception as exc:  # noqa: BLE001 — convert to offline payload for dashboard
        return {
            **base,
            "status": "offline",
            "error": "Failed to collect local metrics",
            "hostname": socket.gethostname(),
            "ip_address": None,
            "os": None,
            "cpu_percent": None,
            "cpu_count": None,
            "memory": None,
            "disk": None,
            "network": None,
            "listening_ports": [],
            "uptime_seconds": None,
            "uptime_human": None,
            "load_average": None,
            "detail": str(exc.__class__.__name__),
        }


def os_getloadavg() -> tuple[float, float, float]:
    """Indirection for easier unit testing."""
    return os_loadavg_impl()


def os_loadavg_impl() -> tuple[float, float, float]:
    import os

    return os.getloadavg()
