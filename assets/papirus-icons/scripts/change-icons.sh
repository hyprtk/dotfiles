#!/usr/bin/env bash
#
# change-icons.sh — recolour Papirus folders to the nearest pywal colour.
#
# Reads pywal's color4 (line 5 of ~/.cache/wal/colors), matches it against every
# folder colour the installed Papirus-Dark theme actually ships (not a
# hard-coded subset), and applies the closest one. Matching is done in CIE
# L*a*b* so neutral wallpapers land on neutral folders instead of drifting to
# whatever saturated pastel is numerically closest in RGB.
#
# Idempotent without a cache: the colour currently linked in the theme is read
# back from disk, so a colour applied externally (Icons page, manual
# papirus-folders, the per-colour helper scripts) is always respected and can
# no longer suppress a needed update.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_FILE="${XDG_CACHE_HOME:-$HOME/.cache}/wal/colors"
OUTPUT_FILE="$SCRIPT_DIR/folder-color.txt"
LINE_NUMBER=5               # pywal line index (1-based, so 5 → color4)
DEFAULT_COLOR="mocha-blue"  # safe fallback when no valid colour is available

PAPIRUS="${PAPIRUS_BIN:-$HOME/.local/share/icons/papirus-folders.sh}"
THEME_DIR="${PAPIRUS_THEME:-${XDG_DATA_HOME:-$HOME/.local/share}/icons/Papirus-Dark}"
STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/hyprtk"
LOCK_FILE="$STATE_DIR/icon-color.lock"

hex=""
target=""

# ── pick the source colour ────────────────────────────────────────────────────
# PAPIRUS_TARGET_HEX overrides the pywal cache (used by test-color.sh, which
# derives its colour from the wallpaper itself rather than color4).
if [ -n "${PAPIRUS_TARGET_HEX:-}" ]; then
    hex="$PAPIRUS_TARGET_HEX"
elif [ -f "$INPUT_FILE" ]; then
    hex=$(sed -n "${LINE_NUMBER}p" "$INPUT_FILE" 2>/dev/null | tr -d '[:space:]')
fi
if [[ ! "$hex" =~ ^#?[0-9A-Fa-f]{6}$ ]]; then
    [ -n "$hex" ] && echo "WARNING: no valid hex ('$hex'), using $DEFAULT_COLOR." >&2
    hex=""
    target="$DEFAULT_COLOR"
fi

# ── palette: every colour the installed theme actually ships ──────────────────
# Names come from the theme's own folder-<colour>-documents.svg symlinks (the
# same source papirus-folders uses), so the currently applied colour is included
# and no external list has to be parsed. The hex for each name is read from that
# theme's folder SVG: Papirus-Dark uses darker shades than the light Papirus
# theme, so hard-coded light hexes would skew the match.
palette() {
    local f name svg col line
    for f in "$THEME_DIR"/48x48/places/folder-*-documents.svg; do
        [ -e "$f" ] || continue
        name=${f##*/}
        name=${name#folder-}
        name=${name%-documents.svg}
        svg="$THEME_DIR/48x48/places/folder-$name.svg"
        [ -f "$svg" ] || continue
        col=""
        while IFS= read -r line; do
            if [[ "$line" =~ fill:(#[0-9A-Fa-f]{6}) ]]; then
                col="${BASH_REMATCH[1]}"
                break
            fi
        done < "$svg"
        [ -n "$col" ] && printf '%s %s\n' "$name" "$col"
    done
}

# ── nearest name by CIE76 distance (sRGB → XYZ D65 → L*a*b*) ──────────────────
nearest() {
    awk -v target="$1" '
    function hexv(c) { return index("0123456789abcdef", tolower(c)) - 1 }
    function byte(h, p) { return 16 * hexv(substr(h, p, 1)) + hexv(substr(h, p + 1, 1)) }
    function lin(v) { v /= 255; return (v <= 0.04045) ? v / 12.92 : exp(2.4 * log((v + 0.055) / 1.055)) }
    function f(t) { return (t > 0.008856) ? exp(log(t) / 3) : 7.787 * t + 16 / 116 }
    function setlab(h) {
        r = lin(byte(h, 2)); g = lin(byte(h, 4)); b = lin(byte(h, 6))
        x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
        y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b)
        z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
        L = 116 * f(y) - 16
        A = 500 * (f(x) - f(y))
        B = 200 * (f(y) - f(z))
    }
    BEGIN { setlab(target); tL = L; tA = A; tB = B; best = 1e18; name = "" }
    NF >= 2 {
        setlab($2)
        d = (L - tL) ^ 2 + (A - tA) ^ 2 + (B - tB) ^ 2
        if (d < best) { best = d; name = $1 }
    }
    END { if (name != "") print name }
    '
}

if [ -n "$hex" ]; then
    target=$(palette | nearest "$hex")
fi
[ -n "$target" ] || target="$DEFAULT_COLOR"

# ── current colour, read straight from the theme (no state file) ──────────────
theme_color() {
    local link
    link=$(readlink -f "$THEME_DIR/48x48/places/folder.svg" 2>/dev/null) || return 1
    link=${link##*/}
    link=${link%.svg}
    link=${link#folder-}
    printf '%s' "$link"
}

# ── apply ─────────────────────────────────────────────────────────────────────
echo "Closest color to ${hex:-<invalid>} is: $target"

# Several consumers react to the same wallpaper change (the awww wrapper →
# wallpaper-colors.sh, the polling wal-watcher.sh, the bar's scripts). Serialise
# them so only one applies; the second sees the new colour and exits.
mkdir -p "$STATE_DIR" 2>/dev/null || true
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE" 2>/dev/null && flock 9 2>/dev/null || true
fi

current=$(theme_color) || current=""
if [ "$target" = "$current" ]; then
    exit 0
fi

if [ ! -x "$PAPIRUS" ]; then
    echo "papirus-folders.sh not found at $PAPIRUS" >&2
    notify-send "Icon colors failed" "papirus-folders not found" || true
    exit 1
fi

if "$PAPIRUS" -C "$target" -t "$THEME_DIR"; then
    printf '%s\n' "$target" > "$OUTPUT_FILE" 2>/dev/null || true
    notify-send "Icon Colors updated" "with $target" || true
else
    notify-send "Icon colors failed" "papirus-folders returned an error" || true
    exit 1
fi
