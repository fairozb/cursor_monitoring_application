"""Dispatch metric collection by server type."""

from __future__ import annotations

import logging
from typing import Any

from app.monitoring.demo_collector import collect_demo_metrics
from app.monitoring.local_collector import collect_local_metrics
from app.monitoring.payloads import offline_payload
from app.monitoring.remote_collector import collect_remote_metrics

logger = logging.getLogger(__name__)


def collect_for_server(server) -> dict[str, Any]:
    """Collect metrics for a servers table row. One failure stays on that host."""
    server_type = server["server_type"]
    server_id = server["id"]
    name = server["name"]
    try:
        if server_type == "local":
            return collect_local_metrics(server_id=server_id, name=name)
        if server_type == "remote":
            return collect_remote_metrics(server)
        if server_type == "demo":
            return collect_demo_metrics(server_id, name, server["host"])
        return offline_payload(
            server_id=server_id,
            name=name,
            server_type=server_type,
            error="Unsupported server type",
        )
    except Exception:
        logger.warning("Metric collection failed for server id %s", server_id)
        return offline_payload(
            server_id=server_id,
            name=name,
            server_type=server_type,
            error="Failed to collect metrics",
        )
