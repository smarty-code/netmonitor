#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UUID="netmonitor@netmonitor"
OUT_DIR="${1:-${ROOT}/dist}"
ZIP_NAME="${UUID}.shell-extension.zip"

mkdir -p "$OUT_DIR"
glib-compile-schemas "${ROOT}/extension/schemas"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp -a "${ROOT}/extension/." "$TMP/"
# gnome-extensions pack only includes a few well-known files unless listed.
if command -v gnome-extensions >/dev/null; then
  gnome-extensions pack "$TMP" \
    --extra-source=client.js \
    --extra-source=format.js \
    --extra-source=indicator.js \
    --extra-source=menu.js \
    --extra-source=processRow.js \
    -f -o "$OUT_DIR"
else
  (
    cd "$TMP"
    zip -qr "${OUT_DIR}/${ZIP_NAME}" \
      metadata.json extension.js prefs.js stylesheet.css \
      client.js format.js indicator.js menu.js processRow.js schemas
  )
fi

echo "Wrote ${OUT_DIR}/${ZIP_NAME}"
echo "This zip is only the GNOME UI. Install the agent with ./scripts/install.sh from a clone."
