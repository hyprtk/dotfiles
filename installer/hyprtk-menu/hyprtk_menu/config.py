"""Configuration persistence for hyprtk-menu."""

import json
import os
from copy import deepcopy

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "hyprtk-menu")
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "hyprtk-menu")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# hyprtk-bar is the theming source of truth: the menu follows the SAME
# theme.source (pywal | waybar | manual) and waybar_theme that the bar uses,
# so the menu and bar share an identical look and feel.
BAR_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".config", "hyprtk-bar", "config.json")
BAR_THEMES_DIR = os.path.join(os.path.expanduser("~"), ".config", "hyprtk-bar", "themes")
PYWAL_PATH = os.path.join(os.path.expanduser("~"), ".cache", "wal", "colors.json")

LAYOUTS = ("whisker", "win7", "win11", "plasma")

DEFAULT_CONFIG = {
    "position": "auto",
    "align": "left",
    "gap_in": 4,     # gap between the menu and the bar when following it (px)
    "gap_out": 5,    # gap between the menu and the screen edge (px)
    "layout": "whisker",
    "width": 920,
    "height": 580,
    "sidebar_width": 180,
    "recents_width": 230,
    "show_recents": True,
    "max_recents": 10,
    "favorites": [],
    "recents": [],
    "power": {
        "lock": "pidof swaylock hyprlock || swaylock || hyprlock",
        "logout": "hyprctl dispatch exit",
        "reboot": "systemctl reboot",
        "shutdown": "systemctl poweroff",
        "suspend": "systemctl suspend",
        "hibernate": "systemctl hibernate",
    },
}


def load_config():
    """Load config, deep-merging with defaults. Reset on corruption."""
    config = deepcopy(DEFAULT_CONFIG)
    if not os.path.exists(CONFIG_FILE):
        return config
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key, value in data.items():
                config[key] = value
            power = data.get("power")
            if isinstance(power, dict):
                config["power"].update(power)
    except (json.JSONDecodeError, OSError, TypeError):
        pass
    return config


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def load_bar_theme() -> dict:
    """The bar's ``theme`` block (source + waybar_theme + manual colors).

    Returns ``{}`` when the bar config can't be read. The menu mirrors the
    bar's theming source so both share the same palette.
    """
    try:
        with open(BAR_CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    theme = data.get("theme")
    return theme if isinstance(theme, dict) else {}


def load_pywal_colors() -> dict | None:
    """Read ~/.cache/wal/colors.json into a ``{name: hex}`` map, or None."""
    try:
        with open(PYWAL_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    out = dict(data.get("colors") or {})
    special = data.get("special") or {}
    out["background"] = special.get("background")
    out["foreground"] = special.get("foreground")
    return out or None
