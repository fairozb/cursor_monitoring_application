"""Simulated Linux metrics for training labs. No SSH or system changes."""

from __future__ import annotations

import time
from typing import Any

from app.monitoring.local_collector import _format_bytes, _format_rate, _format_uptime
from app.monitoring.payloads import collected_now


def collect_demo_metrics(server_id: int | None, name: str, host: str | None = None) -> dict[str, Any]:
    """Return plausible changing metrics clearly marked as simulated."""
    tick = int(time.time() // 10)
    seed = sum(ord(ch) for ch in name) % 17
    cpu = round(15 + ((seed * 3 + tick) % 60) + (seed % 5) * 0.1, 1)
    mem_pct = round(35 + ((seed + tick * 2) % 40), 1)
    disk_pct = round(20 + (seed % 25) + (tick % 3), 1)
    mem_total = 8 * 1024**3
    mem_used = int(mem_total * mem_pct / 100)
    disk_total = 100 * 1024**3
    disk_used = int(disk_total * disk_pct / 100)
    uptime = 86400 * (3 + seed % 10) + tick * 10
    upload_bps = float(50_000 + (tick % 20) * 1000 + seed * 100)
    download_bps = float(120_000 + (tick % 15) * 2000)
    return {
        "server_id": server_id,
        "name": name,
        "server_type": "demo",
        "simulated": True,
        "status": "online",
        "error": None,
        "hostname": name.lower().replace(" ", "-"),
        "ip_address": host or "10.0.0.10",
        "os": {
            "system": "Linux",
            "release": "simulated",
            "version": "simulated",
            "pretty": "Linux simulated",
        },
        "cpu_percent": cpu,
        "cpu_count": 4,
        "memory": {
            "total": mem_total,
            "used": mem_used,
            "available": mem_total - mem_used,
            "percent": mem_pct,
            "total_human": _format_bytes(mem_total),
            "used_human": _format_bytes(mem_used),
            "available_human": _format_bytes(mem_total - mem_used),
        },
        "disk": {
            "total": disk_total,
            "used": disk_used,
            "available": disk_total - disk_used,
            "percent": disk_pct,
            "total_human": _format_bytes(disk_total),
            "used_human": _format_bytes(disk_used),
            "available_human": _format_bytes(disk_total - disk_used),
            "mount": "/",
        },
        "network": {
            "bytes_sent": int(upload_bps * 100),
            "bytes_recv": int(download_bps * 100),
            "bytes_sent_per_sec": upload_bps,
            "bytes_recv_per_sec": download_bps,
            "upload": _format_rate(upload_bps),
            "download": _format_rate(download_bps),
        },
        "listening_ports": [
            {"port": 22, "proto": "tcp", "status": "LISTEN"},
            {"port": 80, "proto": "tcp", "status": "LISTEN"},
            {"port": 443, "proto": "tcp", "status": "LISTEN"},
        ],
        "uptime_seconds": uptime,
        "uptime_human": _format_uptime(uptime),
        "load_average": {"1m": round(cpu / 100, 2), "5m": 0.4, "15m": 0.3},
        "collected_at": collected_now(),
    }
