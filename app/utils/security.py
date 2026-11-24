"""Password hashing and session login helpers."""

from __future__ import annotations

from functools import wraps

from flask import jsonify, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    """Return a Werkzeug secure password hash."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return check_password_hash(password_hash, password)


def login_user(user_id: int, username: str) -> None:
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session.permanent = False


def logout_user() -> None:
    session.clear()


def current_username() -> str | None:
    return session.get("username")


def login_required(view):
    """Redirect anonymous users to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def api_login_required(view):
    """Return JSON 401 for unauthenticated API callers."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped

