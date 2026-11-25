"""Inventory add/remove, CSRF, and session protection."""


def _token(html: str) -> str:
    marker = 'name="csrf_token" value="'
    start = html.index(marker) + len(marker)
    return html[start : html.index('"', start)]


def test_inventory_requires_login(client):
    response = client.get("/inventory")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_and_delete_server(auth_client):
    page = auth_client.get("/inventory")
    token = _token(page.get_data(as_text=True))
    added = auth_client.post(
        "/inventory",
        data={
            "csrf_token": token,
            "name": "Lab-Remote-01",
            "server_type": "remote",
            "host": "10.1.1.10",
            "ssh_port": "22",
            "ssh_username": "monitor",
            "ssh_key_path": "/tmp/lab_demo_key",
        },
        follow_redirects=True,
    )
    assert added.status_code == 200
    assert b"Lab-Remote-01" in added.data

    from app.db import get_server_by_name

    with auth_client.application.app_context():
        row = get_server_by_name("Lab-Remote-01")
        assert row is not None
        assert row["ssh_key_path"] == "/tmp/lab_demo_key"
        server_id = row["id"]

    page = auth_client.get("/inventory")
    token = _token(page.get_data(as_text=True))
    removed = auth_client.post(
        f"/inventory/{server_id}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert removed.status_code == 200
    with auth_client.application.app_context():
        assert get_server_by_name("Lab-Remote-01") is None


def test_add_without_csrf_fails(auth_client):
    response = auth_client.post(
        "/inventory",
        data={
            "name": "No-CSRF",
            "server_type": "demo",
            "host": "10.1.1.11",
        },
    )
    assert response.status_code == 400


def test_soft_cap_at_five(auth_client):
    from app.db import count_servers, create_server

    with auth_client.application.app_context():
        while count_servers() < 5:
            create_server(
                name=f"Fill-{count_servers()}",
                host="10.9.9.9",
                server_type="demo",
            )
    page = auth_client.get("/inventory")
    token = _token(page.get_data(as_text=True))
    response = auth_client.post(
        "/inventory",
        data={
            "csrf_token": token,
            "name": "One-Too-Many",
            "server_type": "demo",
            "host": "10.9.9.8",
        },
        follow_redirects=True,
    )
    assert b"limited to 5" in response.data
    with auth_client.application.app_context():
        assert count_servers() == 5
