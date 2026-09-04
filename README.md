# NetMonitor

Lightweight Ubuntu / GNOME top-bar network monitor.

```text
↓ 8.42 MB/s   ↑ 1.21 MB/s
```

Click the indicator for a per-process breakdown. Open a process submenu for details, SIGTERM, or SIGKILL.

The UI is a GNOME Shell 50 extension. Monitoring runs in a user-level Python agent that reads [NetHogs](https://github.com/raboof/nethogs) and exposes a JSON Unix socket.

## Requirements

- Ubuntu with GNOME Shell 50
- Python 3.12+
- NetHogs (`sudo apt install nethogs`)

## One-time NetHogs permissions

The agent is **not** root. Grant capabilities on the nethogs binary instead:

```bash
sudo setcap "cap_net_admin,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep" /usr/sbin/nethogs
nethogs -t -d 1 -c 2
```

Ubuntu package upgrades can clear those capabilities. Re-run `setcap` if the menu says monitoring requires additional permissions.

## Install

```bash
./scripts/install.sh
```

Development install (symlinks the extension, runs the agent from this repo):

```bash
./scripts/install.sh --dev
```

On Wayland, log out and back in after enabling the extension. `Alt+F2 r` does not restart GNOME Shell.

Uninstall:

```bash
./scripts/uninstall.sh
```

## Manual agent

```bash
python3 -m agent              # Unix socket at $XDG_RUNTIME_DIR/netmonitor.sock
python3 -m agent --stream     # print snapshots in the terminal
```

## Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Docs

- [Architecture](docs/architecture.md)
- [Agent API](docs/api.md)
- [Development](docs/development.md)
