"""PID validation and process signaling. Never uses a shell."""

from __future__ import annotations

import os
import signal
from pathlib import Path


class ProcessError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ProcessManager:
    def validate_pid(self, pid: object) -> int:
        if isinstance(pid, bool) or not isinstance(pid, int):
            raise ProcessError("invalid_pid", "pid must be a positive integer")
        if pid <= 1:
            raise ProcessError("invalid_pid", "pid must be greater than 1")
        if pid == os.getpid():
            raise ProcessError("invalid_pid", "refusing to signal the agent")
        return pid

    def exists(self, pid: int) -> bool:
        return Path(f"/proc/{pid}").exists()

    def command_line(self, pid: int, limit: int = 512) -> str | None:
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return None
        text = raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        if not text:
            return None
        return text[:limit]

    def terminate(self, pid: object, force: bool = False) -> None:
        checked = self.validate_pid(pid)
        if not self.exists(checked):
            raise ProcessError("not_found", f"process {checked} does not exist")
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.kill(checked, sig)
        except PermissionError as exc:
            raise ProcessError(
                "permission_denied",
                f"not allowed to signal process {checked}",
            ) from exc
        except ProcessLookupError as exc:
            raise ProcessError("not_found", f"process {checked} does not exist") from exc
