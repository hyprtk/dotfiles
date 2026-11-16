#!/bin/bash
#
#                                                      
#  
# by hyprtk (Kori Tk) (2026)
# ----------------------------------------------------- 

# ----------------------------------------------------- 
# Screenshot menu (gum).
. "$(dirname "$0")/menu.sh"

DIR="$HOME/Pictures/screenshots/"
NAME="screenshot_$(date +%d%m%Y_%H%M%S).png"

option2="Selected area"
option3="Fullscreen (delay 3 sec)"

choice=$(printf '%s\n' "$option2" "$option3" | menu_choose "Take Screenshot")

case $choice in
    $option2)
        grim -g "$(slurp)" - | swappy -f -
        # grim -g "$(slurp)" $(xdg-user-dir PICTURES)/screenshots/$(date +'%s_grim.png')
        notify-send "Screenshot created" "Mode: Selected area"
    ;;
    $option3)
        sleep 3
        grim - | swappy -f -
        # grim $(xdg-user-dir PICTURES)/screenshots/$(date +'%s_grim.png')
        notify-send "Screenshot created" "Mode: Fullscreen"
    ;;
esac
