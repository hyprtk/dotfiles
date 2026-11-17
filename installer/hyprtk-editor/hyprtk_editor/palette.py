"""The hyprtk palette, resolved from the running bar theme.

Mirrors ``hyprtk-bar-qt``'s ``resolve_palette`` (and the palette loader shared
by hyprtk-usb / iso-creator): a pywal-driven dark panel with mauve (color5)
accents and cyan (color6) tints. The editor turns the same 16 colours into a
syntax theme, so highlighting follows the wallpaper instead of shipping a
fixed colour scheme.
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

# ANSI fallbacks used when pywal is absent (Catppuccin Mocha-ish, matching the
# bar's stock look).
ANSI_FALLBACK = [
    "#45475a", "#f38ba8", "#a6e3a1", "#f9e2af",
    "#89b4fa", "#c084fc", "#22d3ee", "#bac2de",
    "#585b70", "#f38ba8", "#a6e3a1", "#f9e2af",
    "#89b4fa", "#c084fc", "#22d3ee", "#a6adc8",
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
    # The bar records its active theme here; fall back to the pre-rename path.
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

    # Syntax roles are assigned by intent, not by ANSI slot, so one mapping
    # works for every wallpaper: keywords take the bar's mauve accent, strings
    # its green, numbers its yellow, comments recede into the muted slot.
    palette["syntax"] = {
        "keyword": palette["accent"],
        "name": palette["foreground"],
        "function": palette["accent2"],
        "class": palette["info"],
        "type": palette["info"],
        "builtin": palette["accent2"],
        "constant": palette["warning"],
        "variable": palette["foreground"],
        "string": palette["success"],
        "number": palette["warning"],
        "comment": palette["muted"],
        "operator": palette["muted"],
        "punctuation": palette["foreground"],
        "tag": palette["accent"],
        "attribute": palette["warning"],
        "heading": palette["accent"],
        "link": palette["accent2"],
        "added": palette["success"],
        "deleted": palette["danger"],
        "error": palette["danger"],
        "whitespace": palette["surface_alt"],
    }
    return palette
