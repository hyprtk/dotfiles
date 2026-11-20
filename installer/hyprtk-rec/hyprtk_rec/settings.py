"""Persisted preferences: ``$XDG_CONFIG_HOME/hyprtk-rec/config.json``."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .audio import AUDIO
from .recorder import BACKENDS, CODECS, CONTAINERS, QUALITIES
from .sources import SOURCES
from .store import default_dir

APP_DIR = "hyprtk-rec"

DEFAULTS = {
    "source": "output",
    "window": "",             # Hyprland client address picked in the UI; "" = focused
    "fps": 60,
    "codec": "h264",
    "quality": "medium",
    "audio": "none",
    "cursor": True,
    "countdown": 0,
    "dir": "",
    "backend": "auto",
    "container": "mp4",
    "notify": True,
    "recent": 12,
}


def config_dir() -> Path:
    override = os.environ.get("HYPRTK_REC_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / APP_DIR


def config_path() -> Path:
    override = os.environ.get("HYPRTK_REC_CONFIG")
    return Path(override) if override else config_dir() / "config.json"


class Settings:
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
            if key == "source":
                return value if value in SOURCES else default
            if key == "codec":
                return value if value in CODECS else default
            if key == "quality":
                return value if value in QUALITIES else default
            if key == "container":
                return value if value in CONTAINERS else default
            if key == "backend":
                return value if value in BACKENDS else default
            if key == "audio":
                return value if value in AUDIO else default
            if key == "fps":
                return max(5, min(240, int(value)))
            if key == "countdown":
                return max(0, min(30, int(value)))
            if key == "recent":
                return max(0, min(60, int(value)))
            if key == "window":
                return str(value or "").strip()
            if key == "dir":
                text = str(value or "").strip()
                return os.path.expanduser(text) if text else ""
            if isinstance(default, bool):
                return bool(value)
            if isinstance(default, int):
                return int(value)
            return str(value)
        except (TypeError, ValueError):
            return default
