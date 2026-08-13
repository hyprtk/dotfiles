#!/bin/bash
# hyprlock_wall.sh - Update hyprlock wallpaper
# Copies the current wallpaper to the hyprlock cache location

WALLPAPER="$1"

if [ -z "$WALLPAPER" ] || [ ! -f "$WALLPAPER" ]; then
    echo "Usage: $0 <wallpaper-path>"
    exit 1
fi

mkdir -p ~/.cache
cp "$WALLPAPER" ~/.cache/current_wallpaper.png 2>/dev/null

exit 0
