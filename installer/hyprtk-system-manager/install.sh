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

usage() {
    echo "Usage: $0 [--system] [--dry-run|--uninstall|--help]"
    echo "  (no args)     Install or update $TITLE for the current user."
    echo "  --system      Install under /usr/local (used by the ISO)."
    echo "  --dry-run     Check requirements and report what is missing; change nothing."
    echo "  --uninstall   Remove the app, launcher and desktop entry (backups are kept)."
}

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --system) SYSTEM_MODE=1 ;;
        -u|--uninstall) DO_UNINSTALL=1 ;;
        *) echo ":: WARN: unknown option '$arg' (ignored)" >&2 ;;
    esac
done

if [ "$SYSTEM_MODE" -eq 1 ]; then
    INSTALL_DIR="/usr/local/share/$APP_NAME"
    BIN_DIR="/usr/local/bin"
    APPS_DIR="/usr/local/share/applications"
    STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-system-manager"
else
    INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
    BIN_DIR="$HOME/.local/bin"
    APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-system-manager"
fi
DESKTOP_FILE="$APPS_DIR/$APP_NAME.desktop"

if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install $TITLE into $INSTALL_DIR"
    exit 0
fi

# Root is required only for --system.
if [ "$SYSTEM_MODE" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
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
        && [ "$(readlink -f "$BIN_DIR/$LAUNCHER_NAME")" = "$INSTALL_DIR/bin/$LAUNCHER_NAME" ]; then
        rm -f "$BIN_DIR/$LAUNCHER_NAME"
    fi
    rm -rf "${INSTALL_DIR:?}"
    rm -f "$DESKTOP_FILE"
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    echo ":: Removed."
    echo ":: Kept backups in $STATE_DIR"
    exit 0
fi

MISSING="$(missing_deps)"

if [ "$DRY_RUN" -eq 1 ]; then
    echo ":: Dry run — nothing will be installed or modified."
    echo ":: Mode:            $([ "$SYSTEM_MODE" -eq 1 ] && echo system || echo user)"
    echo ":: Install dir:     $INSTALL_DIR"
    echo ":: Launcher:        $BIN_DIR/$LAUNCHER_NAME"
    echo ":: Desktop entry:   $DESKTOP_FILE"
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

if [ -n "$MISSING" ]; then
    echo ":: ERROR: missing runtime requirements:" >&2
    while IFS= read -r dep; do [ -n "$dep" ] && echo "   - $dep" >&2; done <<<"$MISSING"
    echo ":: Install Quickshell first (the hyprtk installer does this)." >&2
    exit 1
fi

echo ":: Installing $TITLE into $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPS_DIR"

stage="${INSTALL_DIR}.stage.$$"
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
rm -rf "${INSTALL_DIR:?}"
mv "$stage" "$INSTALL_DIR"

ln -sf "$INSTALL_DIR/bin/$LAUNCHER_NAME" "$BIN_DIR/$LAUNCHER_NAME"
if [ "$SYSTEM_MODE" -eq 0 ] && ! on_path "$BIN_DIR"; then
    echo ":: NOTE: add $BIN_DIR to PATH to use '$LAUNCHER_NAME' directly."
fi

install -Dm644 "$SCRIPT_DIR/data/$APP_NAME.svg" "$INSTALL_DIR/$APP_NAME.svg"

mkdir -p "$APPS_DIR"
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

PYTHONPATH="$INSTALL_DIR/backend" python3 -m system_manager.cli version >/dev/null
echo ":: Backend import OK ($(PYTHONPATH="$INSTALL_DIR/backend" python3 -m system_manager.cli version))"

echo ":: Installed."
echo ":: Run:       $LAUNCHER_NAME"
echo ":: App:       $INSTALL_DIR"
echo ":: Backups:   $STATE_DIR/backups"
echo ":: Uninstall: $0 --uninstall"
