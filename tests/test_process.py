import os
import signal
import subprocess
import time

import pytest

from agent.models import ProcessStats
from agent.process_manager import (
    ProcessError,
    ProcessManager,
    enrich_process,
    lookup_identity,
)


def test_accepts_integer_float():
    manager = ProcessManager()
    assert manager.validate_pid(4321.0) == 4321


def test_rejects_non_integer():
    manager = ProcessManager()
    with pytest.raises(ProcessError) as exc:
        manager.validate_pid("1234")
    assert exc.value.code == "invalid_pid"


def test_rejects_bool():
    manager = ProcessManager()
    with pytest.raises(ProcessError):
        manager.validate_pid(True)


def test_rejects_pid_one_and_self():
    manager = ProcessManager()
    with pytest.raises(ProcessError):
        manager.validate_pid(1)
    with pytest.raises(ProcessError):
        manager.validate_pid(os.getpid())


def test_exists_and_missing():
    manager = ProcessManager()
    assert manager.exists(os.getpid())
    assert not manager.exists(99999999)


def test_terminate_missing_process():
    manager = ProcessManager()
    with pytest.raises(ProcessError) as exc:
        manager.terminate(99999999)
    assert exc.value.code in {"not_found", "invalid_pid"}


def test_lookup_identity_resolves_proc_self_exe(tmp_path):
    proc = tmp_path / "39464"
    proc.mkdir()
    os.symlink("/usr/share/cursor/cursor", proc / "exe")
    (proc / "comm").write_text("cursor\n")
    (proc / "cmdline").write_bytes(b"/proc/self/exe\x00--type=utility\x00")
    name, command = lookup_identity(39464, proc_root=tmp_path)
    assert name == "cursor"
    assert command == "/usr/share/cursor/cursor"


def test_enrich_process_replaces_exe_name(tmp_path):
    proc_dir = tmp_path / "22199"
    proc_dir.mkdir()
    os.symlink("/usr/share/cursor/cursor", proc_dir / "exe")
    (proc_dir / "comm").write_text("cursor\n")
    stats = ProcessStats(
        pid=22199,
        name="exe",
        command="/proc/self/exe",
        download=10,
        upload=2,
    )
    enriched = enrich_process(stats, proc_root=tmp_path)
    assert enriched.name == "cursor"
    assert enriched.command == "/usr/share/cursor/cursor"


def test_sigterm_child_process():
    manager = ProcessManager()
    child = subprocess.Popen(["sleep", "30"])
    try:
        manager.terminate(child.pid, force=False)
        for _ in range(50):
            if child.poll() is not None:
                break
            time.sleep(0.05)
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
            child.wait(timeout=2)
