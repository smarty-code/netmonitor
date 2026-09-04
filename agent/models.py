"""Internal data structures for network snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


KB = 1024.0

STATUS_STARTING = "starting"
STATUS_OK = "ok"
STATUS_NETHOGS_MISSING = "nethogs_missing"
STATUS_PERMISSION_DENIED = "permission_denied"
STATUS_NETHOGS_EXITED = "nethogs_exited"


@dataclass(slots=True)
class ProcessStats:
    pid: int
    name: str
    command: str
    download: float
    upload: float
    uid: int = 0

    @property
    def total(self) -> float:
        return self.download + self.upload

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command,
            "download": self.download,
            "upload": self.upload,
            "total": self.total,
        }


@dataclass(slots=True)
class NetworkSnapshot:
    timestamp: float
    total_download: float
    total_upload: float
    processes: list[ProcessStats] = field(default_factory=list)
    status: str = STATUS_OK
    status_message: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "status_message": self.status_message,
            "total": {
                "download": self.total_download,
                "upload": self.total_upload,
            },
            "processes": [proc.to_dict() for proc in self.processes],
        }


def format_rate(bytes_per_sec: float) -> str:
    """Human-readable byte rate for terminal output."""
    value = abs(bytes_per_sec)
    if value < KB:
        return f"{bytes_per_sec:.0f} B/s"
    if value < KB * KB:
        return f"{bytes_per_sec / KB:.1f} KB/s"
    return f"{bytes_per_sec / (KB * KB):.2f} MB/s"


def snapshot_as_dict(snapshot: NetworkSnapshot) -> dict:
    return asdict(snapshot)
