#!/usr/bin/env bash
set -euo pipefail

SELF=$(readlink -f "$0")
ROOT=$(cd -- "$(dirname -- "$SELF")" && pwd)
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA/hyprtk-file-manager"
BIN="$HOME/.local/bin"
APPS="$DATA/applications"

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$PREFIX"
    rm -f "$BIN/hyprtk-fm" "$APPS/hyprtk-file-manager.desktop"
    echo "removed hyprtk-file-manager"
    exit 0
fi

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install hyprtk-file-manager into $PREFIX"
    exit 0
fi

command -v qs >/dev/null 2>&1 || { echo "qs (Quickshell) is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$PREFIX" "$BIN" "$APPS"
for item in shell.qml surface components theme config data backend bin; do
    rm -rf "$PREFIX/$item"
    cp -a "$ROOT/$item" "$PREFIX/$item"
done

find "$PREFIX/backend" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$PREFIX/bin/hyprtk-fm"
ln -sf "$PREFIX/bin/hyprtk-fm" "$BIN/hyprtk-fm"
cp "$ROOT/hyprtk-file-manager.desktop" "$APPS/hyprtk-file-manager.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

echo "installed hyprtk-file-manager to $PREFIX"
echo "launch: hyprtk-fm [path]"
