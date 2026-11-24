"""Pytest fixtures for the demo monitoring app."""

import os

import pytest

# Must be set before app import/config side effects in each test process
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")

    # Re-resolve config values that were read at import time
    from app import config as config_module

    monkeypatch.setattr(config_module.Config, "SECRET_KEY", "test-secret-key-not-for-production")
    db_path = tmp_path / "test_monitor.db"
    monkeypatch.setattr(config_module.Config, "DATABASE_PATH", str(db_path))

    from app import create_app

    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "WTF_CSRF_ENABLED": True,
        }
    )
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_token(client):
    """Fetch a CSRF token from the login page."""
    response = client.get("/login")
    html = response.get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    end = html.index('"', start)
    return html[start:end]


@pytest.fixture
def auth_client(client, csrf_token):
    """Authenticated test client logged in as admin."""
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
    return client
