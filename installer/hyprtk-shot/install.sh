#!/usr/bin/env bash
# ── hyprtk-shot installer ─────────────────────────────────────────────────
# Installs the screenshot tool the way the rest of the suite installs its apps:
# a self-contained tree under $XDG_DATA_HOME, a launcher in ~/.local/bin and a
# desktop entry. No pip, no venv — PySide6 comes from the distro and is already
# a suite dependency.
#
# External programs (installed by the suite's package lists, not by this
# script): grim (capture), slurp (cross-output region selection), wl-clipboard
# (copy), libnotify (notifications).
#
#   ./install.sh                 install
#   ./install.sh --uninstall     remove
#   ./install.sh --system        install under /usr/local (ISO / all users)
#
# Env: HYPRTK_DRYRUN=1, XDG_DATA_HOME, PYTHON.
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

SELF=$(readlink -f "$0")
ROOT=$(cd -- "$(dirname -- "$SELF")" && pwd)
DATA="${HYPRTK_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}"
PREFIX="${HYPRTK_SHOT_DIR:-$DATA/hyprtk-shot}"
BIN="${HYPRTK_BIN_DIR:-$HOME/.local/bin}"
APPS="${HYPRTK_APPS_DIR:-$DATA/applications}"
PY="${PYTHON:-python3}"

for arg in "$@"; do
    case "$arg" in
        --uninstall)
            rm -rf "$PREFIX"
            rm -f "$BIN/hyprtk-shot" "$APPS/hyprtk-shot.desktop"
            command -v update-desktop-database >/dev/null 2>&1 \
                && update-desktop-database "$APPS" >/dev/null 2>&1 || true
            echo "removed hyprtk-shot"
            exit 0
            ;;
        --system)
            # System-wide install (used by the live ISO): /usr/local, all users.
            PREFIX="${HYPRTK_SHOT_DIR:-/usr/local/share/hyprtk-shot}"
            BIN="${HYPRTK_BIN_DIR:-/usr/local/bin}"
            APPS="${HYPRTK_APPS_DIR:-/usr/local/share/applications}"
            ;;
        -h|--help)
            sed -n '2,20p' "$SELF" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install hyprtk-shot into $PREFIX"
    exit 0
fi

command -v "$PY" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

for tool in grim wl-copy; do
    command -v "$tool" >/dev/null 2>&1 || \
        echo "warning: '$tool' not found — screenshots need it (pacman -S grim wl-clipboard)" >&2
done
command -v slurp >/dev/null 2>&1 || \
    echo "warning: 'slurp' not found — only cross-output region selection needs it" >&2

mkdir -p "$PREFIX" "$BIN" "$APPS"
for item in hyprtk_shot bin; do
    rm -rf "$PREFIX/$item"
    cp -a "$ROOT/$item" "$PREFIX/$item"
done
find "$PREFIX" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$PREFIX/bin/hyprtk-shot"

cp "$ROOT/hyprtk_shot/assets/hyprtk-shot.svg" "$PREFIX/hyprtk-shot.svg"

ln -sf "$PREFIX/bin/hyprtk-shot" "$BIN/hyprtk-shot"

# The session's PATH does not include ~/.local/bin (SDDM starts Hyprland
# without it), so the entry needs absolute paths or it will not launch.
_tmp=$(mktemp)
sed -e "s|^Exec=.*|Exec=$PREFIX/bin/hyprtk-shot|" \
    -e "s|^Icon=.*|Icon=$PREFIX/hyprtk-shot.svg|" \
    "$ROOT/hyprtk-shot.desktop" > "$_tmp"
install -Dm644 "$_tmp" "$APPS/hyprtk-shot.desktop"
rm -f "$_tmp"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

# Debian/Ubuntu package PySide6 without the QML bindings; fall back to PyPI in
# a private venv, the same pattern the editor and the suite's GUI tools use.
if ! "$PY" -c 'import PySide6.QtQml, PySide6.QtQuick' >/dev/null 2>&1; then
    echo ":: PySide6 QML bindings missing — installing into $PREFIX/venv"
    "$PY" -m venv --system-site-packages "$PREFIX/venv"
    "$PREFIX/venv/bin/pip" install --quiet --upgrade pip
    "$PREFIX/venv/bin/pip" install --quiet "PySide6>=6.6"
fi

echo "installed hyprtk-shot to $PREFIX"
echo "launch: hyprtk-shot          (launcher)"
echo "        hyprtk-shot region   (freeze, select, annotate)"
