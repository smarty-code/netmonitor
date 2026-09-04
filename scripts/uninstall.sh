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
echo "NetMonitor user service and extension removed."
