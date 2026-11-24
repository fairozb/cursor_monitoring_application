"""First-run admin bootstrap and local Jumpbox registration."""

from __future__ import annotations

import logging
import os
import socket

from app.db import (
    create_server,
    create_user,
    get_local_server,
    get_user_by_username,
    init_db,
    update_server_host,
    update_user_password,
)
from app.utils.security import hash_password

logger = logging.getLogger(__name__)

ADMIN_USERNAME = "admin"


def bootstrap_admin() -> None:
    """Ensure admin exists; create or reset password from ADMIN_PASSWORD only."""
    init_db()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    existing = get_user_by_username(ADMIN_USERNAME)

    if existing is None:
        if not password:
            raise RuntimeError(
                "ADMIN_PASSWORD environment variable is required to create the "
                "initial admin user. Set it before first launch (see .env.example)."
            )
        create_user(ADMIN_USERNAME, hash_password(password))
        logger.info(
            "Created initial admin user '%s' (password hash stored in SQLite).",
            ADMIN_USERNAME,
        )
        return

    if password:
        update_user_password(ADMIN_USERNAME, hash_password(password))
        logger.info(
            "Updated password hash for admin user '%s' from environment configuration.",
            ADMIN_USERNAME,
        )


def bootstrap_local_server() -> None:
    """Register the current Jumpbox as the default local monitored server."""
    init_db()
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except OSError:
        ip_address = "127.0.0.1"

    existing = get_local_server()
    display_name = f"Jumpbox ({hostname})"
    if existing is None:
        create_server(
            name=display_name,
            host=ip_address,
            server_type="local",
        )
        logger.info("Registered local Jumpbox server '%s'.", display_name)
    else:
        update_server_host(existing["id"], display_name, ip_address)
