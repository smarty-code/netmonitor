import json
import socket
import time
from pathlib import Path

import pytest

from agent.models import ProcessStats
from agent.process_manager import ProcessManager
from agent.server import AgentServer
from agent.state import NetworkState


def _client_request(path: Path, payload: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        sock.connect(str(path))
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        raw = b""
        while b"\n" not in raw:
            chunk = sock.recv(4096)
            if not chunk:
                break
            raw += chunk
    return json.loads(raw.decode("utf-8"))


@pytest.fixture
def api_server(tmp_path):
    state = NetworkState()
    state.replace_processes(
        [
            ProcessStats(
                pid=4321,
                name="curl",
                command="/usr/bin/curl",
                download=2048,
                upload=512,
            )
        ]
    )
    server = AgentServer(state, ProcessManager(), path=tmp_path / "netmonitor.sock")
    server.start()
    for _ in range(50):
        if server.path.exists():
            break
        time.sleep(0.02)
    yield server, state
    server.stop()


def test_ping(api_server):
    server, _ = api_server
    response = _client_request(server.path, {"action": "ping", "id": 1})
    assert response["ok"] is True
    assert response["status"] == "ok"
    assert response["id"] == 1


def test_get_stats_and_processes(api_server):
    server, _ = api_server
    stats = _client_request(server.path, {"action": "get_stats"})
    assert stats["ok"] is True
    assert stats["total"]["download"] == 2048
    assert stats["processes"][0]["name"] == "curl"
    processes = _client_request(server.path, {"action": "get_processes"})
    assert processes["processes"][0]["pid"] == 4321


def test_get_process_missing(api_server):
    server, _ = api_server
    response = _client_request(server.path, {"action": "get_process", "pid": 1})
    assert response["ok"] is False
    assert response["error"] == "not_found"


def test_rejects_command_strings(api_server):
    server, _ = api_server
    response = _client_request(server.path, {"command": "kill 1234; rm -rf ~"})
    assert response["ok"] is False
    assert response["error"] == "invalid_request"


def test_unknown_action(api_server):
    server, _ = api_server
    response = _client_request(server.path, {"action": "explode"})
    assert response["error"] == "unknown_action"


def test_invalid_json(api_server):
    server, _ = api_server
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(server.path))
        sock.sendall(b"not-json\n")
        raw = sock.recv(4096)
    response = json.loads(raw.decode("utf-8"))
    assert response["error"] == "invalid_json"


def test_kill_invalid_pid(api_server):
    server, _ = api_server
    response = _client_request(server.path, {"action": "kill_process", "pid": "nope"})
    assert response["ok"] is False
    assert response["error"] == "invalid_pid"


def test_rebind_after_socket_file_removed(api_server):
    server, _ = api_server
    server.path.unlink()
    deadline = time.time() + 2
    while time.time() < deadline:
        if server.path.exists():
            break
        time.sleep(0.05)
    assert server.path.exists()
    response = _client_request(server.path, {"action": "ping"})
    assert response["ok"] is True
