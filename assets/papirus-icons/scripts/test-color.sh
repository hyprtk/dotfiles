#!/usr/bin/env bash
#
# test-color.sh — recolour Papirus folders to the dominant wallpaper colour.
#
# Differs from change-icons.sh only in the colour it starts from: this uses the
# most frequent colour in the current wallpaper (ImageMagick histogram) instead
# of pywal's color4. The palette + nearest-colour match is delegated to
# change-icons.sh so both paths always agree.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WALLPAPER=$(head -n1 "${XDG_CACHE_HOME:-$HOME/.cache}/wal/wal" 2>/dev/null)

if [ ! -f "$WALLPAPER" ]; then
    echo "ERROR: Wallpaper file not found: $WALLPAPER"
    exit 1
fi

# Reduce to 16 colours and take the most frequent one; fall back to the average
# colour (1x1 pixel) if the histogram is unavailable.
get_dominant_color() {
    local img="$1" hist top hex avg
    hist=$(magick "$img" -colors 16 -format "%c" histogram:info: 2>/dev/null)
    if [ -n "$hist" ]; then
        top=$(printf '%s\n' "$hist" | sort -nr | head -n1)
        hex=$(printf '%s\n' "$top" | grep -o '#[0-9A-Fa-f]\{6\}' | head -n1)
    fi
    if [ -z "${hex:-}" ]; then
        avg=$(magick "$img" -resize 1x1! -format "%[pixel:p{0,0}]" info: 2>/dev/null)
        hex=$(printf '%s\n' "$avg" | grep -o '#[0-9A-Fa-f]\{6\}' | head -n1)
    fi
    printf '%s' "${hex:-}"
}

DOMINANT_HEX=$(get_dominant_color "$WALLPAPER")
if [ -z "$DOMINANT_HEX" ]; then
    echo "ERROR: Could not extract a dominant colour from the wallpaper."
    exit 1
fi
echo "Dominant colour: $DOMINANT_HEX"

PAPIRUS_TARGET_HEX="$DOMINANT_HEX" exec bash "$SCRIPT_DIR/change-icons.sh"
