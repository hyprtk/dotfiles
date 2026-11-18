#!/usr/bin/env bash
# ── hyprtk-term installer ─────────────────────────────────────────────────
# Installs the terminal the same way the rest of the suite installs its apps:
# a self-contained tree under $XDG_DATA_HOME, a launcher in ~/.local/bin and a
# desktop entry. No pip, no venv — PySide6 comes from the distro and libvterm is
# the only C dependency (it is in every supported archive).
#
#   ./install.sh                 install
#   ./install.sh --uninstall     remove
#   ./install.sh --set-default   also register as the default terminal
#   ./install.sh --system        install under /usr/local (ISO / all users)
#
# Env: HYPRTK_DRYRUN=1, XDG_DATA_HOME, PYTHON.
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

SELF=$(readlink -f "$0")
ROOT=$(cd -- "$(dirname -- "$SELF")" && pwd)
DATA="${HYPRTK_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}"
PREFIX="${HYPRTK_TERM_DIR:-$DATA/hyprtk-term}"
BIN="${HYPRTK_BIN_DIR:-$HOME/.local/bin}"
APPS="${HYPRTK_APPS_DIR:-$DATA/applications}"
PY="${PYTHON:-python3}"

set_default=0
for arg in "$@"; do
    case "$arg" in
        --uninstall)
            rm -rf "$PREFIX"
            rm -f "$BIN/hyprtk-term" "$APPS/hyprtk-term.desktop"
            command -v update-desktop-database >/dev/null 2>&1 \
                && update-desktop-database "$APPS" >/dev/null 2>&1 || true
            echo "removed hyprtk-term"
            exit 0
            ;;
        --set-default) set_default=1 ;;
        --system)
            # System-wide install (used by the live ISO): /usr/local, all users.
            PREFIX="${HYPRTK_TERM_DIR:-/usr/local/share/hyprtk-term}"
            BIN="${HYPRTK_BIN_DIR:-/usr/local/bin}"
            APPS="${HYPRTK_APPS_DIR:-/usr/local/share/applications}"
            ;;
        -h|--help)
            sed -n '2,16p' "$SELF" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install hyprtk-term into $PREFIX"
    exit 0
fi

command -v "$PY" >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

# libvterm is the emulator core; without it the app cannot start.
if ! "$PY" -c "import ctypes; ctypes.CDLL('libvterm.so.0')" >/dev/null 2>&1; then
    echo "warning: libvterm was not found." >&2
    echo "  arch: pacman -S libvterm | debian: apt install libvterm0" >&2
    echo "  fedora: dnf install libvterm | opensuse: zypper in libvterm0" >&2
    echo "  void: xbps-install libvterm | alpine: apk add libvterm" >&2
fi

mkdir -p "$PREFIX" "$BIN" "$APPS"
for item in hyprtk_term bin; do
    rm -rf "$PREFIX/$item"
    cp -a "$ROOT/$item" "$PREFIX/$item"
done
find "$PREFIX" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "$PREFIX/bin/hyprtk-term"

install -Dm644 "$ROOT/hyprtk_term/assets/hyprtk-term.svg" "$PREFIX/hyprtk-term.svg"
ln -sf "$PREFIX/bin/hyprtk-term" "$BIN/hyprtk-term"

# The session's PATH does not include ~/.local/bin (SDDM starts Hyprland
# without it), so the entry needs absolute paths or it will not launch.
_tmp=$(mktemp)
sed -e "s|^Exec=.*|Exec=$PREFIX/bin/hyprtk-term %U|" \
    -e "s|^Icon=.*|Icon=$PREFIX/hyprtk-term.svg|" \
    "$ROOT/hyprtk-term.desktop" > "$_tmp"
install -Dm644 "$_tmp" "$APPS/hyprtk-term.desktop"
rm -f "$_tmp"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi

if [ "$set_default" = "1" ] && command -v xdg-settings >/dev/null 2>&1; then
    xdg-settings set default-terminal-emulator hyprtk-term.desktop >/dev/null 2>&1 || true
    echo ":: registered as the default terminal emulator"
fi

# PySide6 normally comes from the distro. Debian/Ubuntu split it and ship only
# the Widgets modules, so fall back to PyPI in a private venv -- the same
# pattern the editor and the usb/iso GUIs use.
if ! "$PY" -c 'import PySide6.QtQml, PySide6.QtQuick' >/dev/null 2>&1; then
    echo ":: PySide6 QML bindings missing — installing into $PREFIX/venv"
    "$PY" -m venv --system-site-packages "$PREFIX/venv"
    "$PREFIX/venv/bin/pip" install --quiet --upgrade pip
    "$PREFIX/venv/bin/pip" install --quiet "PySide6>=6.6"
fi

echo "installed hyprtk-term to $PREFIX"
echo "launch: hyprtk-term"
