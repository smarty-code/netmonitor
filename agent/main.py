"""NetMonitor agent entry point."""

from __future__ import annotations

import argparse
import signal
import sys
import time

from agent import config
from agent.logger import get_logger, setup_logging
from agent.models import format_rate
from agent.nethogs import NethogsReader
from agent.process_manager import ProcessManager
from agent.server import AgentServer
from agent.state import NetworkState


def _print_snapshot(snapshot) -> None:
    print("---")
    print(
        f"total  ↓ {format_rate(snapshot.total_download)}  "
        f"↑ {format_rate(snapshot.total_upload)}  [{snapshot.status}]"
    )
    for proc in snapshot.processes:
        print(
            f"{proc.name:<24} pid={proc.pid:<7} "
            f"↓ {format_rate(proc.download):<12} ↑ {format_rate(proc.upload)}"
        )
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NetMonitor monitoring agent")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print live snapshots to stdout instead of serving the Unix socket",
    )
    parser.add_argument(
        "--socket",
        default=None,
        help="Override Unix socket path",
    )
    args = parser.parse_args(argv)

    setup_logging()
    log = get_logger("main")
    state = NetworkState()
    stop = False

    def on_status(code: str, message: str) -> None:
        state.set_status(code, message)

    def on_line(line: str) -> None:
        snapshot = state.feed_line(line)
        if args.stream and snapshot is not None:
            _print_snapshot(snapshot)

    reader = NethogsReader(on_line=on_line, on_status=on_status)
    server = None
    if not args.stream:
        from pathlib import Path

        path = Path(args.socket) if args.socket else config.socket_path()
        server = AgentServer(state, ProcessManager(), path=path)

    def handle_stop(signum, _frame) -> None:
        nonlocal stop
        log.info("received signal %s", signum)
        stop = True

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    reader.start()
    if server is not None:
        server.start()
        log.info("agent ready")

    try:
        while not stop:
            time.sleep(0.2)
    finally:
        reader.stop()
        if server is not None:
            server.stop()
        leftover = state.flush()
        if args.stream and leftover is not None:
            _print_snapshot(leftover)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
