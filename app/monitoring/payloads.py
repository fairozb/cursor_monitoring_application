"""Shared metric payload helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def collected_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def offline_payload(
    *,
    server_id: int | None,
    name: str,
    server_type: str,
    error: str,
    simulated: bool = False,
    hostname: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Structured offline result. Error text must not include secrets or key material."""
    return {
        "server_id": server_id,
        "name": name,
        "server_type": server_type,
        "simulated": simulated,
        "status": "offline",
        "error": error,
        "hostname": hostname,
        "ip_address": ip_address,
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
        "collected_at": collected_now(),
    }
