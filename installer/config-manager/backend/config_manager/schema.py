"""Page and option metadata.

Paths are Lua config key paths rooted at the hl.config table, e.g.
"decoration.rounding" -> hl.config({ decoration = { rounding = 12 } }).
"""

from __future__ import annotations

from typing import Any

# type: bool | int | float | str | enum | color | vec2 | css_gaps | font_weight
PAGES: list[dict[str, Any]] = [
    {
        "id": "animations",
        "title": "Animations",
        "icon": "animation",
        "description": "Curves, per-leaf animation tree, and hyprtk bar animation mirror.",
        "options": [],
    },
    {
        "id": "general",
        "title": "General",
        "icon": "window",
        "description": "Gaps, borders, layout and focus behaviour.",
        "options": [
            {"path": "general.gaps_in", "label": "Inner gaps", "type": "int", "default": 5, "min": 0, "max": 60},
            {"path": "general.gaps_out", "label": "Outer gaps", "type": "int", "default": 20, "min": 0, "max": 120},
            {"path": "general.border_size", "label": "Border size", "type": "int", "default": 2, "min": 0, "max": 20},
            {"path": "general.layout", "label": "Layout", "type": "enum", "default": "dwindle", "choices": ["dwindle", "master"]},
            {"path": "general.resize_on_border", "label": "Resize on border", "type": "bool", "default": False},
            {"path": "general.extend_border_grab_area", "label": "Border grab area", "type": "int", "default": 15, "min": 0, "max": 60},
            {"path": "general.hover_icon_on_border", "label": "Hover icon on border", "type": "bool", "default": True},
            {"path": "general.allow_tearing", "label": "Allow tearing", "type": "bool", "default": False},
            {"path": "general.snap.enabled", "label": "Window snapping", "type": "bool", "default": True},
            {"path": "general.float_gap", "label": "Float gap", "type": "int", "default": 0, "min": 0, "max": 40},
        ],
    },
    {
        "id": "decoration",
        "title": "Decoration",
        "icon": "sparkle",
        "description": "Rounding, opacity, blur, shadow and border colours.",
        "options": [
            {"path": "decoration.rounding", "label": "Rounding", "type": "int", "default": 10, "min": 0, "max": 40},
            {"path": "decoration.active_opacity", "label": "Active opacity", "type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
            {"path": "decoration.inactive_opacity", "label": "Inactive opacity", "type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
            {"path": "decoration.fullscreen_opacity", "label": "Fullscreen opacity", "type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
            {"path": "decoration.dim_inactive", "label": "Dim inactive", "type": "bool", "default": False},
            {"path": "decoration.dim_strength", "label": "Dim strength", "type": "float", "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01},
            {"path": "decoration.blur.enabled", "label": "Blur", "type": "bool", "default": True},
            {"path": "decoration.blur.size", "label": "Blur size", "type": "int", "default": 8, "min": 1, "max": 32},
            {"path": "decoration.blur.passes", "label": "Blur passes", "type": "int", "default": 3, "min": 1, "max": 8},
            {"path": "decoration.shadow.enabled", "label": "Shadow", "type": "bool", "default": True},
            {"path": "decoration.shadow.range", "label": "Shadow range", "type": "int", "default": 20, "min": 0, "max": 100},
            {"path": "decoration.shadow.render_power", "label": "Shadow power", "type": "int", "default": 3, "min": 1, "max": 10},
            {"path": "decoration.shadow.color", "label": "Shadow colour", "type": "color", "default": "rgba(1a1a1aee)"},
            {"path": "decoration.col_blur", "label": "Blur colours", "type": "bool", "default": False},
        ],
    },
    {
        "id": "input",
        "title": "Input",
        "icon": "keyboard",
        "description": "Keyboard, mouse, touchpad and gestures.",
        "options": [
            {"path": "input.kb_layout", "label": "Keyboard layout", "type": "str", "default": "us"},
            {"path": "input.kb_variant", "label": "Variant", "type": "str", "default": ""},
            {"path": "input.kb_options", "label": "Options", "type": "str", "default": ""},
            {"path": "input.numlock_by_default", "label": "Numlock on start", "type": "bool", "default": False},
            {"path": "input.repeat_rate", "label": "Repeat rate", "type": "int", "default": 25, "min": 1, "max": 100},
            {"path": "input.repeat_delay", "label": "Repeat delay", "type": "int", "default": 600, "min": 100, "max": 2000, "step": 10},
            {"path": "input.sensitivity", "label": "Mouse sensitivity", "type": "float", "default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05},
            {"path": "input.accel_profile", "label": "Accel profile", "type": "enum", "default": "", "choices": ["", "flat", "adaptive"]},
            {"path": "input.touchpad.natural_scroll", "label": "Natural scroll", "type": "bool", "default": True},
            {"path": "input.touchpad.tap-to-click", "label": "Tap to click", "type": "bool", "default": True},
            {"path": "input.touchpad.disable_while_typing", "label": "Disable while typing", "type": "bool", "default": True},
            {"path": "input.touchpad.scroll_factor", "label": "Scroll factor", "type": "float", "default": 1.0, "min": 0.1, "max": 3.0, "step": 0.05},
        ],
    },
    {"id": "monitors", "title": "Monitors", "icon": "monitor", "description": "Layout, resolution, scale, VRR, HDR.", "options": []},
    {"id": "keybinds", "title": "Keybinds", "icon": "keys", "description": "Bind editor with key capture.", "options": []},
    {"id": "rules", "title": "Rules", "icon": "rules", "description": "Window, layer and workspace rules.", "options": []},
]

# Animation leaves and their allowed styles (Hyprland 0.55 tree).
ANIMATION_TREE: dict[str, list[str]] = {
    "windows": ["slide", "popin", "slidefade", "gnomed"],
    "windowsIn": ["slide", "popin", "slidefade", "gnomed"],
    "windowsOut": ["slide", "popin", "slidefade", "gnomed"],
    "windowsMove": ["slide", "slidevert"],
    "layers": ["slide", "popin", "fade"],
    "layersIn": ["slide", "popin", "fade"],
    "layersOut": ["slide", "popin", "fade"],
    "fade": [],
    "fadeIn": [],
    "fadeOut": [],
    "fadeSwitch": [],
    "fadeShadow": [],
    "fadeDim": [],
    "fadeLayers": [],
    "fadeLayersIn": [],
    "fadeLayersOut": [],
    "border": [],
    "borderangle": ["loop", "once"],
    "workspaces": ["slide", "slidevert", "fade", "slidefade", "slidefadevert"],
    "specialWorkspace": ["slide", "slidevert", "fade", "slidefade", "slidefadevert"],
    "zoomFactor": [],
    "monitorAdded": [],
}

ANIMATION_FIELDS = [
    {"key": "enabled", "label": "Enabled", "type": "bool"},
    {"key": "speed", "label": "Speed (ds)", "type": "int", "min": 1, "max": 60},
    {"key": "curve", "label": "Curve", "type": "curve"},
    {"key": "style", "label": "Style", "type": "style"},
]


def pages() -> list[dict[str, Any]]:
    return PAGES


def options() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in PAGES:
        for opt in page.get("options", []):
            out.append({**opt, "page": page["id"]})
    return out


def option(path: str) -> dict[str, Any] | None:
    for opt in options():
        if opt["path"] == path:
            return opt
    return None


def schema() -> dict[str, Any]:
    return {
        "pages": pages(),
        "animationFields": ANIMATION_FIELDS,
        "animationTree": ANIMATION_TREE,
    }
