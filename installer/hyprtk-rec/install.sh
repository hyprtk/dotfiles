#!/usr/bin/env bash
# ── hyprtk-rec installer ──────────────────────────────────────────────────
# Installs the screen recorder the way the rest of the suite installs its apps:
# a self-contained tree under $XDG_DATA_HOME, a launcher in ~/.local/bin and a
# desktop entry. No pip, no venv — PySide6 comes from the distro.
#
# External programs (installed by the suite's package lists, not by this
# script): wf-recorder (encoder; already a suite dependency), wl-screenrec
# (optional, faster), slurp (region selection), pactl (audio devices),
# libnotify (notifications).
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
PREFIX="${HYPRTK_REC_DIR:-$DATA/hyprtk-rec}"
BIN="${HYPRTK_BIN_DIR:-$HOME/.local/bin}"
APPS="${HYPRTK_APPS_DIR:-$DATA/applications}"
PY="${PYTHON:-python3}"

for arg in "$@"; do
    case "$arg" in
        --uninstall)
            rm -rf "$PREFIX"
            rm -f "$BIN/hyprtk-rec" "$APPS/hyprtk-rec.desktop"
            command -v update-desktop-database >/dev/null 2>&1 \
                && update-desktop-database "$APPS" >/dev/null 2>&1 || true
            echo "removed hyprtk-rec"
            exit 0
            ;;
        --system)
            PREFIX="${HYPRTK_REC_DIR:-/usr/local/share/hyprtk-rec}"
            BIN="${HYPRTK_BIN_DIR:-/usr/local/bin}"
            APPS="${HYPRTK_APPS_DIR:-/usr/local/share/applications}"
            ;;
        -h|--help)
            sed -n '2,18p' "$SELF" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install hyprtk-rec into $PREFIX"
    exit 0
fi

command -v "$PY" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

if ! command -v wf-recorder >/dev/null 2>&1 && ! command -v wl-screenrec >/dev/null 2>&1; then
    echo "warning: neither wf-recorder nor wl-screenrec is installed — recording needs one" >&2
fi
command -v slurp >/dev/null 2>&1 || echo "warning: 'slurp' not found — region recording needs it" >&2
command -v pactl >/dev/null 2>&1 || echo "warning: 'pactl' not found — audio device selection needs it" >&2

mkdir -p "$PREFIX" "$BIN" "$APPS"
for item in hyprtk_rec bin; do
    rm -rf "$PREFIX/$item"
    cp -a "$ROOT/$item" "$PREFIX/$item"
done
find "$PREFIX" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$PREFIX/bin/hyprtk-rec"

cp "$ROOT/hyprtk_rec/assets/hyprtk-rec.svg" "$PREFIX/hyprtk-rec.svg"

ln -sf "$PREFIX/bin/hyprtk-rec" "$BIN/hyprtk-rec"

# The session's PATH does not include ~/.local/bin (SDDM starts Hyprland
# without it), so the entry needs absolute paths or it will not launch.
_tmp=$(mktemp)
sed -e "s|^Exec=.*|Exec=$PREFIX/bin/hyprtk-rec|" \
    -e "s|^Icon=.*|Icon=$PREFIX/hyprtk-rec.svg|" \
    "$ROOT/hyprtk-rec.desktop" > "$_tmp"
install -Dm644 "$_tmp" "$APPS/hyprtk-rec.desktop"
rm -f "$_tmp"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

# Debian/Ubuntu package PySide6 without the QML bindings; PyPI venv fallback,
# the same pattern the editor and terminal use.
if ! "$PY" -c 'import PySide6.QtQml, PySide6.QtQuick' >/dev/null 2>&1; then
    echo ":: PySide6 QML bindings missing — installing into $PREFIX/venv"
    "$PY" -m venv --system-site-packages "$PREFIX/venv"
    "$PREFIX/venv/bin/pip" install --quiet --upgrade pip
    "$PREFIX/venv/bin/pip" install --quiet "PySide6>=6.6"
fi

echo "installed hyprtk-rec to $PREFIX"
echo "launch: hyprtk-rec            (window)"
echo "        hyprtk-rec --toggle   (start or stop)"
