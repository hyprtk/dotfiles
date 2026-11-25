"""hyprtk Suite — every suite application plus the bar's core settings."""

from __future__ import annotations

from pathlib import Path

from .. import apps, form, jsonconf, util
from . import base


# Apply is a pure file edit, so a dry run can show it as a diff.
PREVIEW = "files"

def _bar_rows() -> list[dict]:
    cfg = jsonconf.load()
    theme = cfg.get("theme") or {}
    font = cfg.get("font") or {}
    anim = cfg.get("animations") or {}
    return [
        form.slider("bar_opacity", "Bar opacity", float(cfg.get("opacity") or 0.92),
                    minimum=0.4, maximum=1.0, step=0.01),
        form.number("bar_border_width", "Bar border width", int(cfg.get("border_width") or 2),
                    minimum=0, maximum=6),
        form.number("bar_font_size", "Bar font size", int(font.get("size") or 12),
                    minimum=8, maximum=24),
        form.choice("bar_animations", "Border animation speed",
                    anim.get("mode") or "high",
                    [{"value": "low", "label": "Low"}, {"value": "high", "label": "High"},
                     {"value": "custom", "label": "Custom"}]),
        form.info("Colour source", theme.get("source") or "pywal"),
    ]


def probe() -> dict:
    found = apps.all_apps()
    items = []
    for app in found:
        if not app["installed"]:
            continue
        actions = []
        if app["settings"]:
            actions.append({
                "label": "Open settings", "action": "suite.settings",
                "args": {"id": app["id"]},
            })
        if app["binary"]:
            actions.append({
                "label": "Launch", "action": "suite.launch",
                "args": {"id": app["id"]},
            })
        badges = ["running"] if app["running"] else []
        subtitle = f"{app['name']} {app['version'] or '—'} · {app['binary']}"
        if app.get("settings_hint"):
            subtitle += f" · {app['settings_hint']}"
        items.append({
            "title": app["title"],
            "subtitle": subtitle,
            "badges": badges, "actions": actions,
        })

    missing = [app["title"] for app in found if not app["installed"]]

    return base.make_page("suite", [
        form.section("Applications", [
            form.list_row(items, label="") if items else form.note("No suite apps installed.", "warn"),
            form.note("Version numbers are read from the installed payload, not from "
                      "--version (the Quickshell apps forward that flag to qs).", "info"),
        ]),
        form.section("Bar settings", _bar_rows(),
                     "A focused subset; the bar's own Settings window covers all ten pages."),
        form.section("Links", [
            form.action("Open the bar's settings", "suite.open_bar_settings", variant="primary"),
            form.action("Open Hyprland settings", "suite.open_hyprland"),
            form.action("Open the suite folder", "suite.open_folder"),
        ]),
        form.section("Not installed", [
            form.kv([{"label": name, "value": ""} for name in missing]) if missing else
            form.note("Every suite application is installed.", "ok"),
        ]),
    ])


def apply(changes: dict) -> dict:
    updates: dict = {}
    if "bar_opacity" in changes:
        updates["opacity"] = max(0.4, min(1.0, float(changes["bar_opacity"])))
    if "bar_border_width" in changes:
        updates["border_width"] = max(0, min(6, int(changes["bar_border_width"])))
    if "bar_font_size" in changes:
        updates.setdefault("font", {})["size"] = max(8, min(24, int(changes["bar_font_size"])))
    if "bar_animations" in changes:
        updates.setdefault("animations", {})["mode"] = str(changes["bar_animations"])
    if not updates:
        return base.ok("Nothing to change")
    jsonconf.patch(updates)
    return base.ok("Bar settings updated",
                   details=["~/.config/hyprtk-bar-qt/config.json"])


def action(name: str, args: dict) -> dict:
    if name == "suite.open_bar_settings":
        if util.which("hyprtk-bar-qt-settings-toggle") is None:
            return base.fail("The bar settings toggle is not installed")
        if not util.spawn(["hyprtk-bar-qt-settings-toggle"]):
            return base.fail("Could not open the bar settings")
        return base.ok("Opened the bar's settings")
    if name == "suite.open_hyprland":
        if util.which("config-manager") is None:
            return base.fail("config-manager is not installed")
        if not util.spawn(["config-manager", "open"]):
            return base.fail("Could not open Hyprland settings")
        return base.ok("Opened Hyprland settings")
    if name == "suite.open_folder":
        command = ["hyprtk-fm", str(Path.home() / ".local" / "share")]
        if util.which("hyprtk-fm") is None:
            command = ["xdg-open", str(Path.home() / ".local" / "share")]
        if not util.spawn(command):
            return base.fail("Could not open the suite folder")
        return base.ok("Opened the suite folder")
    app = next((item for item in apps.APPS if item["id"] == args.get("id")), None)
    if app is None:
        return base.fail("Unknown application")
    if name == "suite.settings":
        argv = apps.settings_argv(app)
        if not argv:
            return base.fail(f"{app['title']} has no settings entry point")
        util.run(argv, timeout=10)
        return base.ok(f"Opened {app['title']} settings")
    if name == "suite.launch":
        if util.which(app["binary"]) is None:
            return base.fail(f"{app['binary']} is not on PATH")
        util.run([app["binary"]], timeout=10)
        return base.ok(f"Launched {app['title']}")
    return base.fail(f"unknown action {name!r}")
