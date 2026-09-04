import os
import signal
import subprocess
import time

import pytest

from agent.process_manager import ProcessError, ProcessManager


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
