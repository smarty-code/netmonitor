"""In-memory network state updated from NetHogs snapshots."""

from __future__ import annotations

import threading
import time

from agent.models import (
    STATUS_OK,
    STATUS_STARTING,
    NetworkSnapshot,
    ProcessStats,
)
from agent.parser import (
    is_permission_error,
    is_refresh_marker,
    parse_snapshot_lines,
)
from agent.process_manager import enrich_process

IDLE_BYTES_PER_SEC = 0.0


def _process_key(proc: ProcessStats) -> tuple:
    if proc.pid > 0:
        return ("pid", proc.pid)
    return ("zero", proc.name, proc.command)


class NetworkState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._buffer: list[str] = []
        self._timestamp = 0.0
        self._total_download = 0.0
        self._total_upload = 0.0
        self._processes: list[ProcessStats] = []
        self._status = STATUS_STARTING
        self._status_message = "Waiting for NetHogs"
        self._listeners: list = []

    def add_listener(self, callback) -> None:
        self._listeners.append(callback)

    def set_status(self, status: str, message: str = "") -> None:
        with self._lock:
            self._status = status
            self._status_message = message
        self._emit()

    def feed_line(self, line: str) -> NetworkSnapshot | None:
        if is_permission_error(line):
            self.set_status(
                "permission_denied",
                "Network monitoring requires additional permissions.",
            )
            return self.snapshot()
        if is_refresh_marker(line):
            committed = None
            with self._lock:
                if self._buffer:
                    committed = self._commit_unlocked(self._buffer)
                    self._buffer = []
            return committed
        stripped = line.strip()
        if stripped:
            with self._lock:
                self._buffer.append(stripped)
        return None

    def flush(self) -> NetworkSnapshot | None:
        with self._lock:
            if not self._buffer:
                return None
            snapshot = self._commit_unlocked(self._buffer)
            self._buffer = []
        return snapshot

    def replace_processes(self, processes: list[ProcessStats]) -> NetworkSnapshot:
        with self._lock:
            return self._apply_unlocked(processes)

    def snapshot(self) -> NetworkSnapshot:
        with self._lock:
            return NetworkSnapshot(
                timestamp=self._timestamp,
                total_download=self._total_download,
                total_upload=self._total_upload,
                processes=list(self._processes),
                status=self._status,
                status_message=self._status_message,
            )

    def get_process(self, pid: int) -> ProcessStats | None:
        with self._lock:
            for proc in self._processes:
                if proc.pid == pid:
                    return proc
        return None

    def _commit_unlocked(self, lines: list[str]) -> NetworkSnapshot:
        processes = parse_snapshot_lines(lines)
        return self._apply_unlocked(processes)

    def _apply_unlocked(self, processes: list[ProcessStats]) -> NetworkSnapshot:
        enriched = [enrich_process(proc) for proc in processes]
        self._total_download = sum(p.download for p in enriched)
        self._total_upload = sum(p.upload for p in enriched)
        active = [proc for proc in enriched if proc.total > IDLE_BYTES_PER_SEC]
        incoming = {_process_key(proc): proc for proc in active}
        kept: list[ProcessStats] = []
        seen: set[tuple] = set()
        for previous in self._processes:
            key = _process_key(previous)
            current = incoming.get(key)
            if current is None:
                continue
            kept.append(current)
            seen.add(key)
        newcomers = [proc for proc in active if _process_key(proc) not in seen]
        self._processes = list(reversed(newcomers)) + kept
        self._timestamp = time.time()
        self._status = STATUS_OK
        self._status_message = ""
        snapshot = NetworkSnapshot(
            timestamp=self._timestamp,
            total_download=self._total_download,
            total_upload=self._total_upload,
            processes=list(self._processes),
            status=self._status,
            status_message=self._status_message,
        )
        self._emit(snapshot)
        return snapshot

    def _emit(self, snapshot: NetworkSnapshot | None = None) -> None:
        current = snapshot or self.snapshot()
        for listener in list(self._listeners):
            try:
                listener(current)
            except Exception:
                pass
