#!/bin/bash
# Install hyprtk-menu (vendored app) to ~/.local/share/hyprtk-menu.
# The launcher wrapper lives in installer/standalone/ (symlinked into ~/.local/bin
# by the `_installSymLink standalone` step), so no wrapper is written here.
set -euo pipefail

APP_NAME="hyprtk-menu"
SRC_DIR="$HOME/hyprtk/installer/hyprtk-menu"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"

uninstall() {
    rm -rf "$INSTALL_DIR"
    echo "$APP_NAME payload removed."
}

if [[ "${1:-}" == "--uninstall" || "${1:-}" == "-u" ]]; then
    uninstall
    exit 0
fi

if [ ! -d "$SRC_DIR" ]; then
    echo "ERROR: vendored app not found at $SRC_DIR"
    exit 1
fi

mkdir -p "$INSTALL_DIR"

rm -rf "$INSTALL_DIR/hyprtk_menu"
cp -r "$SRC_DIR/hyprtk_menu" "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/assets"
cp "$SRC_DIR"/assets/* "$INSTALL_DIR/assets/"
cp "$SRC_DIR/main.py" "$INSTALL_DIR/main.py"

echo "Installed $APP_NAME payload to $INSTALL_DIR"
echo "Open/toggle with: ~/.local/bin/hyprtk-menu [--toggle]"
