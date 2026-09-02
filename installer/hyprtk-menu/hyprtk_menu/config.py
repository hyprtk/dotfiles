"""Configuration persistence for hyprtk-menu."""

import json
import os
from copy import deepcopy

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "hyprtk-menu")
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "hyprtk-menu")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

LAYOUTS = ("whisker", "win7", "win11", "plasma")

DEFAULT_CONFIG = {
    "position": "auto",
    "align": "left",
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
