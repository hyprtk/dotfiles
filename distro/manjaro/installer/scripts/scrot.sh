#!/bin/bash
#
# ─────────────────────────────────────────────────────────────────
#   HYPRTK · Screenshot
#   Part of the Hyprtk desktop suite · github.com/hyprtk
# ─────────────────────────────────────────────────────────────────


DIR="$HOME/Pictures/screenshots/"
NAME="screenshot_$(date +%d%m%Y_%H%M%S).png"

option1="Selected window (delay 3 sec)"
option2="Selected area"
option3="Fullscreen (delay 3 sec)"

# gum menu (no rofi); helper lives in the installed dotfiles tree.
if [ -f "$HOME/hyprtk/installer/scripts/menu.sh" ]; then
    . "$HOME/hyprtk/installer/scripts/menu.sh"
else
    echo "menu.sh not found" >&2
    exit 1
fi

choice=$(printf '%s\n' "$option2" "$option3" "$option1" | menu_choose "Take Screenshot")

case $choice in
    $option1)
        scrot $DIR$NAME -d 3 -e 'xclip -selection clipboard -t image/png -i $f' -c -z -u
        notify-send "Screenshot created" "Mode: Selected window"
    ;;
    $option2)
        scrot $DIR$NAME -s -e 'xclip -selection clipboard -t image/png -i $f'
        notify-send "Screenshot created" "Mode: Selected area"
    ;;
    $option3)
        scrot $DIR$NAME -d 3 -e 'xclip -selection clipboard -t image/png -i $f'
        notify-send "Screenshot created" "Mode: Fullscreen"
    ;;
esac
