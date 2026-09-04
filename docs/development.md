# Development

## Prerequisites

- Ubuntu with GNOME Shell 50 (this project targets `"shell-version": ["50"]`)
- Python 3.12+
- NetHogs (`/usr/sbin/nethogs`)
- `glib-compile-schemas`

## Capabilities

NetHogs cannot open pcap as a normal user until capabilities are set. Package upgrades can clear them.

```bash
sudo setcap "cap_net_admin,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep" /usr/sbin/nethogs
nethogs -t -d 1 -c 2
```

## Agent

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Print live snapshots without the socket (uses a fake NetHogs if you point at it):

```bash
python3 -m agent --stream
NETMONITOR_NETHOGS="$(pwd)/tests/fakes/nethogs" python3 -m agent --stream
```

Run the real agent:

```bash
python3 -m agent
python3 - <<'PY'
import json, os, socket
path = os.path.join(os.environ["XDG_RUNTIME_DIR"], "netmonitor.sock")
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(path)
sock.sendall(b'{"action":"ping"}\n')
print(sock.recv(4096).decode())
PY
```

## GNOME extension

This is a Wayland session. `Alt+F2` `r` does not reload GNOME Shell. After copying or editing the extension:

```bash
./scripts/install.sh --dev
gnome-extensions enable netmonitor@netmonitor
```

Then log out and back in, or test in a nested Shell if `mutter-devkit` is installed:

```bash
dbus-run-session gnome-shell --devkit --wayland
```

Watch Shell errors with:

```bash
journalctl --user -f /usr/bin/gnome-shell
```

## Packing for GitHub

```bash
./scripts/pack.sh
```

writes `dist/netmonitor@netmonitor.shell-extension.zip`. CI runs tests and uploads that zip. Push a tag `v1.1.0` to publish a GitHub Release.

The zip is the GNOME UI only. End users should clone the repo (or a tag) and run `./scripts/install.sh`.

## Layout

| Path | Role |
|---|---|
| `agent/` | Python monitoring agent |
| `extension/` | GNOME Shell 50 ESM extension |
| `systemd/netmonitor.service` | User unit |
| `tests/` | Parser, state, API, process tests |
