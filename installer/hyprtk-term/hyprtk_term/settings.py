"""Settings and their on-disk shape.

``~/.config/hyprtk-term/config.json`` -- the same file the Settings sheet
writes. Values are validated on load so a hand-edited file can never put the
grid into an impossible state.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

DEFAULTS_PATH = ("~/.config/hyprtk-term/config.json")

MONO_FALLBACKS = (
    "JetBrainsMono Nerd Font Mono",
    "JetBrainsMono Nerd Font",
    "CaskaydiaCove Nerd Font Mono",
    "FiraCode Nerd Font",
    "DejaVu Sans Mono",
    "monospace",
)


def config_path() -> str:
    override = os.environ.get("HYPRTK_TERM_CONFIG")
    return os.path.expanduser(override or DEFAULTS_PATH)


@dataclass
class Settings:
    font_family: str = "JetBrainsMono Nerd Font Mono"
    font_size: float = 11.0
    line_height: float = 1.18
    opacity: float = 0.98
    padding: int = 6
    scrollback: int = 10_000
    shell: str = ""
    login_shell: bool = True
    cursor_blink: bool = True
    cursor_shape: str = "block"          # block | underline | bar
    bell: str = "visual"                 # visual | none
    copy_on_select: bool = False
    theme: str = "auto"                  # auto | <pywal palette name> (reserved)

    @classmethod
    def load(cls) -> "Settings":
        data = _read(config_path())
        out = cls()
        out.update(data)
        return out

    def update(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            if not hasattr(self, key):
                continue
            setattr(self, key, _coerce(key, value, getattr(self, key)))

    def save(self) -> None:
        path = config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)

    def as_dict(self) -> dict:
        return asdict(self)

    def argv(self) -> list[str]:
        """Kept for symmetry with the bridge; the shell decides its own flags."""
        return []


def _read(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _coerce(key: str, value, current):
    try:
        if isinstance(current, bool):
            return bool(value)
        if isinstance(current, int):
            return max(0, int(value))
        if isinstance(current, float):
            return float(value)
        if isinstance(current, str):
            return str(value)
    except (TypeError, ValueError):
        return current
    return value


def clamp_font_size(size: float) -> float:
    return max(4.0, min(72.0, float(size)))


def clamp_opacity(value: float) -> float:
    return max(0.35, min(1.0, float(value)))


def clamp_scrollback(value: int) -> int:
    return max(0, min(200_000, int(value)))
