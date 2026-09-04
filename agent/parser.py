"""Parse NetHogs trace-mode output into ProcessStats."""

from __future__ import annotations

import os
import re

from agent.config import KB
from agent.models import ProcessStats

LINE_RE = re.compile(
    r"^(?P<ident>.+?)\s+(?P<sent>-?\d+(?:\.\d+)?)\s+(?P<recv>-?\d+(?:\.\d+)?)\s*$"
)

SKIP_PREFIXES = (
    "Refreshing:",
    "Adding local address",
    "Ethernet link",
    "Waiting for first packet",
    "Unknown connection",
    "Error opening",
    "To run nethogs",
    "See the documentation",
)

PERMISSION_MARKERS = (
    "without being root",
    "cap_net_admin",
    "Error opening pcap",
    "Error opening handler",
)


def is_refresh_marker(line: str) -> bool:
    return line.strip().startswith("Refreshing:")


def is_permission_error(line: str) -> bool:
    return any(marker in line for marker in PERMISSION_MARKERS)


def kbps_to_bytes(kbps: float) -> float:
    return kbps * KB


def _executable_path(command: str) -> str:
    if command.startswith("/") and " " in command:
        return command.split()[0]
    return command


def _display_name(command: str, pid: int) -> str:
    if pid == 0 and "unknown" in command.lower():
        return "Unknown"
    binary = _executable_path(command)
    if binary.startswith("/"):
        binary = os.path.basename(binary) or binary
    if len(binary) > 48:
        return binary[:45] + "..."
    return binary


def parse_identifier(ident: str) -> tuple[str, int, int]:
    """Split `name/pid/uid` from the right so names may contain slashes."""
    parts = ident.rsplit("/", 2)
    if len(parts) != 3:
        return ident, 0, 0
    name, pid_s, uid_s = parts
    try:
        pid = int(pid_s)
        uid = int(uid_s)
    except ValueError:
        return ident, 0, 0
    return name, pid, uid


def parse_line(line: str) -> ProcessStats | None:
    text = line.strip()
    if not text:
        return None
    if any(text.startswith(prefix) for prefix in SKIP_PREFIXES):
        return None
    match = LINE_RE.match(text)
    if not match:
        return None
    command, pid, uid = parse_identifier(match.group("ident"))
    sent_kb = float(match.group("sent"))
    recv_kb = float(match.group("recv"))
    return ProcessStats(
        pid=pid,
        name=_display_name(command, pid),
        command=_executable_path(command),
        download=kbps_to_bytes(recv_kb),
        upload=kbps_to_bytes(sent_kb),
        uid=uid,
    )


def merge_by_pid(processes: list[ProcessStats]) -> list[ProcessStats]:
    by_key: dict[tuple[int, str], ProcessStats] = {}
    for proc in processes:
        key = (proc.pid, proc.name if proc.pid <= 0 else "")
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = proc
            continue
        by_key[key] = ProcessStats(
            pid=existing.pid,
            name=existing.name,
            command=existing.command,
            download=existing.download + proc.download,
            upload=existing.upload + proc.upload,
            uid=existing.uid,
        )
    return list(by_key.values())


def parse_snapshot_lines(lines: list[str]) -> list[ProcessStats]:
    parsed = [proc for line in lines if (proc := parse_line(line))]
    return merge_by_pid(parsed)
