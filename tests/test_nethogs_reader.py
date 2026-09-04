import os
import time
from pathlib import Path

from agent.nethogs import NethogsReader
from agent.state import NetworkState

FAKE = Path(__file__).resolve().parent / "fakes" / "nethogs"


def test_reader_feeds_state_from_fake_nethogs(tmp_path):
    os.chmod(FAKE, 0o755)
    state = NetworkState()
    snapshots = []
    state.add_listener(lambda snap: snapshots.append(snap) if snap.status == "ok" else None)

    reader = NethogsReader(
        on_line=state.feed_line,
        command=["python3", str(FAKE)],
    )
    os.environ["FAKE_NETHOGS_INTERVAL"] = "0.05"
    os.environ["FAKE_NETHOGS_CYCLES"] = "3"
    reader.start()
    try:
        deadline = time.time() + 3
        while time.time() < deadline:
            if any(snap.processes for snap in snapshots) or state.snapshot().processes:
                break
            time.sleep(0.05)
        snapshot = state.snapshot()
        if snapshot.status != "ok":
            snapshot = state.flush() or snapshot
        assert snapshot.processes
        names = {proc.name for proc in snapshot.processes}
        assert "curl" in names or "firefox" in names
    finally:
        reader.stop()
        os.environ.pop("FAKE_NETHOGS_INTERVAL", None)
        os.environ.pop("FAKE_NETHOGS_CYCLES", None)


def test_permission_error_survives_process_exit(tmp_path):
    script = tmp_path / "nethogs"
    script.write_text(
        "#!/bin/sh\n"
        'echo "Error opening pcap handlers for all devices." >&2\n'
        "exit 1\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    state = NetworkState()
    reader = NethogsReader(
        on_line=state.feed_line,
        on_status=state.set_status,
        command=[str(script)],
    )
    reader.start()
    try:
        deadline = time.time() + 2
        while time.time() < deadline:
            if state.snapshot().status == "permission_denied":
                break
            time.sleep(0.05)
        assert state.snapshot().status == "permission_denied"
        time.sleep(0.2)
        assert state.snapshot().status == "permission_denied"
    finally:
        reader.stop()

