"""Server inventory management (session + CSRF)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import count_servers, create_server, delete_server, get_server, list_servers
from app.utils.security import login_required

bp = Blueprint("servers", __name__, url_prefix="/inventory")

MAX_SERVERS = 5


def _clean(value: str | None) -> str:
    return (value or "").strip()


@bp.route("", methods=["GET"])
@login_required
def manage():
    servers = list_servers()
    return render_template(
        "servers_manage.html",
        servers=servers,
        server_count=len(servers),
        max_servers=MAX_SERVERS,
    )


@bp.route("", methods=["POST"])
@login_required
def add():
    if count_servers() >= MAX_SERVERS:
        flash(f"Demo inventory is limited to {MAX_SERVERS} servers.", "warning")
        return redirect(url_for("servers.manage"))

    name = _clean(request.form.get("name"))
    server_type = _clean(request.form.get("server_type"))
    host = _clean(request.form.get("host"))
    username = _clean(request.form.get("ssh_username"))
    key_path = _clean(request.form.get("ssh_key_path"))
    port_raw = _clean(request.form.get("ssh_port")) or "22"

    if not name or server_type not in {"remote", "demo"}:
        flash("Name and a server type of remote or demo are required.", "warning")
        return redirect(url_for("servers.manage"))
    try:
        port = int(port_raw)
    except ValueError:
        port = 0
    if server_type == "remote":
        if not host or not username or not key_path or not (1 <= port <= 65535):
            flash("Remote servers need host, SSH port, username, and a key path.", "warning")
            return redirect(url_for("servers.manage"))
    elif not (1 <= port <= 65535):
        port = 22

    create_server(
        name=name,
        host=host or None,
        server_type=server_type,
        ssh_port=port,
        ssh_username=username or None,
        ssh_key_path=key_path or None,
    )
    flash(f"Added {name}.", "info")
    return redirect(url_for("servers.manage"))


@bp.route("/<int:server_id>/delete", methods=["POST"])
@login_required
def remove(server_id: int):
    server = get_server(server_id)
    if server is None:
        flash("Server was not found.", "warning")
        return redirect(url_for("servers.manage"))
    if server["server_type"] == "local":
        flash("The local Jumpbox stays in the inventory.", "warning")
        return redirect(url_for("servers.manage"))
    delete_server(server_id)
    flash(f"Removed {server['name']}.", "info")
    return redirect(url_for("servers.manage"))
