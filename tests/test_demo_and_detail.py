"""Demo mode, server detail, and mixed offline results."""

import os

from app.monitoring.demo_collector import collect_demo_metrics


def test_demo_metrics_are_labelled():
    metrics = collect_demo_metrics(3, "Simulated-Web-01", "10.0.0.11")
    assert metrics["simulated"] is True
    assert metrics["server_type"] == "demo"
    assert metrics["status"] == "online"
    assert metrics["name"].startswith("Simulated-")


def test_demo_mode_seeds_servers(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("DEMO_MODE", "true")
    from app import config as config_module

    db_path = tmp_path / "demo.db"
    monkeypatch.setattr(config_module.Config, "SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setattr(config_module.Config, "DATABASE_PATH", str(db_path))
    from app import create_app

    app = create_app()
    from app.db import list_servers

    with app.app_context():
        rows = list_servers()
    types = {row["server_type"] for row in rows}
    names = {row["name"] for row in rows}
    assert "local" in types
    assert "demo" in types
    assert "Simulated-Web-01" in names
    assert 3 <= len(rows) <= 5


def test_detail_requires_login(client):
    blocked = client.get("/servers/1")
    assert blocked.status_code == 302
    assert "/login" in blocked.headers["Location"]


def test_detail_page_and_unknown_id(auth_client):
    missing = auth_client.get("/servers/99999")
    assert missing.status_code == 404
    listing = auth_client.get("/api/servers").get_json()["servers"]
    local = next(s for s in listing if s["server_type"] == "local")
    page = auth_client.get(f"/servers/{local['id']}")
    assert page.status_code == 200
    assert b"Refresh now" in page.data
    assert b"Listening ports" in page.data


def test_aggregate_keeps_going_when_one_host_fails(auth_client):
    from app.db import create_server

    with auth_client.application.app_context():
        create_server(
            name="Unreachable-01",
            host="10.255.255.1",
            server_type="remote",
            ssh_username="monitor",
            ssh_key_path="/tmp/does-not-exist-key",
        )
    response = auth_client.get("/api/servers/metrics")
    assert response.status_code == 200
    servers = response.get_json()["servers"]
    local = next(s for s in servers if s["server_type"] == "local")
    remote = next(s for s in servers if s["name"] == "Unreachable-01")
    assert local["status"] == "online"
    assert remote["status"] == "offline"
    assert remote["error"]
    assert "does-not-exist" not in remote["error"]
    assert os.environ.get("ADMIN_PASSWORD")
