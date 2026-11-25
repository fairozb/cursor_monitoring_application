"""SQLite helpers for the demo monitoring application."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        path = current_app.config["DATABASE_PATH"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(_e=None) -> None:
    """Close the request-scoped connection."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT,
            ssh_port INTEGER DEFAULT 22,
            ssh_username TEXT,
            ssh_key_path TEXT,
            server_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def create_user(username: str, password_hash: str) -> None:
    db = get_db()
    created_at = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, created_at),
    )
    db.commit()


def update_user_password(username: str, password_hash: str) -> None:
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (password_hash, username),
    )
    db.commit()


def list_servers(enabled_only: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM servers"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY id ASC"
    return get_db().execute(sql).fetchall()


def get_server(server_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM servers WHERE id = ?",
        (server_id,),
    ).fetchone()


def get_local_server() -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM servers WHERE server_type = 'local' LIMIT 1",
    ).fetchone()


def create_server(
    *,
    name: str,
    host: str | None,
    server_type: str,
    ssh_port: int = 22,
    ssh_username: str | None = None,
    ssh_key_path: str | None = None,
    enabled: int = 1,
) -> int:
    db = get_db()
    created_at = datetime.now(timezone.utc).isoformat()
    cur = db.execute(
        """
        INSERT INTO servers (
            name, host, ssh_port, ssh_username, ssh_key_path, server_type, enabled, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, host, ssh_port, ssh_username, ssh_key_path, server_type, enabled, created_at),
    )
    db.commit()
    return int(cur.lastrowid)


def update_server_host(server_id: int, name: str, host: str | None) -> None:
    db = get_db()
    db.execute(
        "UPDATE servers SET name = ?, host = ? WHERE id = ?",
        (name, host, server_id),
    )
    db.commit()


def count_servers() -> int:
    row = get_db().execute("SELECT COUNT(*) AS n FROM servers").fetchone()
    return int(row["n"])


def get_server_by_name(name: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM servers WHERE name = ?",
        (name,),
    ).fetchone()


def delete_server(server_id: int) -> int:
    db = get_db()
    cur = db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    db.commit()
    return int(cur.rowcount)
