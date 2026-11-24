"""Fonts — interface and monospace families, size and installation."""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import form, jsonconf, paths, util
from . import appearance
from . import base

FONT_SUFFIXES = (".ttf", ".otf", ".ttc", ".woff", ".woff2")


def families() -> list[str]:
    result = util.run(["fc-list", ":", "family"], timeout=20)
    names: set[str] = set()
    for line in result.lines():
        for part in line.split(","):
            name = part.strip()
            if name and not name.startswith("."):
                names.add(name)
    return sorted(names)


def default_family(pattern: str = "sans-serif") -> str:
    result = util.run(["fc-match", "-f", "%{family}", pattern], timeout=8)
    return (result.out or "").split(",")[0].strip()


def probe() -> dict:
    if util.which("fc-list") is None:
        return base.make_page("fonts", [
            form.section("Unavailable", [base.missing_note("fc-list", "fontconfig")]),
        ])

    cfg = jsonconf.load()
    font = cfg.get("font") or {}
    gtk = appearance.gtk_values()
    gtk_font = gtk.get("gtk-font-name") or "Noto Sans 10"
    family = font.get("family") or gtk_font.rsplit(" ", 1)[0]
    size = int(font.get("size") or (gtk_font.rsplit(" ", 1)[-1] if gtk_font.rsplit(" ", 1)[-1].isdigit() else 12))
    mono = default_family("monospace")
    all_families = families()

    return base.make_page("fonts", [
        form.section("Interface", [
            form.choice("family", "Font family", family, all_families or [family]),
            form.number("size", "Font size", size, minimum=6, maximum=32, unit="pt"),
            form.info("Resolved sans-serif", default_family("sans-serif")),
            form.info("Resolved monospace", mono),
        ]),
        form.section("Install a font", [
            form.note("Install a .ttf, .otf, .ttc or .woff file; it is copied to "
                      "~/.local/share/fonts and the cache is refreshed. Every toolkit "
                      "picks it up without a restart.", "info"),
            form.action("Install a font…", "fonts.install", variant="primary", needs="file"),
            form.action("Refresh the font cache", "fonts.refresh"),
        ]),
        form.section("Applied to", [
            form.info("Bar font", f"{family} {size}pt"),
            form.info("GTK font", gtk_font, mono=True),
            form.info("Cache", "fc-cache -f", mono=True),
        ]),
        form.section("Families detected", [
            form.kv([{"label": name, "value": ""} for name in all_families[:60]]),
            form.info("Total", len(all_families)),
        ]),
    ])


def apply(changes: dict) -> dict:
    details: list[str] = []
    bar: dict = {}
    gtk: dict[str, str] = {}

    family = changes.get("family")
    size = changes.get("size")
    if family:
        bar.setdefault("font", {})["family"] = str(family)
    if size:
        bar.setdefault("font", {})["size"] = int(size)
    if family or size:
        cfg = jsonconf.load()
        current_family = str(family or (cfg.get("font") or {}).get("family") or "Noto Sans")
        current_size = int(size or (cfg.get("font") or {}).get("size") or 12)
        if family:
            gtk["gtk-font-name"] = f"{current_family} {current_size}"
        if size:
            gtk["gtk-font-name"] = f"{current_family} {current_size}"

    if bar:
        jsonconf.patch(bar)
        details.append("~/.config/hyprtk-bar-qt/config.json")
    if gtk:
        details.extend(appearance.gtk_set(gtk))

    if not details:
        return base.ok("Nothing to change")
    return base.ok("Fonts updated", details=details,
                   note="Running applications pick up the new font when they next start.")


def action(name: str, args: dict) -> dict:
    if name == "fonts.refresh":
        result = util.run(["fc-cache", "-f"], timeout=60)
        if not result.ok:
            return base.fail(result.text.strip() or "fc-cache failed")
        return base.ok("Font cache refreshed")

    if name == "fonts.install":
        source = Path(str(args.get("path") or "")).expanduser()
        if not source.is_file() or source.suffix.lower() not in FONT_SUFFIXES:
            return base.fail("Choose a .ttf, .otf, .ttc or .woff file")
        target = paths.FONTS_DIR / source.name
        try:
            paths.FONTS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as exc:
            return base.fail(f"Could not copy: {exc}")
        util.run(["fc-cache", "-f"], timeout=60)
        return base.ok(f"Installed {source.name}", details=[str(target)])

    return base.fail(f"unknown action {name!r}")
