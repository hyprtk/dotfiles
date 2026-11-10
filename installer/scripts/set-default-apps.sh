#!/bin/bash
# ── Register the suite's preferred apps with XDG and the bar quick links ─────
# The dotfiles install alacritty, thunar, brave and hyprtk-fm, but a fresh
# distro still points XDG at its own defaults (seen on Fedora: kitty as the
# inode/directory handler, firefox as the browser). Prefer hyprtk-fm for
# inode/directory and point the bar's Files quick link at it; Thunar stays
# installed as a fallback. User-level; best-effort.
#
# The session terminal is $TERMINAL, set in hypr/environment.lua.
set -u

apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
bar_cfg="${XDG_CONFIG_HOME:-$HOME/.config}/hyprtk-bar-qt/config.json"

fm_desktop="thunar.desktop"
if [ -f "$apps_dir/hyprtk-file-manager.desktop" ] || [ -f "/usr/share/applications/hyprtk-file-manager.desktop" ]; then
    fm_desktop="hyprtk-file-manager.desktop"
fi

if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default "$fm_desktop" inode/directory 2>/dev/null || true
fi

if command -v xdg-settings >/dev/null 2>&1; then
    for d in brave-browser.desktop brave.desktop; do
        if [ -f "/usr/share/applications/$d" ]; then
            xdg-settings set default-web-browser "$d" 2>/dev/null || true
            break
        fi
    done
fi

# The bar's "Files" quick link: replace an explicit Thunar command with
# hyprtk-fm (and relabel it), keeping every other link untouched. Back up once.
if [ -f "$bar_cfg" ] && command -v python3 >/dev/null 2>&1; then
    [ -f "$bar_cfg.bak" ] || cp -a "$bar_cfg" "$bar_cfg.bak" 2>/dev/null || true
    python3 - "$bar_cfg" <<'PY'
import json
import os
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except Exception:
    raise SystemExit(0)


def patch(node):
    if isinstance(node, dict):
        if node.get("id") == "files" or node.get("tooltip") == "Files":
            node["command"] = "hyprtk-fm"
            if "label" in node:
                node["label"] = "Files"
        elif node.get("command") == "thunar":
            label = str(node.get("label") or node.get("tooltip") or "").lower()
            if "file" in label or "thunar" in label:
                node["command"] = "hyprtk-fm"
                if "label" in node:
                    node["label"] = "Files"
        for value in list(node.values()):
            patch(value)
    elif isinstance(node, list):
        for value in node:
            patch(value)


patch(data)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
os.replace(tmp, path)
PY
fi

echo "preferred apps registered (file manager: ${fm_desktop%.desktop}; bar quick link: hyprtk-fm; browser: brave if present)"
