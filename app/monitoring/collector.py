"""Dispatch metric collection by server type."""

from __future__ import annotations

from typing import Any

from app.monitoring.local_collector import collect_local_metrics


def collect_for_server(server) -> dict[str, Any]:
    """Collect metrics for a servers table row."""
    server_type = server["server_type"]
    server_id = server["id"]
    name = server["name"]

    if server_type == "local":
        return collect_local_metrics(server_id=server_id, name=name)

    return {
        "server_id": server_id,
        "name": name,
        "server_type": server_type,
        "status": "offline",
        "error": f"Collector for type '{server_type}' is not implemented yet",
        "simulated": False,
        "listening_ports": [],
        "collected_at": None,
    }
