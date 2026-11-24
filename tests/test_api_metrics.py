"""Authenticated metrics API tests."""


def test_metrics_unauthorized(client):
    response = client.get("/api/servers/metrics")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_servers_list_unauthorized(client):
    response = client.get("/api/servers")
    assert response.status_code == 401


def test_metrics_authorized_local_shape(auth_client):
    response = auth_client.get("/api/servers/metrics")
    assert response.status_code == 200
    payload = response.get_json()
    assert "servers" in payload
    assert len(payload["servers"]) >= 1
    local = next(s for s in payload["servers"] if s["server_type"] == "local")
    assert local["status"] == "online"
    assert "cpu_percent" in local
    assert "memory" in local
    assert "disk" in local
    assert "network" in local
    assert "listening_ports" in local
    assert "uptime_human" in local
    assert "load_average" in local
    assert local["hostname"]
    assert "ssh_key_path" not in local


def test_single_server_metrics(auth_client):
    listing = auth_client.get("/api/servers").get_json()["servers"]
    local = next(s for s in listing if s["server_type"] == "local")
    response = auth_client.get(f"/api/servers/{local['id']}/metrics")
    assert response.status_code == 200
    body = response.get_json()
    assert body["server_id"] == local["id"]
    assert body["status"] == "online"


def test_local_server_auto_registered(app):
    from app.db import get_local_server

    with app.app_context():
        local = get_local_server()
        assert local is not None
        assert local["server_type"] == "local"
