"""Authenticated JSON metrics API."""

from flask import Blueprint, jsonify

from app.db import get_server, list_servers
from app.monitoring.collector import collect_for_server
from app.utils.security import api_login_required

bp = Blueprint("api", __name__, url_prefix="/api")


def _server_public(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "host": row["host"],
        "server_type": row["server_type"],
        "enabled": bool(row["enabled"]),
    }


@bp.get("/servers")
@api_login_required
def api_servers():
    servers = [_server_public(row) for row in list_servers(enabled_only=True)]
    return jsonify({"servers": servers})


@bp.get("/servers/metrics")
@api_login_required
def api_all_metrics():
    results = [collect_for_server(row) for row in list_servers(enabled_only=True)]
    return jsonify({"servers": results})


@bp.get("/servers/<int:server_id>/metrics")
@api_login_required
def api_server_metrics(server_id: int):
    server = get_server(server_id)
    if server is None or not server["enabled"]:
        return jsonify({"error": "not_found"}), 404
    return jsonify(collect_for_server(server))
