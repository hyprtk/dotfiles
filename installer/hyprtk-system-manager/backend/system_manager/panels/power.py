"""Power — power sources, battery and idle behaviour."""

from __future__ import annotations

from pathlib import Path

from .. import form, util
from . import base


def _supplies() -> list[dict]:
    items: list[dict] = []
    root = Path("/sys/class/power_supply")
    if not root.is_dir():
        return items
    for entry in sorted(root.iterdir()):
        kind = util.read_text(entry / "type").strip()
        if not kind:
            continue
        online = util.read_text(entry / "online").strip()
        capacity = util.read_text(entry / "capacity").strip()
        status = util.read_text(entry / "status").strip()
        items.append({
            "name": entry.name, "type": kind, "online": online,
            "capacity": capacity, "status": status,
        })
    return items


def probe() -> dict:
    supplies = _supplies()
    rows = []
    for item in supplies:
        if item["type"] == "Battery":
            rows.append(form.info(item["name"], f"{item['capacity']}% · {item['status']}", mono=True))
        else:
            rows.append(form.info(item["name"], "connected" if item["online"] == "1" else "disconnected", mono=True))
    if not rows:
        rows.append(form.note("This machine has no battery or AC adapter reported "
                              "through /sys/class/power_supply (desktop).", "info"))

    hypridle = Path.home() / ".config" / "hypr" / "hypridle.conf"
    profiles = util.which("powerprofilesctl") is not None
    tlp = util.which("tlp-stat") is not None

    return base.make_page("power", [
        form.section("Sources", rows),
        form.section("Idle behaviour", [
            form.info("hypridle config", str(hypridle) if hypridle.is_file() else "missing", mono=True),
            form.info("hypridle running", "yes" if util.which("pgrep") and
                      util.run(["pgrep", "-x", "hypridle"], timeout=4).ok else "no"),
            form.info("Power profiles", "powerprofilesctl available" if profiles else "powerprofilesctl not installed"),
            form.info("TLP", "installed" if tlp else "not installed"),
        ]),
        form.section("Suspend, reboot and shutdown", [
            form.note("Those actions live in the bar's power menu and require no settings.", "info"),
            form.action("Open the bar's power menu", "power.open_menu"),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    if name == "power.open_menu":
        if util.which("hyprctl") is None:
            return base.fail("hyprctl is not installed")
        util.run(["hyprctl", "dispatch", 'hl.dsp.exec_cmd("hyprtk-bar-qt-menu-toggle")'], timeout=8)
        return base.ok("Opened the bar menu")
    return base.fail(f"unknown action {name!r}")
