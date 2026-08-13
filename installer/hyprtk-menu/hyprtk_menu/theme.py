"""CSS assembly for hyprtk-menu — pywal colors + base glass theme."""

import os
import re

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk

from . import config as cfg

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_CSS = os.path.join(BASE_DIR, "assets", "style.css")
WAL_COLORS_SH = os.path.expanduser("~/.cache/wal/colors.sh")
THEME_FILE = os.path.expanduser("~/.cache/.themestyle.sh")

LAYOUT_ICONS = {
    "whisker": "\uf0ca",
    "win7": "\uf108",
    "win11": "\uf108",
    "plasma": "\uf042",
}
LAYOUT_ORDER = list(cfg.LAYOUTS)

# Waybar-theme profiles: semantic token overrides so the menu matches the
# active waybar theme. Accents stay pywal (@color5 mauve / @color6 cyan).
# Token names must match the @define-color defaults in assets/style.css.
PROFILES = {
    "default": {  # hyprtk dark frosted
        "panel_bg": "rgba(10, 10, 20, 0.88)",
        "panel_border": "rgba(255, 255, 255, 0.10)",
        "text": "@foreground",
        "muted": "alpha(@foreground, 0.6)",
        "selected_text": "#ffffff",
        "surface": "rgba(255, 255, 255, 0.05)",
        "selected_bg": "alpha(@color5, 0.28)",
        "selected_border": "alpha(@color5, 0.5)",
        "input_bg": "rgba(255, 255, 255, 0.05)",
        "input_border": "rgba(255, 255, 255, 0.14)",
    },
    "hyprtk-aero": {  # neutral dark glass, white borders, pywal accents
        "panel_bg": "rgba(10, 10, 20, 0.88)",
        "panel_border": "alpha(#ffffff, 0.25)",
        "text": "#ffffff",
        "muted": "alpha(#ffffff, 0.65)",
        "selected_text": "#ffffff",
        "surface": "alpha(#ffffff, 0.06)",
        "selected_bg": "alpha(@color5, 0.3)",
        "selected_border": "alpha(#ffffff, 0.35)",
        "input_bg": "alpha(#ffffff, 0.05)",
        "input_border": "alpha(#ffffff, 0.25)",
    },
    "hyprtk-clear": {  # transparent bar, dark glass pills, light text
        "panel_bg": "rgba(10, 10, 20, 0.78)",
        "panel_border": "rgba(255, 255, 255, 0.08)",
        "text": "rgba(220, 220, 235, 0.95)",
        "muted": "rgba(220, 220, 235, 0.6)",
        "selected_text": "#ffffff",
        "surface": "rgba(255, 255, 255, 0.05)",
        "selected_bg": "alpha(@color5, 0.28)",
        "selected_border": "alpha(@color5, 0.5)",
        "input_bg": "rgba(255, 255, 255, 0.05)",
        "input_border": "rgba(255, 255, 255, 0.14)",
    },
    "hyprtk-glass": {  # transparent bar, sapphire border, muted text
        "panel_bg": "rgba(10, 10, 20, 0.72)",
        "panel_border": "alpha(@color4, 0.4)",
        "text": "rgba(200, 200, 210, 0.9)",
        "muted": "rgba(180, 180, 190, 0.6)",
        "selected_text": "#ffffff",
        "surface": "rgba(255, 255, 255, 0.05)",
        "selected_bg": "alpha(@color6, 0.14)",
        "selected_border": "alpha(@color4, 0.5)",
        "input_bg": "rgba(255, 255, 255, 0.05)",
        "input_border": "alpha(@color4, 0.3)",
    },
    "hyprtk-inverse": {  # transparent bar, dark glass pills, light text + pywal accents
        "panel_bg": "rgba(20, 20, 30, 0.82)",
        "panel_border": "rgba(255, 255, 255, 0.08)",
        "text": "rgba(220, 220, 235, 0.92)",
        "muted": "rgba(220, 220, 235, 0.6)",
        "selected_text": "#ffffff",
        "surface": "rgba(255, 255, 255, 0.06)",
        "selected_bg": "alpha(@color5, 0.28)",
        "selected_border": "alpha(@color5, 0.5)",
        "input_bg": "rgba(255, 255, 255, 0.06)",
        "input_border": "rgba(255, 255, 255, 0.14)",
    },
    "hyprtk-light": {  # light frosted, white glass pills, dark text
        "panel_bg": "rgba(255, 255, 255, 0.82)",
        "panel_border": "rgba(255, 255, 255, 0.5)",
        "text": "rgba(20, 20, 30, 0.95)",
        "muted": "rgba(20, 20, 30, 0.6)",
        "selected_text": "#111111",
        "surface": "rgba(255, 255, 255, 0.35)",
        "selected_bg": "alpha(@color5, 0.3)",
        "selected_border": "alpha(@color5, 0.5)",
        "input_bg": "rgba(255, 255, 255, 0.45)",
        "input_border": "rgba(0, 0, 0, 0.15)",
    },
    "hyprtk-negative": {  # photo-negative light bar (hardcoded light like waybar)
        "panel_bg": "rgba(250, 250, 240, 0.88)",
        "panel_border": "rgba(0, 0, 0, 0.12)",
        "text": "rgba(35, 35, 20, 0.95)",
        "muted": "rgba(35, 35, 20, 0.6)",
        "selected_text": "#000000",
        "surface": "rgba(0, 0, 0, 0.06)",
        "selected_bg": "rgba(0, 0, 0, 0.12)",
        "selected_border": "rgba(0, 0, 0, 0.22)",
        "input_bg": "rgba(0, 0, 0, 0.04)",
        "input_border": "rgba(0, 0, 0, 0.12)",
    },
    "hyprtk-reverse": {  # light frosted, white glass pills, solid pywal accents
        "panel_bg": "rgba(255, 255, 255, 0.82)",
        "panel_border": "rgba(255, 255, 255, 0.45)",
        "text": "rgba(20, 20, 30, 0.95)",
        "muted": "rgba(20, 20, 30, 0.6)",
        "selected_text": "#ffffff",
        "surface": "rgba(255, 255, 255, 0.4)",
        "selected_bg": "@color5",
        "selected_border": "@color5",
        "input_bg": "rgba(255, 255, 255, 0.4)",
        "input_border": "alpha(@color5, 0.5)",
    },
}


# Fallback palette (hyprtk defaults) when the pywal cache is missing.
FALLBACK = {
    "color0": "#11111b",
    "color1": "#f38ba8",
    "color2": "#a6e3a1",
    "color3": "#f9e2af",
    "color4": "#89b4fa",
    "color5": "#c084fc",
    "color6": "#22d3ee",
    "color7": "#cdd6f4",
    "color8": "#6c7086",
    "color9": "#f38ba8",
    "color10": "#a6e3a1",
    "color11": "#f9e2af",
    "color12": "#89b4fa",
    "color13": "#c084fc",
    "color14": "#22d3ee",
    "color15": "#f5f5f5",
    "background": "#1e1e2e",
    "foreground": "#cdd6f4",
}


def _read_wal_colors():
    """Parse ~/.cache/wal/colors.sh into {name: #hex}. Empty on failure."""
    colors = {}
    pattern = re.compile(r"^(background|foreground|color\d+)='(#[0-9a-fA-F]{6,8})'")
    try:
        with open(WAL_COLORS_SH, encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    colors[match.group(1)] = match.group(2)
    except OSError:
        pass
    return colors


def active_theme_name():
    """Base name of the active waybar theme from ~/.cache/.themestyle.sh."""
    try:
        with open(THEME_FILE, encoding="utf-8") as f:
            name = f.read().split(";")[0].strip().strip("/")
    except OSError:
        return ""
    return name


def active_profile():
    """Profile dict for the active waybar theme (falls back to default)."""
    name = active_theme_name()
    base = name
    for suffix in ("-top", "-bottom"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return PROFILES.get(base) or PROFILES.get("default")


def _palette_to_css(colors):
    lines = ["/* pywal palette */"]
    for name in FALLBACK:
        lines.append("@define-color %s %s;" % (name, colors.get(name, FALLBACK[name])))
    return "\n".join(lines)


def _profile_to_css(profile):
    lines = ["/* waybar theme profile */"]
    for key, value in profile.items():
        lines.append("@define-color %s %s;" % (key, value))
    return "\n".join(lines)


def active_layout():
    """Current layout name, validated against known layouts."""
    name = cfg.load_config().get("layout", "whisker")
    return name if name in cfg.LAYOUTS else "whisker"


def layout_css(name):
    """Contents of the layout CSS file for `name` (empty if missing)."""
    path = os.path.join(BASE_DIR, "assets", "layout-%s.css" % name)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def build_css():
    """Assemble the final CSS: pywal palette, base rules, theme profile, layout."""
    colors = _read_wal_colors()
    if not colors:
        colors = dict(FALLBACK)
    parts = [_palette_to_css(colors)]
    with open(STYLE_CSS, encoding="utf-8") as f:
        parts.append(f.read())
    parts.append(_profile_to_css(active_profile()))
    parts.append(layout_css(active_layout()))
    return "\n".join(parts)


def wal_mtime():
    """Nanosecond mtime of the pywal colors file (0 if missing)."""
    try:
        return os.stat(WAL_COLORS_SH).st_mtime_ns
    except OSError:
        return 0


def themestyle_mtime():
    """Nanosecond mtime of the active-theme file (0 if missing)."""
    try:
        return os.stat(THEME_FILE).st_mtime_ns
    except OSError:
        return 0


_provider = None


def apply_css(css):
    """Load CSS into a single persistent provider and refresh all widgets."""
    global _provider
    screen = Gdk.Screen.get_default()
    if _provider is None:
        _provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            screen, _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    _provider.load_from_data(css.encode("utf-8"))
    Gtk.StyleContext.reset_widgets(screen)
