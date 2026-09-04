from agent.models import ProcessStats
from agent.state import NetworkState


def test_snapshot_after_two_refreshes():
    state = NetworkState()
    assert state.feed_line("Refreshing:") is None
    assert state.feed_line("/usr/bin/curl/10/1000 1.0 2.0") is None
    snapshot = state.feed_line("Refreshing:")
    assert snapshot is not None
    assert snapshot.status == "ok"
    assert len(snapshot.processes) == 1
    proc = snapshot.processes[0]
    assert proc.pid == 10
    assert proc.upload == 1024.0
    assert proc.download == 2048.0
    assert snapshot.total_upload == 1024.0
    assert snapshot.total_download == 2048.0


def test_sorts_by_total_and_drops_vanished():
    state = NetworkState()
    state.feed_line("Refreshing:")
    state.feed_line("/usr/bin/a/1/1000 0.1 0.1")
    state.feed_line("/usr/bin/b/2/1000 5.0 5.0")
    first = state.feed_line("Refreshing:")
    assert first is not None
    assert [p.pid for p in first.processes] == [2, 1]

    state.feed_line("/usr/bin/a/1/1000 0.2 0.2")
    second = state.feed_line("Refreshing:")
    assert second is not None
    assert [p.pid for p in second.processes] == [1]


def test_permission_line_sets_status():
    state = NetworkState()
    snapshot = state.feed_line("Error opening pcap handlers for all devices.")
    assert snapshot is not None
    assert snapshot.status == "permission_denied"


def test_flush_commits_partial_buffer():
    state = NetworkState()
    state.feed_line("Refreshing:")
    state.feed_line("/bin/ping/9/1000 0.5 0.5")
    snapshot = state.flush()
    assert snapshot is not None
    assert snapshot.processes[0].pid == 9


def test_replace_processes():
    state = NetworkState()
    state.replace_processes(
        [ProcessStats(pid=3, name="x", command="/bin/x", download=10, upload=1)]
    )
    found = state.get_process(3)
    assert found is not None
    assert found.name == "x"
    assert state.get_process(99) is None
