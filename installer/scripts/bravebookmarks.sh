#!/bin/bash
# ----------------------------------------------------- 
#
# by hyprtk (Kori Tk) (2026)
# ----------------------------------------------------- 
# Select a Brave bookmark (gum filter, no rofi).
. "$(dirname "$0")/menu.sh"

selected=$(python3 - <<'PY' | menu_filter "Brave bookmark"
import json
import os

path = os.path.expanduser("~/.config/BraveSoftware/Brave-Browser/Default/Bookmarks")
try:
    data = json.load(open(path))
except Exception:
    raise SystemExit(0)

def walk(node):
    if not isinstance(node, dict):
        return
    if node.get("type") == "url" and node.get("url"):
        print(f"{node.get('name', '')}\t{node['url']}")
    for child in node.get("children") or []:
        walk(child)

roots = data.get("roots") or {}
for key in ("bookmark_bar", "other", "synced"):
    walk(roots.get(key) or {})
PY
)

if [ -n "$selected" ]; then
    url=${selected#*$'\t'}
    [ -n "$url" ] && brave -- "$url"
fi
