"""Services — systemd units that are running or enabled."""

from __future__ import annotations

from .. import form, priv, util
from . import base

PROTECTED = {"systemd-journald.service", "systemd-logind.service", "dbus.service",
             "systemd-udevd.service", "polkit.service"}


def _units() -> tuple[list[str], list[str]]:
    running = util.run(
        ["systemctl", "list-units", "--type=service", "--state=running",
         "--no-legend", "--no-pager", "--plain"], timeout=20,
    )
    enabled = util.run(
        ["systemctl", "list-unit-files", "--type=service", "--state=enabled",
         "--no-legend", "--no-pager"], timeout=20,
    )
    run = [line.split()[0] for line in running.lines() if line.split()]
    en = [line.split()[0] for line in enabled.lines() if line.split()]
    return sorted(set(run)), sorted(set(en))


def probe() -> dict:
    if util.which("systemctl") is None:
        return base.make_page("services", [
            form.section("Unavailable", [base.missing_note("systemctl", "systemd")]),
        ])

    running, enabled = _units()
    items = []
    for unit in sorted(set(running) | set(enabled)):
        actions = []
        if unit not in PROTECTED:
            actions.append({
                "label": "Restart" if unit in running else "Start",
                "action": "services.restart" if unit in running else "services.start",
                "args": {"unit": unit},
            })
            if unit in running:
                actions.append({"label": "Stop", "action": "services.stop",
                                "args": {"unit": unit}, "variant": "danger"})
            actions.append({
                "label": "Disable at boot" if unit in enabled else "Enable at boot",
                "action": "services.disable" if unit in enabled else "services.enable",
                "args": {"unit": unit},
            })
        badges = []
        if unit in running:
            badges.append("running")
        if unit in enabled:
            badges.append("enabled")
        if unit in PROTECTED:
            badges.append("protected")
        items.append({"title": unit, "subtitle": "", "badges": badges, "actions": actions})

    return base.make_page("services", [
        form.section("Units", [
            form.list_row(items, label=""),
        ]),
        form.section("Note", [
            form.note("Core systemd units are protected here. Everything else can be "
                      "started, stopped and toggled through polkit.", "info"),
            form.info("Running services", len(running)),
            form.info("Enabled at boot", len(enabled)),
        ]),
    ])


def _run(argv: list[str]) -> dict:
    result = priv.run_priv(argv)
    if not result.ok:
        return base.denied(result.text.strip() or "systemctl failed", priv.command_for(argv))
    return base.ok("Done", details=[priv.command_for(argv)])


def action(name: str, args: dict) -> dict:
    unit = str(args.get("unit") or "")
    if not unit or unit in PROTECTED:
        return base.fail("That unit cannot be changed here")
    mapping = {
        "services.start": ["systemctl", "start", unit],
        "services.stop": ["systemctl", "stop", unit],
        "services.restart": ["systemctl", "restart", unit],
        "services.enable": ["systemctl", "enable", unit],
        "services.disable": ["systemctl", "disable", unit],
    }
    argv = mapping.get(name)
    if argv is None:
        return base.fail(f"unknown action {name!r}")
    return _run(argv)
