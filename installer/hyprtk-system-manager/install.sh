#!/usr/bin/env bash
# hyprtk-system-manager installer.
#
# Installs the Quickshell front end + Python backend into the user's data dir,
# links `hyprtk-settings` onto PATH and registers a desktop entry. No root is
# needed and no system packages are modified.
#
# Usage: ./install.sh             install or update (user)
#        ./install.sh --system    install under /usr/local (ISO / system-wide)
#        ./install.sh --dry-run   check dependencies, change nothing
#        ./install.sh --uninstall remove the app (keeps backups)
#        ./install.sh --help      show this message

set -euo pipefail

APP_NAME="hyprtk-system-manager"
LAUNCHER_NAME="hyprtk-settings"
TITLE="System Settings"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"

SYSTEM_MODE=0
DRY_RUN=0
DO_UNINSTALL=0
PREFIX=""

usage() {
    echo "Usage: $0 [--system [--prefix DIR]] [--dry-run|--uninstall|--help]"
    echo "  (no args)     Install or update $TITLE for the current user."
    echo "  --system      Install under /usr/local (used by the ISO)."
    echo "  --prefix DIR  With --system: install under DIR (default /usr/local)."
    echo "  --dry-run     Check requirements and report what is missing; change nothing."
    echo "  --uninstall   Remove the app, launcher and desktop entry (backups are kept)."
    echo
    echo "  DESTDIR is honoured for packaging (paths are written under it, but"
    echo "  launchers still point at the final prefix)."
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --system) SYSTEM_MODE=1 ;;
        --prefix) shift; PREFIX="${1:-}" ;;
        --prefix=*) PREFIX="${1#--prefix=}" ;;
        -u|--uninstall) DO_UNINSTALL=1 ;;
        *) echo ":: WARN: unknown option '$1' (ignored)" >&2 ;;
    esac
    shift
done

DESTDIR="${DESTDIR:-}"
if [ "$SYSTEM_MODE" -eq 1 ]; then
    PREFIX="${PREFIX:-/usr/local}"
    PREFIX="${PREFIX%/}"
    INSTALL_DIR="$PREFIX/share/$APP_NAME"
    BIN_DIR="$PREFIX/bin"
    APPS_DIR="$PREFIX/share/applications"
    LIBEXEC_DIR="$PREFIX/libexec"
    POLICY_DIR="$PREFIX/share/polkit-1/actions"
    STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-system-manager"
else
    INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
    BIN_DIR="$HOME/.local/bin"
    APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-system-manager"
fi
INSTALL_DIR_D="${DESTDIR}${INSTALL_DIR}"
BIN_DIR_D="${DESTDIR}${BIN_DIR}"
APPS_DIR_D="${DESTDIR}${APPS_DIR}"
DESKTOP_FILE="$APPS_DIR_D/$APP_NAME.desktop"

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install $TITLE into $INSTALL_DIR"
    exit 0
fi

# Root is required only for --system.
if [ "$SYSTEM_MODE" -eq 1 ] && [ "$DRY_RUN" -eq 0 ] && [ -z "$DESTDIR" ] \
    && [ "$(id -u)" -ne 0 ]; then
    echo ":: --system needs root (sudo $0 --system)" >&2
    exit 1
fi

on_path() {
    case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac
}

qs_bin() { command -v qs 2>/dev/null || command -v quickshell 2>/dev/null || true; }

missing_deps() {
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    [ -n "$(qs_bin)" ] || missing+=("quickshell (qs)")
    printf '%s\n' "${missing[@]}"
}

if [ "$DO_UNINSTALL" -eq 1 ]; then
    echo ":: Uninstalling $APP_NAME (system mode: $SYSTEM_MODE)..."
    if [ -L "$BIN_DIR/$LAUNCHER_NAME" ] \
        && [ "$(readlink -f "$BIN_DIR_D/$LAUNCHER_NAME")" = "$INSTALL_DIR_D/bin/$LAUNCHER_NAME" ]; then
        rm -f "$BIN_DIR_D/$LAUNCHER_NAME"
    fi
    rm -rf "${INSTALL_DIR_D:?}"
    rm -f "$DESKTOP_FILE"
    if [ "$SYSTEM_MODE" -eq 1 ]; then
        rm -f "${DESTDIR}${LIBEXEC_DIR}/hyprtk-sm-helper"
        rm -f "${DESTDIR}${POLICY_DIR}/org.hyprtk.system-manager.policy"
    fi
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$APPS_DIR_D" >/dev/null 2>&1 || true
    echo ":: Removed."
    echo ":: Kept backups in $STATE_DIR"
    exit 0
fi

MISSING="$(missing_deps)"

if [ "$DRY_RUN" -eq 1 ]; then
    echo ":: Dry run — nothing will be installed or modified."
    echo ":: Mode:            $([ "$SYSTEM_MODE" -eq 1 ] && echo system || echo user)"
    echo ":: Install dir:     $INSTALL_DIR_D"
    echo ":: Launcher:        $BIN_DIR_D/$LAUNCHER_NAME"
    echo ":: Desktop entry:   $APPS_DIR_D/$APP_NAME.desktop"
    if [ "$SYSTEM_MODE" -eq 1 ]; then
        echo ":: Polkit policy:   ${DESTDIR}${POLICY_DIR}/org.hyprtk.system-manager.policy"
        echo ":: Root helper:     ${DESTDIR}${LIBEXEC_DIR}/hyprtk-sm-helper"
    fi
    printf ':: python3:         %s\n' "$(command -v python3 || echo MISSING)"
    printf ':: Quickshell:      %s\n' "$(qs_bin || echo MISSING)"
    printf ':: Hyprland:        %s\n' "$(command -v hyprctl || echo 'not found (display panels will be read-only)')"
    printf ':: Privilege:       %s\n' "$(command -v pkexec || command -v sudo || echo none)"
    if [ -n "$MISSING" ]; then
        echo ":: Result: MISSING — $(echo "$MISSING" | tr '\n' ' ')"
        exit 1
    fi
    echo ":: Result: ready."
    exit 0
fi

# A package build stages the tree into DESTDIR on a build host that has no
# desktop stack; the runtime requirements belong in the package metadata.
if [ -n "$DESTDIR" ]; then
    MISSING=""
fi

if [ -n "$MISSING" ]; then
    echo ":: ERROR: missing runtime requirements:" >&2
    while IFS= read -r dep; do [ -n "$dep" ] && echo "   - $dep" >&2; done <<<"$MISSING"
    echo ":: Install Quickshell first (the hyprtk installer does this)." >&2
    exit 1
fi

echo ":: Installing $TITLE into $INSTALL_DIR_D ..."
mkdir -p "$INSTALL_DIR_D" "$BIN_DIR_D" "$APPS_DIR_D"
# The staging dir sits beside the final one so `mv` is a rename, never a copy.
stage="${INSTALL_DIR_D}.stage.$$"
rm -rf "$stage"
mkdir -p "$stage"
cp -a "$SCRIPT_DIR/shell.qml" "$stage/"
for d in surface components config theme backend bin data; do
    [ -e "$SCRIPT_DIR/$d" ] || { echo ":: ERROR: missing $d in source tree" >&2; exit 1; }
    cp -a "$SCRIPT_DIR/$d" "$stage/$d"
done
find "$stage" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$stage" -name '*.pyc' -delete 2>/dev/null || true
chmod +x "$stage/bin/$LAUNCHER_NAME"
rm -rf "${INSTALL_DIR_D:?}"
mv "$stage" "$INSTALL_DIR_D"

ln -sf "$INSTALL_DIR/bin/$LAUNCHER_NAME" "$BIN_DIR_D/$LAUNCHER_NAME"
if [ "$SYSTEM_MODE" -eq 0 ] && ! on_path "$BIN_DIR"; then
    echo ":: NOTE: add $BIN_DIR to PATH to use '$LAUNCHER_NAME' directly."
fi

install -Dm644 "$SCRIPT_DIR/data/$APP_NAME.svg" "$INSTALL_DIR_D/$APP_NAME.svg"

if [ "$SYSTEM_MODE" -eq 1 ]; then
    install -Dm755 "$SCRIPT_DIR/bin/hyprtk-sm-helper" "${DESTDIR}${LIBEXEC_DIR}/hyprtk-sm-helper"
    install -Dm644 "$SCRIPT_DIR/data/org.hyprtk.system-manager.policy" \
        "${DESTDIR}${POLICY_DIR}/org.hyprtk.system-manager.policy"
    echo ":: Root helper + polkit policy installed (pkexec path)."
    case "$PREFIX" in
        /usr) ;;
        *) echo ":: NOTE: $POLICY_DIR is not a polkit search path on most systems;"
           echo "::       mount edits will fall back to sudo." ;;
    esac
fi

mkdir -p "$APPS_DIR_D"
if [ -f "$SCRIPT_DIR/data/$APP_NAME.desktop" ]; then
    sed -e "s|^Exec=.*|Exec=\"$BIN_DIR/$LAUNCHER_NAME\" open|" \
        -e "s|^Icon=.*|Icon=$INSTALL_DIR/$APP_NAME.svg|" \
        "$SCRIPT_DIR/data/$APP_NAME.desktop" > "$DESKTOP_FILE"
else
    cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$TITLE
Comment=Configure the hyprtk desktop and the system under it
Exec="$BIN_DIR/$LAUNCHER_NAME" open
Icon=$INSTALL_DIR/$APP_NAME.svg
Terminal=false
Categories=Settings;System;
StartupNotify=true
DESKTOP
fi
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

PYTHONPATH="$INSTALL_DIR_D/backend" PYTHONDONTWRITEBYTECODE=1 \
    python3 -m system_manager.cli version >/dev/null
echo ":: Backend import OK ($(PYTHONPATH="$INSTALL_DIR_D/backend" PYTHONDONTWRITEBYTECODE=1 python3 -m system_manager.cli version))"

echo ":: Installed."
echo ":: Run:       $LAUNCHER_NAME"
echo ":: App:       $INSTALL_DIR_D"
echo ":: Backups:   $STATE_DIR/backups"
echo ":: Uninstall: $0 --uninstall"
