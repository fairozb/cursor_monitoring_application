"""Remote collector tests using a fake SSH client (no live SSH)."""

import socket

import paramiko

from app.monitoring.remote_collector import (
    READ_ONLY_SCRIPT,
    collect_remote_metrics,
    parse_remote_output,
)

SAMPLE = """
jumpbox
__SEP__
Linux 6.8.0
__SEP__
3600.5
__SEP__
0.10 0.20 0.30
__SEP__
4
__SEP__
8000000000 2000000000 6000000000
__SEP__
100000000000 25000000000 75000000000
__SEP__
100 0 0 900 0 0 0
110 0 10 900 0 0 0
__SEP__
1000 4000
__SEP__
tcp LISTEN 0 128 0.0.0.0:22
"""


class FakeStdout:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text.encode()


class FakeClient:
    def __init__(self, fail=None):
        self.fail = fail
        self.policy = None
        self.kwargs = None
        self.closed = False

    def load_system_host_keys(self):
        return None

    def load_host_keys(self, _path):
        return None

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.kwargs = kwargs
        if self.fail:
            raise self.fail

    def exec_command(self, _cmd, timeout=None):
        return None, FakeStdout(SAMPLE), FakeStdout("")

    def close(self):
        self.closed = True


def _server(tmp_path, host="10.1.1.8"):
    key = tmp_path / "id_demo"
    key.write_text("not-a-real-key\n")
    return {
        "id": 7,
        "name": "Remote-1",
        "host": host,
        "ssh_port": 22,
        "ssh_username": "monitor",
        "ssh_key_path": str(key),
        "server_type": "remote",
    }


def test_parse_remote_output_shape():
    metrics = parse_remote_output(SAMPLE, server_id=7, name="Remote-1", host="10.1.1.8")
    assert metrics["status"] == "online"
    assert metrics["server_type"] == "remote"
    assert metrics["hostname"] == "jumpbox"
    assert metrics["cpu_count"] == 4
    assert metrics["memory"]["percent"] > 0
    assert metrics["listening_ports"][0]["port"] == 22


def test_read_only_script_and_reject_policy(tmp_path, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(paramiko, "SSHClient", lambda: client)
    metrics = collect_remote_metrics(_server(tmp_path))
    assert metrics["status"] == "online"
    assert isinstance(client.policy, paramiko.RejectPolicy)
    assert "password" not in client.kwargs
    assert client.kwargs["look_for_keys"] is False
    assert client.closed is True
    assert "rm " not in READ_ONLY_SCRIPT
    assert "chmod" not in READ_ONLY_SCRIPT


def test_timeout_is_offline(tmp_path, monkeypatch):
    client = FakeClient(fail=socket.timeout("timed out"))
    monkeypatch.setattr(paramiko, "SSHClient", lambda: client)
    metrics = collect_remote_metrics(_server(tmp_path, host="10.1.1.9"))
    assert metrics["status"] == "offline"
    assert metrics["error"] == "SSH connection timed out"
    assert client.closed is True


def test_host_key_failure_is_offline(tmp_path, monkeypatch):
    client = FakeClient(fail=paramiko.SSHException("not found in known_hosts"))
    monkeypatch.setattr(paramiko, "SSHClient", lambda: client)
    metrics = collect_remote_metrics(_server(tmp_path, host="10.1.1.7"))
    assert metrics["status"] == "offline"
    assert metrics["error"] == "Host key verification failed"


def test_missing_key_does_not_connect(tmp_path, monkeypatch):
    called = {"yes": False}

    def _boom():
        called["yes"] = True
        raise AssertionError("should not connect")

    monkeypatch.setattr(paramiko, "SSHClient", _boom)
    server = _server(tmp_path)
    server["ssh_key_path"] = str(tmp_path / "missing")
    metrics = collect_remote_metrics(server)
    assert metrics["status"] == "offline"
    assert "missing" in metrics["error"].lower()
    assert called["yes"] is False
    assert server["ssh_key_path"] not in metrics["error"]
