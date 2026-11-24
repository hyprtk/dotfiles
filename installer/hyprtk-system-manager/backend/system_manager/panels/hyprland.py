"""Hyprland — a link page into the Hyprland settings application."""

from __future__ import annotations

from .. import form, jsonconf, paths, util
from . import base


def _requires() -> list[str]:
    root = paths.hypr_dir()
    if root is None:
        return []
    text = util.read_text(root / "hyprland.lua")
    modules = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("require(") and line.endswith(")"):
            modules.append(line[len("require("):-1].strip().strip('"\''))
    return modules


def probe() -> dict:
    root = paths.hypr_dir()
    names = sorted(p.name for p in root.glob("*.lua")) if root else []
    cfg = jsonconf.load()
    monitor_source = str(paths.monitors_file() or "not found")

    return base.make_page("hyprland", [
        form.section("Compositor", [
            form.info("Configuration", str(root or "not found"), mono=True, copy=True),
            form.info("Lua modules", ", ".join(names) or "none", mono=True),
            form.info("Monitor file", monitor_source, mono=True),
            form.info("Bar animations", (cfg.get("animations") or {}).get("mode") or "high"),
        ]),
        form.section("Hyprland settings", [
            form.note("Gaps, blur, shadows, animations, key bindings, window rules and "
                      "input live in the Hyprland settings app (config-manager). It reads "
                      "the Lua tree directly and validates every write.", "info"),
            form.action("Open Hyprland settings", "hyprland.open", variant="primary"),
            form.action("Open as an overlay", "hyprland.open_overlay"),
            form.action("Open the configuration folder", "hyprland.open_folder"),
        ]),
        form.section("Modules loaded", [
            form.kv([{"label": name, "value": ""} for name in _requires()]) or
            form.note("No require() entries found.", "warn"),
        ]),
        form.section("Displays", [
            form.note("Screen arrangement is handled by the Displays panel, which writes a "
                      "managed block into monitors.lua and leaves the rest untouched.", "info"),
        ]),
    ], status="link")


def action(name: str, args: dict) -> dict:
    if util.which("config-manager") is None:
        return base.fail("config-manager is not installed")
    if name == "hyprland.open":
        util.run(["config-manager", "open"], timeout=10)
        return base.ok("Opened Hyprland settings")
    if name == "hyprland.open_overlay":
        util.run(["config-manager", "open", "--overlay"], timeout=10)
        return base.ok("Opened Hyprland settings as an overlay")
    if name == "hyprland.open_folder":
        root = paths.hypr_dir()
        if root is None:
            return base.fail("No Hyprland configuration found")
        command = "hyprtk-fm" if util.which("hyprtk-fm") else "xdg-open"
        util.run([command, str(root)], timeout=10)
        return base.ok("Opened the configuration folder")
    return base.fail(f"unknown action {name!r}")
