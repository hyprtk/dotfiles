#!/bin/bash
#
#
# by hyprtk (Kori Tk) (2026)
# ----------------------------------------------------- 
# Select wallpaper (gum; menu.sh re-opens this in a floating terminal when
# launched from a keybind).
# ----------------------------------------------------- 
. "$(dirname "$0")/menu.sh"
selected=$(find "$HOME/Pictures/Wallpapers" -maxdepth 1 -type f \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.webp" \) \
    -printf "%f\n" 2>/dev/null | sort | menu_filter "Wallpaper")

if [ "$selected" ]; then

    echo "Changing theme..."
    # ----------------------------------------------------- 
    # Update wallpaper with pywal16
    # ----------------------------------------------------- 
    wal -q -i "$HOME/Pictures/Wallpapers/$selected" 

    # ----------------------------------------------------- 
    # Read the selected wallpaper from pywal's JSON (never `source` colors.sh:
    # it embeds the raw filename and is injectable).
    # ----------------------------------------------------- 
    wallpaper="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("wallpaper",""))' "$HOME/.cache/wal/colors.json" 2>/dev/null)"

    # ----------------------------------------------------- 
    # Copy selected wallpaper into .cache folder
    # ----------------------------------------------------- 
    [ -f "$wallpaper" ] && cp "$wallpaper" ~/.cache/current-wallpaper.png

    newwall=$(basename "$wallpaper")

    # ----------------------------------------------------- 
    # Set the new wallpaper
    # ----------------------------------------------------- 
    awww img "$wallpaper" \
        --transition-bezier .43,1.19,1,.4 \
        --transition-fps=60 \
        --transition-type="random" \
        --transition-duration=0.7 \
        --transition-pos "$( hyprctl cursorpos )"

    ~/hyprtk/assets/papirus-icons/scripts/change-icons.sh

    # ----------------------------------------------------- 
    # Send notification
    # ----------------------------------------------------- 
    notify-send "Colors and Wallpaper updated" "with image $newwall"

    echo "Done."
fi
