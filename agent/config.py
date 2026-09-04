"""Agent configuration. Override paths with environment variables in tests."""

from __future__ import annotations

import os
from pathlib import Path

NETHOGS_BIN = os.environ.get("NETMONITOR_NETHOGS", "/usr/sbin/nethogs")
REFRESH_SECONDS = 1
VIEW_MODE_KBPS = "0"

# Trace mode, 1s refresh, kB/s rates, TCP+UDP, short process names.
NETHOGS_ARGS = ("-t", "-d", str(REFRESH_SECONDS), "-v", VIEW_MODE_KBPS, "-C", "-b")

RESTART_INITIAL_DELAY = 1.0
RESTART_MAX_DELAY = 30.0
SOCKET_BACKLOG = 8

KB = 1024.0


def socket_path() -> Path:
    override = os.environ.get("NETMONITOR_SOCK")
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        runtime = f"/tmp/netmonitor-{os.getuid()}"
    return Path(runtime) / "netmonitor.sock"


def nethogs_command() -> list[str]:
    return [NETHOGS_BIN, *NETHOGS_ARGS]
