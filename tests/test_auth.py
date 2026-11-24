"""Unit tests for admin sign-in, sessions, and password hashing."""

import sqlite3

from app.utils.security import hash_password, verify_password


def test_password_hash_verify_succeeds():
    hashed = hash_password("correct-horse")
    assert hashed != "correct-horse"
    assert verify_password(hashed, "correct-horse") is True


def test_password_hash_verify_fails():
    hashed = hash_password("correct-horse")
    assert verify_password(hashed, "wrong-password") is False


def test_login_success_sets_session(client, csrf_token):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "test-admin-password",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert sess.get("username") == "admin"
        assert sess.get("user_id") is not None


def test_login_invalid_password_does_not_set_session(client, csrf_token):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "not-the-password",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_login_invalid_username(client, csrf_token):
    response = client.post(
        "/login",
        data={
            "username": "notadmin",
            "password": "test-admin-password",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_unauthorized_dashboard_redirects(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(auth_client, app):
    # Need fresh CSRF after login page flow — get dashboard then logout with token
    dash = auth_client.get("/")
    html = dash.get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    token = html[start:end]

    response = auth_client.post(
        "/logout",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with auth_client.session_transaction() as sess:
        assert sess.get("user_id") is None

    blocked = auth_client.get("/", follow_redirects=False)
    assert blocked.status_code == 302


def test_password_stored_as_hash_in_sqlite(app):
    db_path = app.config["DATABASE_PATH"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT username, password_hash FROM users WHERE username = ?",
        ("admin",),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["username"] == "admin"
    assert row["password_hash"] != "test-admin-password"
    assert row["password_hash"].startswith("scrypt:") or row["password_hash"].startswith(
        "pbkdf2:"
    )
    assert verify_password(row["password_hash"], "test-admin-password")


def test_login_requires_csrf(client):
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "test-admin-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_session_cookie_flags(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_admin_not_duplicated_on_second_boot(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")
    from app import config as config_module

    db_path = tmp_path / "once.db"
    monkeypatch.setattr(config_module.Config, "SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setattr(config_module.Config, "DATABASE_PATH", str(db_path))

    from app import create_app

    create_app()
    create_app()

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'").fetchone()[0]
    conn.close()
    assert count == 1
