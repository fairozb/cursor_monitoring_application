"""Main UI routes (authentication required for monitoring views)."""

from flask import Blueprint, render_template

from app.db import get_local_server
from app.utils.security import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    """Grafana-style dashboard — live values loaded via authenticated API + JS."""
    local = get_local_server()
    return render_template(
        "dashboard.html",
        local_server_id=local["id"] if local else None,
        local_server_name=local["name"] if local else "Jumpbox",
    )
