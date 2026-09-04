# NetMonitor

Lightweight Ubuntu / GNOME top-bar network monitor.

```text
↓ 8.42 MB/s   ↑ 1.21 MB/s
```

Click the indicator for a per-process breakdown. Open a process submenu for **Details**, **Kill Process** (SIGTERM), or **Force Kill** (SIGKILL). Settings let you place the indicator on the **left**, **center**, or **right** of the top bar.

The UI is a GNOME Shell 50 extension. Monitoring runs in a user-level Python agent that reads [NetHogs](https://github.com/raboof/nethogs) and exposes a JSON Unix socket. **GNOME System Monitor is not a replacement** — it only graphs whole-machine traffic, not per-process bandwidth.

## Install from GitHub

```bash
sudo apt install nethogs python3 libglib2.0-bin
git clone https://github.com/smarty-code/netmonitor.git
cd netmonitor
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
```

Grant NetHogs capture capabilities (the agent itself does **not** run as root):

```bash
sudo setcap "cap_net_admin,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep" /usr/sbin/nethogs
```

On Wayland, **log out and back in** so GNOME Shell loads the extension. `Alt+F2 r` does not restart the shell.

Then right-click the panel indicator (or open **Settings** from its menu) and set **Position** to Left / Center / Right.

Uninstall:

```bash
./scripts/uninstall.sh
```

Ubuntu package upgrades can clear NetHogs capabilities. Re-run `setcap` if the menu says monitoring requires additional permissions.

## What gets installed

| Piece | Location |
|---|---|
| GNOME extension | `~/.local/share/gnome-shell/extensions/netmonitor@netmonitor/` |
| Python agent | `~/.local/lib/netmonitor/agent/` |
| User service | `~/.config/systemd/user/netmonitor.service` |

`systemctl --user enable --now netmonitor.service` starts the agent at login.

## Releases

CI packs `netmonitor@netmonitor.shell-extension.zip` on every push. Tagged releases (`v1.0.0`, …) attach that zip. The zip is **only the GNOME UI** — still clone the tag and run `./scripts/install.sh` so the agent is installed.

```bash
git clone --branch v1.0.0 https://github.com/smarty-code/netmonitor.git
cd netmonitor
./scripts/install.sh
```

## Development

```bash
./scripts/install.sh --dev   # symlink extension, run agent from this repo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
make test
make pack                   # writes dist/*.shell-extension.zip
```

## Docs

- [Architecture](docs/architecture.md)
- [Agent API](docs/api.md)
- [Development](docs/development.md)
