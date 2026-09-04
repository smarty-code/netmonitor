# Architecture

NetMonitor is two processes that talk over a user-private Unix socket.

```text
GNOME Shell extension (GJS)
        │
        │  newline-delimited JSON
        ▼
$XDG_RUNTIME_DIR/netmonitor.sock
        │
        ▼
Python agent (user service)
        │
        ▼
/usr/sbin/nethogs -t -d 1 -v 0 -C
```

GNOME System Monitor (`gnome-system-monitor`) only graphs **interface totals**. It has no per-process network API, so it cannot replace NetHogs.

## Why two processes

The GNOME extension only renders UI. Packet capture, parsing, process signaling, and NetHogs supervision stay in the agent so a monitoring bug cannot take down GNOME Shell.

## Privilege split

- The agent runs as the logged-in user.
- Packet capture is granted to the **nethogs binary** with file capabilities (`cap_net_admin`, `cap_net_raw`, `cap_dac_read_search`, `cap_sys_ptrace`).
- `kill_process` / `force_kill_process` use `os.kill`. They only succeed for processes the user is allowed to signal. PID `1` and the agent itself are rejected.

## Data flow

1. The agent starts NetHogs in trace mode (`-t`) with a 1 second refresh and kB/s rates (`-v 0`).
2. Each `Refreshing:` marker closes the previous sample.
3. The parser turns `name/pid/uid sent recv` lines into `ProcessStats` with **bytes/s**.
4. `NetworkState` keeps the latest snapshot, sorted by total bandwidth.
5. The extension polls `get_stats` on a GSettings interval (default 1 second).
6. The top-bar label always updates. The process list updates while the menu is open.

## Failure modes

| Condition | Agent status | Extension copy |
|---|---|---|
| Socket not connected | — | Connecting… then Agent unavailable |
| `nethogs` missing | `nethogs_missing` | NetHogs not found |
| Missing capabilities / pcap | `permission_denied` | Network monitoring requires additional permissions. |
| NetHogs exited | `nethogs_exited` | retry with backoff |

The extension must not throw out of `enable()` / `disable()` when the agent is down.
