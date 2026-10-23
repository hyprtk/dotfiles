#!/usr/bin/env bash
# hyprtk-config-manager installer.
#
# Installs the Quickshell front end + Python backend into the user's data dir,
# links the `config-manager` launcher onto PATH and registers a desktop entry.
# No root is needed and no system packages are modified: Quickshell (`qs`) and a
# Lua interpreter come from the hyprtk suite / your distro.
#
# Usage: ./install.sh             install or update
#        ./install.sh --dry-run   check dependencies, change nothing
#        ./install.sh --uninstall remove the app (keeps your backups)
#        ./install.sh --help      show this message

set -euo pipefail

APP_NAME="hyprtk-config-manager"
LAUNCHER_NAME="config-manager"
TITLE="Hyprland Settings"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/$APP_NAME.desktop"
STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-config-manager"

DRY_RUN=0
DO_UNINSTALL=0

usage() {
    echo "Usage: $0 [--dry-run|--uninstall|--help]"
    echo "  (no args)     Install or update $TITLE."
    echo "  --dry-run     Check requirements and report what is missing; change nothing."
    echo "  --uninstall   Remove the app, launcher and desktop entry (backups are kept)."
}

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        -u|--uninstall) DO_UNINSTALL=1 ;;
        *) echo ":: WARN: unknown option '$arg' (ignored)" >&2 ;;
    esac
done

# Called by hyprtk-merged's installer under HYPRTK_DRYRUN: the package step is
# simulated, so do not fail on (intentionally) missing runtime tools.
if [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: DRYRUN: would install $TITLE into $INSTALL_DIR"
    exit 0
fi

on_path() {
    case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac
}

qs_bin() {
    command -v qs 2>/dev/null || command -v quickshell 2>/dev/null || true
}

lua_bin() {
    command -v lua5.4 2>/dev/null || command -v lua 2>/dev/null \
        || command -v luajit 2>/dev/null || true
}

missing_deps() {
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    [ -n "$(qs_bin)" ] || missing+=("quickshell (qs)")
    [ -n "$(lua_bin)" ] || missing+=("lua5.4 or lua")
    printf '%s\n' "${missing[@]}"
}

if [ "$DO_UNINSTALL" -eq 1 ]; then
    echo ":: Uninstalling $APP_NAME..."
    if [ -L "$BIN_DIR/$LAUNCHER_NAME" ] \
        && [ "$(readlink -f "$BIN_DIR/$LAUNCHER_NAME")" = "$INSTALL_DIR/bin/$LAUNCHER_NAME" ]; then
        rm -f "$BIN_DIR/$LAUNCHER_NAME"
    fi
    if [ -L "/usr/local/bin/$LAUNCHER_NAME" ] \
        && [ "$(readlink -f "/usr/local/bin/$LAUNCHER_NAME")" = "$INSTALL_DIR/bin/$LAUNCHER_NAME" ]; then
        rm -f "/usr/local/bin/$LAUNCHER_NAME" 2>/dev/null \
            || sudo rm -f "/usr/local/bin/$LAUNCHER_NAME" 2>/dev/null || true
    fi
    rm -rf "${INSTALL_DIR:?}"
    rm -f "$DESKTOP_FILE"
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    echo ":: Removed."
    echo ":: Kept backups/state in $STATE_DIR"
    exit 0
fi

MISSING="$(missing_deps)"

if [ "$DRY_RUN" -eq 1 ] || [ "${HYPRTK_DRYRUN:-}" = "1" ]; then
    echo ":: Dry run — nothing will be installed or modified."
    echo ":: Install dir:     $INSTALL_DIR"
    echo ":: Launcher:        $BIN_DIR/$LAUNCHER_NAME"
    echo ":: Desktop entry:   $DESKTOP_FILE"
    printf ':: python3:         %s\n' "$(command -v python3 || echo MISSING)"
    printf ':: Quickshell:      %s\n' "$(qs_bin || echo MISSING)"
    printf ':: Lua:             %s\n' "$(lua_bin || echo MISSING)"
    if [ -n "$MISSING" ]; then
        echo ":: Result: MISSING — $(echo "$MISSING" | tr '\n' ' ')"
        exit 1
    fi
    if on_path "$BIN_DIR"; then
        echo ":: ~/.local/bin on PATH: yes"
    else
        echo ":: ~/.local/bin on PATH: no (the launcher will be linked into /usr/local/bin when possible)"
    fi
    echo ":: Result: ready."
    exit 0
fi

if [ -n "$MISSING" ]; then
    echo ":: ERROR: missing runtime requirements:" >&2
    while IFS= read -r dep; do [ -n "$dep" ] && echo "   - $dep" >&2; done <<<"$MISSING"
    echo ":: Install Quickshell and a Lua interpreter first (the hyprtk installer does this)." >&2
    exit 1
fi

echo ":: Installing $TITLE into $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPS_DIR"

# Stage the full app tree atomically, so an interrupted update never leaves a
# half-written shell behind.
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

# Launcher on PATH.
ln -sf "$INSTALL_DIR/bin/$LAUNCHER_NAME" "$BIN_DIR/$LAUNCHER_NAME"
if ! on_path "$BIN_DIR"; then
    if [ "$(id -u)" -eq 0 ]; then
        ln -sf "$INSTALL_DIR/bin/$LAUNCHER_NAME" "/usr/local/bin/$LAUNCHER_NAME" 2>/dev/null || true
    elif command -v sudo >/dev/null 2>&1; then
        sudo ln -sf "$INSTALL_DIR/bin/$LAUNCHER_NAME" "/usr/local/bin/$LAUNCHER_NAME" 2>/dev/null \
            && echo ":: ~/.local/bin is not on PATH — linked into /usr/local/bin" \
            || echo ":: NOTE: ~/.local/bin is not on PATH; run $INSTALL_DIR/bin/$LAUNCHER_NAME"
    else
        echo ":: NOTE: add $BIN_DIR to PATH to use '$LAUNCHER_NAME' directly."
    fi
fi

# Desktop entry (Exec rewritten to the absolute launcher).
mkdir -p "$APPS_DIR"
if [ -f "$SCRIPT_DIR/data/$APP_NAME.desktop" ]; then
    sed "s|^Exec=.*|Exec=\"$BIN_DIR/$LAUNCHER_NAME\" open|" \
        "$SCRIPT_DIR/data/$APP_NAME.desktop" > "$DESKTOP_FILE"
else
    cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$TITLE
Comment=Configure Hyprland's Lua configuration
Exec="$BIN_DIR/$LAUNCHER_NAME" open
Icon=preferences-system
Terminal=false
Categories=Settings;System;
StartupNotify=true
DESKTOP
fi
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true

# Self-test: import the backend and print the CLI version. A running tree is
# optional — a machine without hyprland.lua can still install the app.
PYTHONPATH="$INSTALL_DIR/backend" python3 -m config_manager.cli version >/dev/null
echo ":: Backend import OK ($(PYTHONPATH="$INSTALL_DIR/backend" python3 -m config_manager.cli version))"

if [ -f "$HOME/.config/hypr/hyprland.lua" ] || [ -f "$HOME/hyprtk/hypr/hyprland.lua" ]; then
    if PYTHONPATH="$INSTALL_DIR/backend" python3 -m config_manager.cli dump --summary >/dev/null 2>&1; then
        echo ":: Live config probe OK"
    else
        echo ":: NOTE: live config probe failed — check the Hyprland Lua tree; the app will report it on open." >&2
    fi
fi

echo ":: Installed."
echo ":: Run:       $LAUNCHER_NAME"
echo ":: Shell:     $INSTALL_DIR"
echo ":: Backups:   $STATE_DIR/backups"
echo ":: Uninstall: $0 --uninstall"
