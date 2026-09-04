from pathlib import Path

from agent.models import format_rate
from agent.parser import (
    is_permission_error,
    is_refresh_marker,
    parse_identifier,
    parse_line,
    parse_snapshot_lines,
)


def test_format_rate():
    assert format_rate(0) == "0 B/s"
    assert format_rate(512) == "512 B/s"
    assert format_rate(1024) == "1.0 KB/s"
    assert "MB/s" in format_rate(8.42 * 1024 * 1024)


def test_parse_chrome_line():
    stats = parse_line("/usr/bin/google-chrome/12345/1000 0.39 4.82")
    assert stats is not None
    assert stats.pid == 12345
    assert stats.name == "google-chrome"
    assert stats.command == "/usr/bin/google-chrome"
    assert stats.uid == 1000
    assert stats.upload == 0.39 * 1024
    assert stats.download == 4.82 * 1024
    assert stats.total == stats.download + stats.upload


def test_parse_strips_long_command_line():
    line = (
        "/opt/google/chrome/chrome --type=utility --utility-sub-type=network/"
        "8406/1000 0.02 0.06"
    )
    stats = parse_line(line)
    assert stats is not None
    assert stats.pid == 8406
    assert stats.name == "chrome"
    assert stats.command == "/opt/google/chrome/chrome"


def test_parse_unknown_tcp():
    stats = parse_line("unknown TCP/0/0 0.01 0.02")
    assert stats is not None
    assert stats.pid == 0
    assert stats.name == "Unknown"


def test_parse_name_with_slashes():
    stats = parse_line("sshd: user@pts/7/656215/32076 0.0730469 0.0222659")
    assert stats is not None
    assert stats.pid == 656215
    assert stats.uid == 32076
    assert stats.command == "sshd: user@pts/7"


def test_skip_noise_lines():
    assert parse_line("Refreshing:") is None
    assert parse_line("Adding local address: 10.0.0.1") is None
    assert parse_line("Ethernet link detected") is None
    assert parse_line("Unknown connection: 1.2.3.4:80-5.6.7.8:9") is None
    assert parse_line("") is None


def test_refresh_and_permission_helpers():
    assert is_refresh_marker("Refreshing:")
    assert is_permission_error(
        "To run nethogs without being root, you need to enable capabilities"
    )
    assert is_permission_error("Error opening pcap handlers for all devices.")


def test_parse_identifier_fallback():
    name, pid, uid = parse_identifier("just-a-name")
    assert (name, pid, uid) == ("just-a-name", 0, 0)


def test_parse_snapshot_fixture():
    text = Path("tests/fixtures/nethogs_trace.txt").read_text(encoding="utf-8")
    first_refresh = text.split("Refreshing:")[1]
    lines = [line for line in first_refresh.splitlines() if line.strip()]
    processes = parse_snapshot_lines(lines)
    names = {proc.name for proc in processes}
    assert "google-chrome" in names
    assert "dockerd" in names
    assert "code" in names
    chrome = next(proc for proc in processes if proc.name == "google-chrome")
    assert chrome.pid == 12345
