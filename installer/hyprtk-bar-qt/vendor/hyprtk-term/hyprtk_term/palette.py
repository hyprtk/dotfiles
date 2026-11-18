"""The hyprtk palette, resolved from the running bar theme.

This is the same loader the editor and the bar use: a pywal-driven dark panel
with mauve (color5) accents and cyan (color6) tints. The terminal needs two
things from it -- the sixteen ANSI slots (so `ls`, `vim` and `git` look like the
rest of the desktop) and the UI tokens for the tab strip and the cursor.
"""

from __future__ import annotations

import json
import os

FALLBACK = {
    "background": "#1e1e2e",
    "foreground": "#e5e7eb",
    "surface": "#313244",
    "surface_alt": "#45475a",
    "muted": "#a6adc8",
    "accent": "#c084fc",
    "accent2": "#22d3ee",
    "danger": "#f38ba8",
    "warning": "#f9e2af",
    "success": "#a6e3a1",
    "info": "#89b4fa",
    "border": "#585b70",
    "text_on_accent": "#11111b",
}

# Catppuccin Mocha-ish, matching the bar's stock look when pywal is absent.
ANSI_FALLBACK = [
    "#45475a", "#f38ba8", "#a6e3a1", "#f9e2af",
    "#89b4fa", "#c084fc", "#22d3ee", "#bac2de",
    "#585b70", "#f38ba8", "#a6e3a1", "#f9e2af",
    "#89b4fa", "#c084fc", "#22d3ee", "#a6adca",
]


def _home() -> str:
    return os.environ.get("HYPRTK_WAL_HOME") or os.path.expanduser("~")


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _bar_config() -> dict:
    home = os.path.expanduser("~")
    for rel in (".config/hyprtk-bar-qt/config.json", ".config/hyprtk-bar/config.json"):
        data = _read_json(os.path.join(home, rel))
        if data:
            return data
    return {}


def _is_hex(value) -> bool:
    return isinstance(value, str) and value.startswith("#") and len(value) in (4, 7, 9)


def resolve() -> dict:
    bar = _bar_config()
    theme = bar.get("theme") or {}
    source = str(theme.get("source") or "pywal")

    wal = _read_json(os.path.join(_home(), ".cache", "wal", "colors.json"))
    wal_colors = wal.get("colors") or {}
    wal_special = wal.get("special") or {}

    ansi = []
    for i in range(16):
        value = wal_colors.get(f"color{i}")
        ansi.append(value if _is_hex(value) else ANSI_FALLBACK[i])

    def col(key: str, fallback: str) -> str:
        value = wal_colors.get(key)
        return value if _is_hex(value) else fallback

    def special(key: str, fallback: str) -> str:
        value = wal_special.get(key)
        return value if _is_hex(value) else fallback

    palette = dict(FALLBACK)
    palette["accent"] = theme.get("accent") if _is_hex(theme.get("accent")) else FALLBACK["accent"]
    palette["background"] = (
        theme.get("background") if _is_hex(theme.get("background")) else FALLBACK["background"]
    )
    palette["foreground"] = (
        theme.get("foreground") if _is_hex(theme.get("foreground")) else FALLBACK["foreground"]
    )

    if source == "pywal":
        palette["background"] = special("background", palette["background"])
        palette["foreground"] = special("foreground", palette["foreground"])
        palette["accent"] = col("color5", col("color4", palette["accent"]))

    palette["accent2"] = col("color6", FALLBACK["accent2"])
    palette["danger"] = col("color1", FALLBACK["danger"])
    palette["warning"] = col("color3", FALLBACK["warning"])
    palette["success"] = col("color2", FALLBACK["success"])
    palette["info"] = col("color4", FALLBACK["info"])
    palette["surface"] = col("color0", FALLBACK["surface"])
    palette["surface_alt"] = col("color8", FALLBACK["surface_alt"])
    palette["muted"] = col("color7", FALLBACK["muted"])
    palette["border"] = col("color8", FALLBACK["border"])
    palette["text_on_accent"] = palette["background"]

    try:
        palette["opacity"] = float(bar.get("opacity", 0.98))
    except (TypeError, ValueError):
        palette["opacity"] = 0.98
    palette["theme_name"] = str(theme.get("theme_name") or "")
    palette["source"] = source
    palette["ansi"] = ansi

    # The terminal's own accent roles, assigned by intent so one mapping works
    # for every wallpaper.
    palette["cursor"] = palette["accent"]
    palette["selection"] = palette["accent2"]
    palette["search"] = palette["warning"]
    return palette


def hex_to_int(value, fallback: int = 0xFFFFFF) -> int:
    """``#rrggbb`` (or ``#rgb`` / ``#rrggbbaa``, or a QColor) to 0xRRGGBB."""
    if not isinstance(value, str):
        try:                                   # QColor arriving from QML
            return (value.red() << 16) | (value.green() << 8) | value.blue()
        except Exception:
            return fallback
    if not value.startswith("#"):
        return fallback
    digits = value[1:]
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    if len(digits) == 8:
        digits = digits[:6]
    try:
        return int(digits, 16)
    except ValueError:
        return fallback
