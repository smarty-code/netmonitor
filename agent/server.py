"""JSON Unix-socket API for the NetMonitor agent."""

from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path

from agent import config
from agent.logger import get_logger
from agent.process_manager import ProcessError, ProcessManager
from agent.state import NetworkState

VALID_ACTIONS = frozenset(
    {
        "ping",
        "get_stats",
        "get_processes",
        "get_process",
        "kill_process",
        "force_kill_process",
    }
)


class AgentServer:
    def __init__(
        self,
        state: NetworkState,
        process_manager: ProcessManager | None = None,
        path: Path | None = None,
    ) -> None:
        self._state = state
        self._processes = process_manager or ProcessManager()
        self._path = path or config.socket_path()
        self._log = get_logger("server")
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def path(self) -> Path:
        return self._path

    def start(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._bind()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._accept_loop, name="netmonitor-socket", daemon=True
        )
        self._thread.start()
        self._log.info("listening on %s", self._path)

    def _bind(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(self._path))
        os.chmod(self._path, 0o600)
        sock.listen(config.SOCKET_BACKLOG)
        sock.settimeout(0.5)
        self._sock = sock

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=3)
        if self._path.exists():
            try:
                self._path.unlink()
            except OSError:
                pass

    def handle_request(self, payload: dict) -> dict:
        action = payload.get("action")
        request_id = payload.get("id")
        if action not in VALID_ACTIONS:
            return self._error("unknown_action", "unknown action", request_id)
        try:
            body = self._dispatch(action, payload)
        except ProcessError as exc:
            return self._error(exc.code, exc.message, request_id)
        except Exception as exc:  # pragma: no cover - defensive
            self._log.exception("request failed")
            return self._error("internal", str(exc), request_id)
        body["ok"] = True
        if request_id is not None:
            body["id"] = request_id
        return body

    def _dispatch(self, action: str, payload: dict) -> dict:
        if action == "ping":
            return {"status": "ok"}
        if action == "get_stats":
            return self._state.snapshot().to_dict()
        if action == "get_processes":
            snapshot = self._state.snapshot()
            return {
                "timestamp": snapshot.timestamp,
                "processes": [proc.to_dict() for proc in snapshot.processes],
            }
        if action == "get_process":
            pid = payload.get("pid")
            proc = self._state.get_process(pid) if isinstance(pid, int) else None
            if proc is None:
                raise ProcessError("not_found", "process is not in the current snapshot")
            data = proc.to_dict()
            cmdline = self._processes.command_line(proc.pid)
            if cmdline:
                data["command"] = cmdline
            return {"process": data}
        if action == "kill_process":
            self._processes.terminate(payload.get("pid"), force=False)
            return {"status": "ok"}
        if action == "force_kill_process":
            self._processes.terminate(payload.get("pid"), force=True)
            return {"status": "ok"}
        raise ProcessError("unknown_action", "unknown action")

    def _error(self, code: str, message: str, request_id) -> dict:
        body = {"ok": False, "error": code, "message": message}
        if request_id is not None:
            body["id"] = request_id
        return body

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            sock = self._sock
            if sock is None:
                continue
            try:
                conn, _ = sock.accept()
            except TimeoutError:
                if not self._path.exists():
                    self._log.warning("socket path vanished; rebinding %s", self._path)
                    try:
                        self._bind()
                    except OSError:
                        self._log.exception("socket rebind failed")
                continue
            except OSError:
                if self._stop.is_set():
                    break
                continue
            threading.Thread(
                target=self._handle_client,
                args=(conn,),
                name="netmonitor-client",
                daemon=True,
            ).start()

    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            buffer = b""
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    if not raw.strip():
                        continue
                    response = self._line_to_response(raw)
                    try:
                        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                    except OSError:
                        return

    def _line_to_response(self, raw: bytes) -> dict:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error("invalid_json", "request is not valid JSON", None)
        if not isinstance(payload, dict):
            return self._error("invalid_json", "request must be a JSON object", None)
        if "command" in payload and "action" not in payload:
            return self._error(
                "invalid_request",
                "structured action required; command strings are rejected",
                payload.get("id"),
            )
        return self.handle_request(payload)
