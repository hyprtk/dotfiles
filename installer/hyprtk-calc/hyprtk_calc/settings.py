"""Persisted preferences: ``$XDG_CONFIG_HOME/hyprtk-calc/config.json``."""

from __future__ import annotations

import json
import os
import tempfile

from .number import DEFAULT_PRECISION, GROUPS, clamp_precision

APP_DIR = "hyprtk-calc"
ANGLES = ("deg", "rad", "grad")
KEYPADS = ("basic", "scientific", "programmer")

DEFAULTS = {
    "precision": DEFAULT_PRECISION,
    "angle": "deg",
    "grouping": "none",
    "keypad": "basic",
    "live": True,          # evaluate while typing
    "show_history": True,
    "history_limit": 500,
    "width": 460,
    "height": 700,
    "font_scale": 1.0,
    "always_on_top": False,
}


def config_dir() -> str:
    override = os.environ.get("HYPRTK_CALC_CONFIG_DIR")
    if override:
        return override
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_DIR)


def config_path() -> str:
    override = os.environ.get("HYPRTK_CALC_CONFIG")
    return override or os.path.join(config_dir(), "config.json")


class Settings:
    """A validated view of the config file; unknown keys are dropped."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or config_path()
        self._values = dict(DEFAULTS)
        self.load()

    # -- io
    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data:
                    self._values[key] = self._clean(key, data[key])

    def save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=directory or ".", prefix=".config.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._values, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    # -- access
    def get(self, key: str, default=None):
        return self._values.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> bool:
        """Set one key; returns whether it changed."""
        if key not in DEFAULTS:
            return False
        cleaned = self._clean(key, value)
        if self._values.get(key) == cleaned:
            return False
        self._values[key] = cleaned
        return True

    def as_dict(self) -> dict:
        return dict(self._values)

    def __getitem__(self, key):
        return self.get(key)

    # -- validation
    @staticmethod
    def _clean(key: str, value):
        default = DEFAULTS[key]
        try:
            if key == "precision":
                return clamp_precision(value)
            if key == "angle":
                text = str(value).lower()
                return text if text in ANGLES else default
            if key == "grouping":
                return value if value in GROUPS else default
            if key == "keypad":
                return value if value in KEYPADS else default
            if key == "history_limit":
                return max(20, min(5000, int(value)))
            if key == "width":
                # A calculator, not a spreadsheet. The cap also protects the
                # saved size from a tiled launch: Hyprland gives the window the
                # whole work area until a window rule floats it, and that size
                # would otherwise become the default on the next start.
                return max(320, min(1200, int(value)))
            if key == "height":
                return max(400, min(1400, int(value)))
            if key == "font_scale":
                return max(0.7, min(2.0, round(float(value), 2)))
            if isinstance(default, bool):
                return bool(value)
            return value
        except (TypeError, ValueError):
            return default
