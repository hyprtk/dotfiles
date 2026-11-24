"""Appearance — theme, wallpaper, colours, icons and cursors.

Writes the same keys the bar's own Settings page writes
(`~/.config/hyprtk-bar-qt/config.json`) and the GTK theme files every toolkit
reads. Wallpaper changes go through the suite's awww wrapper, which regenerates
the pywal palette that the whole desktop follows.
"""

from __future__ import annotations

import re
from pathlib import Path

from .. import form, jsonconf, paths, util
from . import base

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".avif")


def _wallpapers() -> list[str]:
    found: list[str] = []
    for root in (Path.home() / "Pictures", Path.home() / "Wallpapers", Path.home() / "wallpapers"):
        if not root.is_dir():
            continue
        try:
            for entry in sorted(root.rglob("*")):
                if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES:
                    found.append(str(entry))
        except OSError:
            continue
        if found:
            break
    return found[:400]


def _theme_dirs(root: Path, marker: str) -> list[str]:
    names: list[str] = []
    if not root.is_dir():
        return names
    try:
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry / marker).exists():
                names.append(entry.name)
    except OSError:
        pass
    return names


def icon_themes() -> list[str]:
    names = _theme_dirs(Path("/usr/share/icons"), "index.theme")
    names += _theme_dirs(Path.home() / ".local" / "share" / "icons", "index.theme")
    names += _theme_dirs(Path.home() / ".icons", "index.theme")
    return sorted(set(names))


def cursor_themes() -> list[str]:
    names = _theme_dirs(Path("/usr/share/icons"), "cursors")
    names += _theme_dirs(Path.home() / ".local" / "share" / "icons", "cursors")
    names += _theme_dirs(Path.home() / ".icons", "cursors")
    return sorted(set(names))


def gtk_themes() -> list[str]:
    names = _theme_dirs(Path("/usr/share/themes"), "gtk-3.0")
    names += _theme_dirs(Path.home() / ".themes", "gtk-3.0")
    return sorted(set(names))


def read_ini(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current = ""
    for line in util.read_text(path).splitlines():
        line = line.rstrip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
        elif "=" in line and current:
            key, _, value = line.partition("=")
            sections[current][key.strip()] = value.strip()
    return sections


def write_ini(path: Path, sections: dict[str, dict[str, str]]) -> None:
    lines: list[str] = []
    for section, values in sections.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key}={value}")
        lines.append("")
    util.atomic_write(path, "\n".join(lines))


def gtk_values() -> dict[str, str]:
    sections = read_ini(paths.GTK3_SETTINGS)
    return sections.get("Settings", {})


def gtk_set(updates: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for target in (paths.GTK3_SETTINGS, paths.GTK4_SETTINGS):
        sections = read_ini(target)
        block = sections.setdefault("Settings", {})
        for key, value in updates.items():
            if block.get(key) != value:
                block[key] = value
                changed.append(f"{target}: {key}={value}")
        write_ini(target, sections)
    return changed


def _cursor_default(name: str) -> None:
    path = Path.home() / ".icons" / "default" / "index.theme"
    util.atomic_write(path, f"[Icon Theme]\nName=Default\nComment=Default cursor theme\nInherits={name}\n")


# The bar's theme lives in two places in one file: the nested `theme` block
# (persisted) and top-level Qt overrides (`themeAccent`, ...) which win. The
# bar's own Settings writes both; a writer that touches only the nested block
# is shadowed by a flat override, and one that touches only the flat keys is
# ignored by anything that reads the block. Write both.
THEME_FLAT = {
    "source": "themeSource",
    "theme_name": "themeName",
    "background": "themeBackground",
    "foreground": "themeForeground",
    "accent": "themeAccent",
}
THEME_COLOURS = ("background", "foreground", "accent")


def current_wallpaper() -> str:
    """The wallpaper actually on screen.

    The bar's Themer asks its own backend (`wallpapers.py current`), which reads
    awww; a `wallpaper` key in the bar config was never read by anything, so
    writing one only made the panel look persisted when it was not.
    """
    for tool in ("awww", "swww"):
        if util.which(tool) is None:
            continue
        result = util.run([tool, "query"], timeout=6)
        for line in result.lines():
            if "image:" in line:
                return line.split("image:", 1)[1].strip()
    return ""


def effective_theme(cfg: dict) -> dict:
    """Theme values as the bar resolves them (flat override first)."""
    theme = dict(cfg.get("theme") or {})
    for key, flat in THEME_FLAT.items():
        value = cfg.get(flat)
        if isinstance(value, str) and value:
            theme[key] = value
    if not theme.get("source"):
        theme["source"] = "pywal" if cfg.get("use_pywal") is not False else "manual"
    return theme


def theme_patch(updates: dict, *, source: str = "") -> dict:
    """A patch carrying both representations of *updates*."""
    patch: dict = {"theme": dict(updates)}
    for key, flat in THEME_FLAT.items():
        if key in updates:
            patch[flat] = updates[key]
    if source == "pywal":
        # Back to the wallpaper: drop the colour overrides, or they keep winning.
        for key in THEME_COLOURS:
            patch[THEME_FLAT[key]] = ""
    return patch


def probe() -> dict:
    cfg = jsonconf.load()
    theme = effective_theme(cfg)
    font = cfg.get("font") or {}
    source = theme.get("source") or ("manual" if cfg.get("use_pywal") is False else "pywal")
    gtk = gtk_values()
    wal = util.read_json(paths.WALLPAPER_CACHE, {})
    wal_colors = (wal.get("special") or {}) if isinstance(wal, dict) else {}

    icon_list = icon_themes()
    current_icon = gtk.get("gtk-icon-theme-name") or (cfg.get("launcher") or {}).get("icon_theme") or "Papirus-Dark"
    current_cursor = gtk.get("gtk-cursor-theme-name") or "Adwaita"
    cursor_size = int(gtk.get("gtk-cursor-theme-size") or 24)
    gtk_theme = gtk.get("gtk-theme-name") or ""
    gtk_font = gtk.get("gtk-font-name") or "Noto Sans 10"
    wallpaper = current_wallpaper()

    theme_rows = [
        form.choice("source", "Colour source", source, [
            {"value": "pywal", "label": "Follow the wallpaper (pywal)"},
            {"value": "manual", "label": "Manual colours"},
        ], help="Writes theme.source in the bar config."),
        form.color("background", "Background", theme.get("background") or wal_colors.get("background") or "#1e1e2e",
                   help="Used when the source is manual."),
        form.color("foreground", "Foreground", theme.get("foreground") or wal_colors.get("foreground") or "#e5e7eb"),
        form.color("accent", "Accent", theme.get("accent") or "#c084fc"),
    ]

    chrome = [
        form.slider("opacity", "Panel opacity", float(cfg.get("opacity") or 0.92),
                    minimum=0.4, maximum=1.0, step=0.01),
        form.number("border_width", "Border width", int(cfg.get("border_width") or 2),
                    minimum=0, maximum=6),
        form.toggle("border_animation", "Animate the border colour",
                    bool(theme.get("border_animation", True))),
        form.toggle("transparent_widgets", "Transparent desktop widgets",
                    bool((cfg.get("widgets") or {}).get("transparent", False))),
    ]

    wallpaper_rows = [
        form.path("wallpaper", "Wallpaper", wallpaper, mode="file", filter="image",
                  help="Awww applies it and regenerates the pywal palette."),
        form.action("Apply wallpaper", "appearance.wallpaper", variant="primary"),
        form.note("Wallpaper changes are session-wide; the bar, terminals and every "
                  "hyprtk app repaint from the new palette.", "info"),
    ]

    identity = [
        form.choice("icon_theme", "Icon theme", current_icon, icon_list or [current_icon]),
        form.choice("cursor_theme", "Cursor theme", current_cursor, cursor_themes() or [current_cursor]),
        form.number("cursor_size", "Cursor size", cursor_size, minimum=12, maximum=64),
        form.choice("gtk_theme", "GTK theme", gtk_theme, gtk_themes() or [gtk_theme]),
        form.info("GTK font", gtk_font, mono=True),
    ]

    return base.make_page("appearance", [
        form.section("Theme", theme_rows),
        form.section("Bar chrome", chrome),
        form.section("Wallpaper", wallpaper_rows),
        form.section("Icons & cursors", identity),
        form.section("Applied to", [
            form.info("Bar settings", str(paths.BAR_CONFIG), mono=True, copy=True),
            form.info("GTK settings", str(paths.GTK3_SETTINGS), mono=True, copy=True),
        ]),
    ])


def apply(changes: dict) -> dict:
    bar: dict = {}
    details: list[str] = []
    gtk: dict[str, str] = {}

    theme_updates: dict = {}
    for key in ("background", "foreground", "accent"):
        if key in changes:
            theme_updates[key] = str(changes[key])
    if "source" in changes:
        theme_updates["source"] = str(changes["source"])
    if "border_animation" in changes:
        theme_updates["border_animation"] = bool(changes["border_animation"])
    if theme_updates:
        bar.update(theme_patch(theme_updates, source=str(changes.get("source") or "")))
    if "opacity" in changes:
        bar["opacity"] = max(0.4, min(1.0, float(changes["opacity"])))
    if "border_width" in changes:
        bar["border_width"] = max(0, min(6, int(changes["border_width"])))
    if "transparent_widgets" in changes:
        bar.setdefault("widgets", {})["transparent"] = bool(changes["transparent_widgets"])
    if "icon_theme" in changes:
        value = str(changes["icon_theme"])
        bar.setdefault("launcher", {})["icon_theme"] = value
        gtk["gtk-icon-theme-name"] = value
    if "cursor_theme" in changes:
        value = str(changes["cursor_theme"])
        gtk["gtk-cursor-theme-name"] = value
        _cursor_default(value)
        details.append("~/.icons/default/index.theme")
    if "cursor_size" in changes:
        gtk["gtk-cursor-theme-size"] = str(max(12, min(64, int(changes["cursor_size"]))))
    if "gtk_theme" in changes:
        gtk["gtk-theme-name"] = str(changes["gtk_theme"])

    if bar:
        jsonconf.patch(bar)
        details.append("~/.config/hyprtk-bar-qt/config.json")
    if gtk:
        details.extend(gtk_set(gtk))

    if not details:
        return base.ok("Nothing to change")
    return base.ok("Appearance updated", details=details,
                   note="Icon and cursor changes reach already-running apps after they restart.")


def action(name: str, args: dict) -> dict:
    if name == "appearance.wallpaper":
        path = Path(str(args.get("path") or "")).expanduser()
        if not path.is_file():
            return base.fail(f"Not a file: {path}")
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            return base.fail("Unsupported image type")
        command = ["awww", "img", str(path)]
        if util.which("awww") is None:
            command = ["swww", "img", str(path)]
        if util.which(command[0]) is None:
            return base.fail("Neither awww nor swww is installed")
        result = util.run(command, timeout=45)
        if not result.ok:
            return base.fail(f"Could not apply the wallpaper: {result.text.strip()}")
        return base.ok("Wallpaper applied", details=[f"{command[0]} img {path}",
                                                     "pywal palette regenerated"])

    if name == "appearance.refresh_palette":
        script = Path.home() / ".config" / "hypr" / "scripts" / "wallpaper-colors.sh"
        if not script.is_file():
            return base.fail("wallpaper-colors.sh not found")
        result = util.run(["bash", str(script)], timeout=60)
        return base.ok("Palette refreshed") if result.ok else base.fail(result.text.strip())

    return base.fail(f"unknown action {name!r}")
