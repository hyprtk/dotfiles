#!/bin/bash
#
#
# by hyprtk (Kori Tk) (2026)
# ----------------------------------------------------- 
# Pick an icon-color helper script (gum).
. "$(dirname "$0")/menu.sh"

SCRIPT_DIR="$HOME/hyprtk/assets/papirus-icons/scripts"
selected=$(find "$SCRIPT_DIR" -maxdepth 1 -type f -name "*.sh" -printf "%f\n" 2>/dev/null \
    | sort | menu_choose "Run Script")
[ -n "$selected" ] && bash "$SCRIPT_DIR/$selected"
