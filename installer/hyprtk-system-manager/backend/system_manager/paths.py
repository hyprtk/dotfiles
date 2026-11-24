"""Filesystem locations for hyprtk-system-manager."""

from __future__ import annotations

import os
from pathlib import Path

HOME = Path.home()

CONFIG_ROOT = Path(os.environ.get("HYPRTK_SM_STATE", HOME / ".config" / "hyprtk-system-manager"))
BACKUP_ROOT = CONFIG_ROOT / "backups"
UI_STATE = CONFIG_ROOT / "ui.json"
LOG = CONFIG_ROOT / "system-manager.log"

BAR_CONFIG = HOME / ".config" / "hyprtk-bar-qt" / "config.json"
BAR_THEMES = HOME / ".config" / "hyprtk-bar-qt" / "themes"

HYPR_DIRS = (
    HOME / ".config" / "hypr",
    HOME / "hyprtk" / "hypr",
)

GTK3_SETTINGS = HOME / ".config" / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = HOME / ".config" / "gtk-4.0" / "settings.ini"
AUTOSTART_DIR = HOME / ".config" / "autostart"
FONTS_DIR = HOME / ".local" / "share" / "fonts"
WALLPAPER_CACHE = HOME / ".cache" / "wal" / "colors.json"


def hypr_dir() -> Path | None:
    """Return the Hyprland config dir (honours HYPRTK_HYPR_DIR)."""
    override = os.environ.get("HYPRTK_HYPR_DIR")
    if override:
        path = Path(override).expanduser()
        return path if path.is_dir() else None
    for directory in HYPR_DIRS:
        if (directory / "hyprland.lua").is_file():
            return directory
    return None


def monitors_file() -> Path | None:
    root = hypr_dir()
    return (root / "monitors.lua") if root else None


def input_file() -> Path | None:
    root = hypr_dir()
    return (root / "input.lua") if root else None


def ensure_state() -> Path:
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    return CONFIG_ROOT
