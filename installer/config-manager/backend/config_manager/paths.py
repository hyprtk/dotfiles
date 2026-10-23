"""Filesystem locations for hyprtk-config-manager."""

from __future__ import annotations

import os
from pathlib import Path

HYPR_DIRS = (
    Path.home() / ".config" / "hypr",
    Path.home() / "hyprtk" / "hypr",
)

STATE_ROOT = Path.home() / ".config" / "hyprtk-config-manager"
BACKUP_ROOT = STATE_ROOT / "backups"

BAR_CONFIG = Path.home() / ".config" / "hyprtk-bar-qt" / "config.json"


def find_hypr_dir() -> Path | None:
    """Return the Hyprland config dir, honouring HYPR_CM_DIR."""
    override = os.environ.get("HYPR_CM_DIR")
    if override:
        p = Path(override).expanduser()
        return p if (p / "hyprland.lua").is_file() else None
    for d in HYPR_DIRS:
        if (d / "hyprland.lua").is_file():
            return d
    return None


def main_file(root: Path) -> Path:
    return root / "hyprland.lua"


def is_lua_config(root: Path | None) -> bool:
    return root is not None and (root / "hyprland.lua").is_file()
