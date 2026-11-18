"""The hyprtk palette, resolved from the running bar theme.

Mirrors ``hyprtk-bar-qt``'s ``resolve_palette`` (and the palette loader the
editor, file manager and terminal share): a pywal-driven dark panel with mauve
(color5) accents and cyan (color6) tints. The calculator maps the same colours
onto the display, the keypad and the operator keys, so a wallpaper change
repaints the whole app.
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


def _rgb(value: str) -> tuple:
    text = value.lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        text = "000000"
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def blend(base: str, other: str, amount: float) -> str:
    """Mix two hex colours; ``amount`` 0 keeps ``base``, 1 is ``other``.

    pywal can return a colour0 that is the same as the background, which would
    make keypad keys invisible. Deriving the surface levels here keeps the QML
    free of colour maths and makes the result testable.
    """
    left, right = _rgb(base), _rgb(other)
    mixed = [
        max(0, min(255, round(left[i] + (right[i] - left[i]) * amount)))
        for i in range(3)
    ]
    return "#%02x%02x%02x" % tuple(mixed)


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

    # Calculator roles, assigned by intent so one mapping works for every
    # wallpaper: digits neutral, operators the bar's mauve accent, the result
    # line the foreground, an error the danger colour.
    palette["display"] = blend(palette["background"], palette["foreground"], 0.05)
    palette["key"] = blend(palette["background"], palette["foreground"], 0.11)
    palette["key_alt"] = blend(palette["background"], palette["foreground"], 0.06)
    palette["key_hover"] = blend(palette["background"], palette["foreground"], 0.18)
    palette["key_operator"] = palette["accent"]
    palette["key_action"] = palette["accent2"]
    palette["result"] = palette["foreground"]
    palette["dim"] = blend(palette["background"], palette["foreground"], 0.55)

    return palette
