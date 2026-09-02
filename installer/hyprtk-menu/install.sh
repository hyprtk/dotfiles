#!/usr/bin/env bash
# Install hyprtk-menu to ~/.local/share + ~/.local/bin
set -euo pipefail

APP_NAME="hyprtk-menu"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
BIN="$BIN_DIR/$APP_NAME"

uninstall() {
    rm -rf "$INSTALL_DIR"
    rm -f "$BIN"
    echo "$APP_NAME uninstalled."
}

if [[ "${1:-}" == "--uninstall" || "${1:-}" == "-u" ]]; then
    uninstall
    exit 0
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# Create the Games directory in the user's home (Win7 places shortcut target)
mkdir -p "$HOME/Games"

rm -rf "$INSTALL_DIR/hyprtk_menu"
cp -r "$SRC_DIR/hyprtk_menu" "$INSTALL_DIR/"
rm -rf "$INSTALL_DIR/assets"
cp -r "$SRC_DIR/assets" "$INSTALL_DIR/assets"
cp "$SRC_DIR/main.py" "$INSTALL_DIR/main.py"

cat > "$BIN" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$BIN"

echo "Installed $APP_NAME to $BIN"
echo "Open/toggle with: $BIN [--toggle]"
