#!/bin/bash
#
# by hyprtk (Kori Tk) (2026)
# ----------------------------------------------------- 
# Select a template and copy it to the clipboard (gum filter).
. "$(dirname "$0")/menu.sh"

selected=$(find "$HOME/private/templates" -maxdepth 1 -type f \
    -printf "%f\n" 2>/dev/null | sort | menu_filter "Select the template")

if [ "$selected" ]; then
    xclip -sel clip "$HOME/private/templates/$selected"
fi
