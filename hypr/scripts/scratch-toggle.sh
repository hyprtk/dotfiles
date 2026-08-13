#!/bin/bash
class="scratchterm"
special_ws="scratch"

if hyprctl clients -j | jq -e ".[] | select(.class == \"$class\" and .workspace.name != \"special:$special_ws\")" > /dev/null 2>&1; then
    hyprctl dispatch movetoworkspace "special:$special_ws,$class"
    hyprctl dispatch togglespecialworkspace "$special_ws"
elif hyprctl clients -j | jq -e ".[] | select(.class == \"$class\")" > /dev/null 2>&1; then
    hyprctl dispatch togglespecialworkspace "$special_ws"
else
    alacritty --class "$class" &
fi
