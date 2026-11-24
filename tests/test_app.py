"""Smoke tests for project initialization and basic UI."""


def test_create_app_returns_flask_app(app):
    assert app is not None
    assert app.name == "app"


def test_dashboard_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_renders_live_shell(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Infra Monitor" in html
    assert "Logout" in html
    assert "Refresh now" in html
    assert "chart-cpu" in html
    assert "/api/servers/metrics" in html
    assert "dashboard.js" in html


def test_static_css_available(client):
    response = client.get("/static/css/dashboard.css")
    assert response.status_code == 200
    assert b"--bg-canvas" in response.data


def test_dashboard_js_refresh_interval(client):
    response = client.get("/static/js/dashboard.js")
    assert response.status_code == 200
    assert b"10000" in response.data
