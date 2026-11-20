#!/bin/bash
#
#                                                      
#  
# by hyprtk (Kori Tk) (2026)
# -----------------------------------------------------
# Open the hyprtk screenshot overlay.
#
# hyprtk-shot is the suite's screenshot tool (frozen overlay, in-app annotation).
# This script stays as the stable entry point for anything still calling it:
# it prefers hyprtk-shot and falls back to the vendored HyprQuickFrame overlay
# for one release while the new app settles in.
#
# The overlay is a separate one-shot window, so run it detached and return: the
# keybind must not block while the user selects a region.

export PATH="$HOME/.local/bin:$PATH"

SHOT="$HOME/.local/bin/hyprtk-shot"
if [ -x "$SHOT" ]; then
    setsid "$SHOT" region "$@" >/dev/null 2>&1 < /dev/null &
    hyprctl dispatch 'hl.dsp.submap("reset")' >/dev/null 2>&1 || true
    exit 0
fi

LAUNCHER="$HOME/.local/bin/hyprtk-screenshot"
if [ ! -x "$LAUNCHER" ]; then
    LAUNCHER="$HOME/hyprtk/installer/hyprtk-bar-qt/bin/hyprtk-screenshot"
fi

if [ ! -x "$LAUNCHER" ]; then
    echo "ssdetect: neither hyprtk-shot nor hyprtk-screenshot found — re-run the installer." >&2
    command -v notify-send >/dev/null 2>&1 \
        && notify-send -a "Screenshot" "Screenshot unavailable" \
            "hyprtk-shot is not installed."
    exit 1
fi

setsid "$LAUNCHER" "$@" >/dev/null 2>&1 < /dev/null &
hyprctl dispatch 'hl.dsp.submap("reset")' >/dev/null 2>&1 || true
