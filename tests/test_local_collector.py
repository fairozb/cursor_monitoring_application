"""Unit tests for the read-only local psutil collector."""

from app.monitoring.local_collector import collect_local_metrics


REQUIRED_KEYS = {
    "status",
    "hostname",
    "ip_address",
    "os",
    "cpu_percent",
    "cpu_count",
    "memory",
    "disk",
    "network",
    "listening_ports",
    "uptime_seconds",
    "uptime_human",
    "load_average",
    "collected_at",
    "server_type",
}


def test_local_collector_returns_required_keys():
    metrics = collect_local_metrics(server_id=1, name="Jumpbox")
    assert REQUIRED_KEYS.issubset(metrics.keys())
    assert metrics["server_type"] == "local"
    assert metrics["simulated"] is False


def test_local_collector_online_numeric_values():
    metrics = collect_local_metrics(server_id=1, name="Jumpbox")
    assert metrics["status"] == "online"
    assert metrics["error"] is None
    assert isinstance(metrics["cpu_percent"], (int, float))
    assert 0 <= metrics["cpu_percent"] <= 100
    assert isinstance(metrics["cpu_count"], int)
    assert metrics["cpu_count"] >= 1
    assert isinstance(metrics["memory"]["percent"], (int, float))
    assert isinstance(metrics["disk"]["percent"], (int, float))
    assert isinstance(metrics["uptime_seconds"], int)
    assert isinstance(metrics["listening_ports"], list)
    assert "1m" in metrics["load_average"]
    assert metrics["hostname"]
    assert metrics["ip_address"]
    assert metrics["os"]["pretty"]


def test_local_collector_does_not_raise():
    # Smoke: multiple collections for throughput delta path
    collect_local_metrics()
    second = collect_local_metrics()
    assert "network" in second
    assert "bytes_sent_per_sec" in second["network"]
