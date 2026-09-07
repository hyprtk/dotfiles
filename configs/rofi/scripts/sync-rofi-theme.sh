#!/bin/bash
# sync-rofi-theme.sh — link the rofi variant to match the current hyprtk-bar theme
#
# The bar's ``theme.source`` selects the rofi variant:
#   pywal   -> hyprtk-pywal (the dynamic pywal variant; re-tints on wallpaper change)
#   waybar  -> the matching imported-theme variant (e.g. hyprtk-aero -> hyprtk-aero.rasi)
#   manual  -> hyprtk (default glass)
# Missing variants fall back to hyprtk.

bar_config="$HOME/.config/hyprtk-bar/config.json"
variant_dir="$HOME/hyprtk/configs/rofi/variants"
symlink="$HOME/hyprtk/configs/rofi/variant.rasi"

theme="hyprtk"

if [ -f "$bar_config" ]; then
    source=$(python3 -c "import json;d=json.load(open('$bar_config'));print(d.get('theme',{}).get('source',''))" 2>/dev/null)
    waybar_theme=$(python3 -c "import json;d=json.load(open('$bar_config'));print(d.get('theme',{}).get('waybar_theme',''))" 2>/dev/null)
    if [ "$source" = "pywal" ]; then
        theme="hyprtk-pywal"
    elif [ -n "$waybar_theme" ]; then
        theme="$waybar_theme"
    fi
fi

theme="${theme%-top}"
theme="${theme%-bottom}"

if [ -f "$variant_dir/$theme.rasi" ]; then
    ln -sf "variants/$theme.rasi" "$symlink"
else
    ln -sf "variants/hyprtk.rasi" "$symlink"
fi
