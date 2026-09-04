#!/usr/bin/env bash
set -euo pipefail

UUID="netmonitor@netmonitor"
EXT_DST="${HOME}/.local/share/gnome-shell/extensions/${UUID}"
LIB_DST="${HOME}/.local/lib/netmonitor"
UNIT_DST="${HOME}/.config/systemd/user/netmonitor.service"

systemctl --user disable --now netmonitor.service 2>/dev/null || true
rm -f "$UNIT_DST"
rm -rf "$EXT_DST" "${LIB_DST}/agent"
systemctl --user daemon-reload

python3 - <<'PY'
import ast
import subprocess

uuid = "netmonitor@netmonitor"
try:
    raw = subprocess.check_output(
        ["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
        text=True,
    )
    exts = [item for item in ast.literal_eval(raw) if item != uuid]
    value = "[" + ", ".join(f"'{item}'" for item in exts) + "]"
    subprocess.check_call(
        ["gsettings", "set", "org.gnome.shell", "enabled-extensions", value]
    )
except Exception:
    pass
PY

if command -v gnome-extensions >/dev/null; then
  gnome-extensions disable "$UUID" 2>/dev/null || true
fi

echo "NetMonitor user service and extension removed."
