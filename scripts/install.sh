#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UUID="netmonitor@netmonitor"
EXT_DST="${HOME}/.local/share/gnome-shell/extensions/${UUID}"
LIB_DST="${HOME}/.local/lib/netmonitor"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_DST="${UNIT_DIR}/netmonitor.service"
DEV=0

if [[ "${1:-}" == "--dev" ]]; then
  DEV=1
fi

mkdir -p "$(dirname "$EXT_DST")" "$LIB_DST" "$UNIT_DIR"

glib-compile-schemas "${ROOT}/extension/schemas"

if [[ "$DEV" -eq 1 ]]; then
  if [[ -L "$EXT_DST" ]]; then
    rm -f "$EXT_DST"
  elif [[ -d "$EXT_DST" ]]; then
    dest_real="$(realpath "$EXT_DST")"
    src_real="$(realpath "${ROOT}/extension")"
    if [[ "$dest_real" == "$src_real" ]]; then
      echo "Keeping extension sources at $EXT_DST"
    else
      rm -rf "$EXT_DST"
    fi
  fi
  if [[ ! -e "$EXT_DST" ]]; then
    ln -sfn "${ROOT}/extension" "$EXT_DST"
  fi
  cat > "$UNIT_DST" <<EOF
[Unit]
Description=NetMonitor network monitoring agent (development)
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
WorkingDirectory=${ROOT}
ExecStartPre=-/bin/rm -f %t/netmonitor.sock
ExecStart=/usr/bin/python3 -m agent
Restart=on-failure
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
else
  rm -rf "$EXT_DST"
  mkdir -p "$EXT_DST"
  cp -a "${ROOT}/extension/." "$EXT_DST/"
  rm -rf "${LIB_DST}/agent"
  cp -a "${ROOT}/agent" "${LIB_DST}/agent"
  install -m 644 "${ROOT}/systemd/netmonitor.service" "$UNIT_DST"
fi

systemctl --user daemon-reload
systemctl --user enable --now netmonitor.service

if command -v gnome-extensions >/dev/null; then
  gnome-extensions enable "$UUID" 2>/dev/null || true
fi

echo
echo "Installed NetMonitor."
echo "Extension: $EXT_DST"
echo "User service: netmonitor.service (enabled)"
echo
echo "NetHogs needs packet-capture capabilities (once per nethogs upgrade):"
echo "  sudo setcap \"cap_net_admin,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep\" /usr/sbin/nethogs"
echo
echo "On Wayland, log out and back in if the top-bar indicator is missing."
