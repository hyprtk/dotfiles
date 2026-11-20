"""Persisted preferences: ``$XDG_CONFIG_HOME/hyprtk-shot/config.json``."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .annotate import PALETTE, TOOLS
from .capture import MODES
from .store import default_dir

APP_DIR = "hyprtk-shot"

DEFAULTS = {
    "mode": "region",
    "picker": "overlay",     # region selection: frozen overlay, or slurp (cross-output)
    "delay": 0,              # seconds before the freeze
    "copy": True,            # copy after saving
    "save": True,            # write a file at all
    "dir": "",               # empty = ~/Pictures/Screenshots
    "format": "png",
    "quality": 92,
    "cursor": False,
    "annotate": True,        # open the overlay editor after capturing
    "dim": 0.55,             # how far the outside of the selection is darkened
    "tool": "cursor",
    "color": PALETTE[0],
    "stroke": 4.0,
    "recent": 12,
    "notify": True,
}


def config_dir() -> Path:
    override = os.environ.get("HYPRTK_SHOT_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / APP_DIR


def config_path() -> Path:
    override = os.environ.get("HYPRTK_SHOT_CONFIG")
    return Path(override) if override else config_dir() / "config.json"


class Settings:
    """A validated view of the config file; unknown keys are dropped."""

    def __init__(self, path: str | os.PathLike | None = None) -> None:
        self.path = Path(path) if path else config_path()
        self._values = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            with self.path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data:
                    self._values[key] = self._clean(key, data[key])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self._values, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.path)

    def get(self, key: str, default=None):
        return self._values.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> bool:
        if key not in DEFAULTS:
            return False
        cleaned = self._clean(key, value)
        if self._values.get(key) == cleaned:
            return False
        self._values[key] = cleaned
        return True

    def as_dict(self) -> dict:
        values = dict(self._values)
        if not values.get("dir"):
            values["dir"] = str(default_dir())
        return values

    def __getitem__(self, key):
        return self.get(key)

    @staticmethod
    def _clean(key: str, value):
        default = DEFAULTS[key]
        try:
            if key == "mode":
                return value if value in MODES else default
            if key == "picker":
                return value if value in ("overlay", "slurp") else default
            if key == "delay":
                return max(0, min(30, int(value)))
            if key == "format":
                return value if value in ("png", "jpg", "webp") else default
            if key == "quality":
                return max(40, min(100, int(value)))
            if key == "dim":
                return max(0.0, min(0.9, round(float(value), 2)))
            if key == "tool":
                return value if value in TOOLS else default
            if key == "color":
                text = str(value)
                return text if text.startswith("#") and len(text) in (4, 7, 9) else default
            if key == "stroke":
                return max(1.0, min(24.0, round(float(value), 1)))
            if key == "recent":
                return max(0, min(60, int(value)))
            if key == "dir":
                text = str(value or "").strip()
                return os.path.expanduser(text) if text else ""
            if isinstance(default, bool):
                return bool(value)
            if isinstance(default, int):
                return int(value)
            if isinstance(default, float):
                return float(value)
            return str(value)
        except (TypeError, ValueError):
            return default
