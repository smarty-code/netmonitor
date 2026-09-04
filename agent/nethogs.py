"""Launch and supervise the NetHogs subprocess."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections.abc import Callable

from agent import config
from agent.logger import get_logger
from agent.parser import is_permission_error

OnLine = Callable[[str], None]
OnStatus = Callable[[str, str], None]


class NethogsError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class NethogsReader:
    """Start NetHogs in trace mode and deliver stdout/stderr lines."""

    def __init__(
        self,
        on_line: OnLine,
        on_status: OnStatus | None = None,
        command: list[str] | None = None,
    ) -> None:
        self._on_line = on_line
        self._on_status = on_status
        self._command = command or config.nethogs_command()
        self._log = get_logger("nethogs")
        self._proc: subprocess.Popen[str] | None = None
        self._stop = threading.Event()
        self._supervisor: threading.Thread | None = None
        self._restart_delay = config.RESTART_INITIAL_DELAY
        self._fatal_status: str | None = None

    def start(self) -> None:
        self._stop.clear()
        self._supervisor = threading.Thread(
            target=self._run_loop, name="nethogs-supervisor", daemon=True
        )
        self._supervisor.start()

    def stop(self) -> None:
        self._stop.set()
        self._kill_process()
        if self._supervisor is not None:
            self._supervisor.join(timeout=3)

    def restart(self) -> None:
        self._kill_process()

    def _notify(self, code: str, message: str) -> None:
        if code in {"permission_denied", "nethogs_missing"}:
            self._fatal_status = code
        self._log.warning("%s: %s", code, message)
        if self._on_status:
            self._on_status(code, message)

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            started = False
            self._fatal_status = None
            try:
                self._spawn()
                started = True
                self._restart_delay = config.RESTART_INITIAL_DELAY
                self._pipe_output()
            except FileNotFoundError:
                self._notify(
                    "nethogs_missing",
                    f"NetHogs not found at {self._command[0]}",
                )
            except PermissionError as exc:
                self._notify("permission_denied", str(exc))
            except OSError as exc:
                self._notify("nethogs_exited", str(exc))

            if self._stop.is_set():
                break
            if started and self._fatal_status is None:
                self._notify(
                    "nethogs_exited",
                    f"NetHogs stopped; retrying in {self._restart_delay:.0f}s",
                )
            delay = (
                config.RESTART_MAX_DELAY
                if self._fatal_status
                else self._restart_delay
            )
            if self._stop.wait(delay):
                break
            if not self._fatal_status:
                self._restart_delay = min(
                    self._restart_delay * 2, config.RESTART_MAX_DELAY
                )

    def _spawn(self) -> None:
        self._log.info("starting: %s", " ".join(self._command))
        self._proc = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            start_new_session=True,
        )

    def _pipe_output(self) -> None:
        assert self._proc is not None
        stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self._proc.stderr,),
            name="nethogs-stderr",
            daemon=True,
        )
        stderr_thread.start()
        self._read_stream(self._proc.stdout)
        self._proc.wait()
        stderr_thread.join(timeout=2)

    def _read_stream(self, stream) -> None:
        if stream is None:
            return
        for raw in stream:
            if self._stop.is_set():
                break
            line = raw.rstrip("\n")
            if is_permission_error(line):
                self._notify(
                    "permission_denied",
                    "Network monitoring requires additional permissions.",
                )
            try:
                self._on_line(line)
            except Exception:
                self._log.exception("line handler failed")

    def _kill_process(self) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=1)
        self._proc = None
