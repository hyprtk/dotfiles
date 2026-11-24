"""Notifications — the bar's notification store and timeouts."""

from __future__ import annotations

from .. import form, jsonconf, util
from . import base


def probe() -> dict:
    cfg = jsonconf.load()
    block = cfg.get("notifications") or {}
    enabled = bool(block.get("enabled", True))

    return base.make_page("notifications", [
        form.section("Notifications", [
            form.toggle("enabled", "Show notifications", enabled),
            form.number("max_stored", "History size", int(block.get("max_stored") or 50),
                        minimum=0, maximum=500),
            form.number("default_timeout", "Banner timeout", int(block.get("default_timeout") or 5000),
                        minimum=1000, maximum=60000, step=500, unit="ms"),
        ], "Written to ~/.config/hyprtk-bar-qt/config.json."),
        form.section("Do not disturb", [
            form.note("Do-not-disturb is a live toggle in the bar; it is not persisted by "
                      "the bar today, so it is not written here.", "info"),
            form.action("Open notification centre", "notifications.open_center"),
        ]),
        form.section("Delivery", [
            form.info("Server", "the bar's notification daemon"),
            form.info("Stored history", int(block.get("max_stored") or 50)),
            form.info("Default timeout", f"{int(block.get('default_timeout') or 5000) / 1000:.1f} s"),
        ]),
    ], status="partial")


def apply(changes: dict) -> dict:
    updates: dict = {}
    if "enabled" in changes:
        updates["enabled"] = bool(changes["enabled"])
    if "max_stored" in changes:
        updates["max_stored"] = max(0, min(500, int(changes["max_stored"])))
    if "default_timeout" in changes:
        updates["default_timeout"] = max(1000, min(60000, int(changes["default_timeout"])))
    if not updates:
        return base.ok("Nothing to change")
    jsonconf.patch({"notifications": updates})
    return base.ok("Notification settings updated",
                   details=["~/.config/hyprtk-bar-qt/config.json"])


def action(name: str, args: dict) -> dict:
    if name == "notifications.open_center":
        if util.which("hyprctl") is None:
            return base.fail("hyprctl is not installed")
        util.run(["hyprctl", "dispatch",
                  'hl.dsp.exec_cmd("qs -p ~/.config/quickshell/hyprtk-bar-qt ipc call notifications toggle")'],
                 timeout=8)
        return base.ok("Toggled the notification centre")
    return base.fail(f"unknown action {name!r}")
