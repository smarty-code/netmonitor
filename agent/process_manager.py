"""PID validation, /proc identity lookup, and process signaling. Never uses a shell."""

from __future__ import annotations

import os
import signal
from pathlib import Path

from agent.models import ProcessStats

GENERIC_NAMES = frozenset({"exe", "self", ""})


class ProcessError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _basename(path: str) -> str:
    return os.path.basename(path.rstrip("/")) or path


def _useful_name(value: str | None) -> str | None:
    if not value:
        return None
    name = _basename(value)
    if name in GENERIC_NAMES:
        return None
    return name


def lookup_identity(pid: int, *, proc_root: str | os.PathLike[str] = "/proc") -> tuple[str | None, str | None]:
    """Return (display_name, command) from /proc, or (None, None)."""
    if pid <= 1:
        return None, None
    base = Path(proc_root) / str(pid)
    exe = None
    try:
        exe = os.readlink(base / "exe")
        if exe.endswith(" (deleted)"):
            exe = exe[: -len(" (deleted)")]
    except OSError:
        pass
    comm = None
    try:
        comm = (base / "comm").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    cmdline = None
    try:
        raw = (base / "cmdline").read_bytes()
        cmdline = raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    except OSError:
        pass
    cmd0 = cmdline.split()[0] if cmdline else None

    command = None
    if exe and _useful_name(exe):
        command = exe
    elif cmd0 and _useful_name(cmd0):
        command = cmd0
    elif exe:
        command = exe

    name = _useful_name(exe) or _useful_name(comm) or _useful_name(cmd0)
    return name, command


def enrich_process(
    proc: ProcessStats, *, proc_root: str | os.PathLike[str] = "/proc"
) -> ProcessStats:
    if proc.pid <= 1:
        return proc
    command_base = _basename(proc.command) if proc.command else ""
    needs_lookup = (
        proc.name in GENERIC_NAMES
        or proc.name.startswith("pid ")
        or command_base in GENERIC_NAMES
        or proc.command.startswith("/proc/")
    )
    if not needs_lookup:
        return proc
    name, command = lookup_identity(proc.pid, proc_root=proc_root)
    if not name and not command:
        return proc
    return ProcessStats(
        pid=proc.pid,
        name=name or proc.name,
        command=command or proc.command,
        download=proc.download,
        upload=proc.upload,
        uid=proc.uid,
    )


class ProcessManager:
    def validate_pid(self, pid: object) -> int:
        if isinstance(pid, bool):
            raise ProcessError("invalid_pid", "pid must be a positive integer")
        if isinstance(pid, float) and pid.is_integer():
            pid = int(pid)
        if not isinstance(pid, int):
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
