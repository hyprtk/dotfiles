#!/usr/bin/env bash
# ── hyprtk-editor installer ───────────────────────────────────────────────
# Installs the editor the same way the rest of the suite installs its apps: a
# self-contained tree under $XDG_DATA_HOME, a launcher in ~/.local/bin and a
# desktop entry. No pip, no venv — PySide6 and Pygments come from the distro
# (both are already suite dependencies for hyprtk-usb / iso-creator).
#
#   ./install.sh                 install
#   ./install.sh --uninstall     remove
#   ./install.sh --set-default   also make it the default text/plain handler
#   ./install.sh --system        install under /usr/local (ISO / all users)
#
# Env: HYPRTK_DRYRUN=1, XDG_DATA_HOME, PYTHON.
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

SELF=$(readlink -f "$0")
ROOT=$(cd -- "$(dirname -- "$SELF")" && pwd)
DATA="${HYPRTK_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}"
PREFIX="${HYPRTK_EDITOR_DIR:-$DATA/hyprtk-editor}"
BIN="${HYPRTK_BIN_DIR:-$HOME/.local/bin}"
APPS="${HYPRTK_APPS_DIR:-$DATA/applications}"
PY="${PYTHON:-python3}"

set_default=0
for arg in "$@"; do
    case "$arg" in
        --uninstall)
            rm -rf "$PREFIX"
            rm -f "$BIN/hyprtk-edit" "$APPS/hyprtk-editor.desktop"
            command -v update-desktop-database >/dev/null 2>&1 \
                && update-desktop-database "$APPS" >/dev/null 2>&1 || true
            echo "removed hyprtk-editor"
            exit 0
            ;;
        --set-default) set_default=1 ;;
        --system)
            # System-wide install (used by the live ISO): /usr/local, all users.
            PREFIX="${HYPRTK_EDITOR_DIR:-/usr/local/share/hyprtk-editor}"
            BIN="${HYPRTK_BIN_DIR:-/usr/local/bin}"
            APPS="${HYPRTK_APPS_DIR:-/usr/local/share/applications}"
            ;;
        -h|--help)
            sed -n '2,14p' "$SELF" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install hyprtk-editor into $PREFIX"
    exit 0
fi

command -v "$PY" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$PREFIX" "$BIN" "$APPS"
for item in hyprtk_editor bin; do
    rm -rf "$PREFIX/$item"
    cp -a "$ROOT/$item" "$PREFIX/$item"
done
find "$PREFIX" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$PREFIX/bin/hyprtk-edit"

cp "$ROOT/hyprtk_editor/assets/hyprtk-editor.svg" "$PREFIX/hyprtk-editor.svg"

ln -sf "$PREFIX/bin/hyprtk-edit" "$BIN/hyprtk-edit"

# The session's PATH does not include ~/.local/bin (SDDM starts Hyprland
# without it), so the entry needs absolute paths or it will not launch.
_tmp=$(mktemp)
sed -e "s|^Exec=.*|Exec=$PREFIX/bin/hyprtk-edit %U|" \
    -e "s|^Icon=.*|Icon=$PREFIX/hyprtk-editor.svg|" \
    "$ROOT/hyprtk-editor.desktop" > "$_tmp"
install -Dm644 "$_tmp" "$APPS/hyprtk-editor.desktop"
rm -f "$_tmp"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

if [ "$set_default" = "1" ] && command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default hyprtk-editor.desktop text/plain || true
    xdg-mime default hyprtk-editor.desktop text/markdown || true
    echo ":: set as the default handler for text/plain and text/markdown"
fi

# PySide6 normally comes from the distro. Debian/Ubuntu split it and only
# package the Widgets modules (the QML bindings are missing on Debian 12 and
# Ubuntu 24.04), so fall back to PyPI in a private venv -- the same pattern the
# hyprtk-usb / iso-creator GUIs use. Pygments is a small pip install too when
# the distro does not ship it.
if ! "$PY" -c 'import PySide6.QtQml, PySide6.QtQuick' >/dev/null 2>&1 \
    || ! "$PY" -c 'import pygments' >/dev/null 2>&1; then
    echo ":: PySide6 QML bindings or Pygments missing — installing into $PREFIX/venv"
    "$PY" -m venv --system-site-packages "$PREFIX/venv"
    "$PREFIX/venv/bin/pip" install --quiet --upgrade pip
    "$PREFIX/venv/bin/pip" install --quiet "PySide6>=6.6" "Pygments>=2.14"
fi

echo "installed hyprtk-editor to $PREFIX"
echo "launch: hyprtk-edit [FILE ...]"
