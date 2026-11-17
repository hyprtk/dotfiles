"""Preferences for hyprtk-editor.

One JSON file under ``$XDG_CONFIG_HOME/hyprtk-editor/config.json``. Every key
has a default, so a partial or corrupt file never breaks startup; unknown keys
are preserved so a newer build can read an older config back.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Font families are tried in order; the first installed one wins in the QML
# FontLoader fallback chain (QML takes a single family, so the app resolves the
# first available name here and exposes it as `font_family`).
MONO_FAMILIES = (
    "JetBrainsMono Nerd Font Mono",
    "Fira Code",
    "FiraCode Nerd Font Mono",
    "Cascadia Code",
    "Source Code Pro",
    "DejaVu Sans Mono",
    "monospace",
)

DEFAULTS: dict = {
    "font_family": "",          # "" = auto-pick from MONO_FAMILIES
    "font_size": 13,
    "tab_width": 4,
    "insert_spaces": True,
    "wrap": False,
    "line_numbers": True,
    "highlight_current_line": True,
    "match_brackets": True,
    "minimap": True,
    "syntax": True,
    "git_gutter": True,
    "print_colour": True,
    "restore_session": True,
    "autosave_seconds": 5,
    "trim_trailing_on_save": False,
    "recent": [],               # most recent first, max 20
    "window": {"width": 1100, "height": 720},
    "search": {"case": False, "word": False, "regex": False},
    "last_open_dir": "",
}


def config_home() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "hyprtk-editor"


def cache_home() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "hyprtk-editor"


def state_home() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "hyprtk-editor"


def _merge(base: dict, over: dict) -> dict:
    """Deep-merge ``over`` into ``base`` without dropping unknown keys."""
    out = dict(base)
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config_home() / "config.json")
        self.data = dict(DEFAULTS)
        self.load()

    # -- io ---------------------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        self.data = _merge(DEFAULTS, raw if isinstance(raw, dict) else {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".config-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # -- access -----------------------------------------------------------
    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    def update(self, values: dict) -> None:
        if not isinstance(values, dict):
            return
        self.data = _merge(self.data, values)
        self.save()

    def as_dict(self) -> dict:
        return dict(self.data)

    # -- conveniences -----------------------------------------------------
    def resolved_font(self) -> str:
        chosen = str(self.get("font_family") or "").strip()
        if chosen:
            return chosen
        from PySide6.QtGui import QFontDatabase

        families = set(QFontDatabase.families())
        for name in MONO_FAMILIES:
            if name in families:
                return name
        return "monospace"

    def add_recent(self, path: str) -> None:
        path = str(path)
        recent = [p for p in (self.get("recent") or []) if p != path]
        recent.insert(0, path)
        self.data["recent"] = recent[:20]
        self.save()

    def clear_recent(self) -> None:
        self.data["recent"] = []
        self.save()
