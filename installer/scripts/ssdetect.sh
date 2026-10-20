#!/bin/bash
#
#                                                      
#  
# by hyprtk (Kori Tk) (2026)
# -----------------------------------------------------
# Open the hyprtk screenshot overlay (vendored HyprQuickFrame).
#
# The overlay is a separate one-shot Quickshell instance, so run it detached
# and return: the keybind must not block while the user selects a region. The
# launcher handles the no-freeze fallback for NVIDIA/screencopy failures; there
# is no GPU split here any more.

export PATH="$HOME/.local/bin:$PATH"

LAUNCHER="$HOME/.local/bin/hyprtk-screenshot"
if [ ! -x "$LAUNCHER" ]; then
    LAUNCHER="$HOME/hyprtk/installer/hyprtk-bar-qt/bin/hyprtk-screenshot"
fi

if [ ! -x "$LAUNCHER" ]; then
    echo "ssdetect: hyprtk-screenshot not found — re-run the bar installer." >&2
    command -v notify-send >/dev/null 2>&1 \
        && notify-send -a "Screenshot" "Screenshot unavailable" \
            "hyprtk-screenshot is not installed."
    exit 1
fi

setsid "$LAUNCHER" "$@" >/dev/null 2>&1 < /dev/null &
hyprctl dispatch 'hl.dsp.submap("reset")' >/dev/null 2>&1 || true
