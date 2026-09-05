#!/bin/bash
# sync-rofi-theme.sh — link the rofi variant to match the current hyprtk-bar theme

bar_config="$HOME/.config/hyprtk-bar/config.json"
variant_dir="$HOME/hyprtk/configs/rofi/variants"
symlink="$HOME/hyprtk/configs/rofi/variant.rasi"

theme="hyprtk"

if [ -f "$bar_config" ]; then
    waybar_theme=$(python3 -c "import json;d=json.load(open('$bar_config'));print(d.get('theme',{}).get('waybar_theme',''))" 2>/dev/null)
    [ -n "$waybar_theme" ] && theme="$waybar_theme"
fi

theme="${theme%-top}"
theme="${theme%-bottom}"

if [ -f "$variant_dir/$theme.rasi" ]; then
    ln -sf "variants/$theme.rasi" "$symlink"
else
    ln -sf "variants/hyprtk.rasi" "$symlink"
fi
