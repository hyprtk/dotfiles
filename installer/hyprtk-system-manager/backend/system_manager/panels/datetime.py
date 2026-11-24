"""Date & Time — timezone, NTP and the hardware clock."""

from __future__ import annotations

from .. import form, priv, util
from . import base


def parse_timedatectl(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def _zones() -> list[str]:
    result = util.run(["timedatectl", "list-timezones"], timeout=15)
    zones = sorted({line.strip() for line in result.lines()})
    return zones


def probe() -> dict:
    if util.which("timedatectl") is None:
        return base.make_page("datetime", [
            form.section("Unavailable", [base.missing_note("timedatectl", "systemd-timedated")]),
        ])

    state = parse_timedatectl(util.run(["timedatectl", "show"], timeout=10).out)
    zones = _zones()
    current_zone = state.get("Timezone", "UTC")
    if zones and current_zone not in zones:
        zones.insert(0, current_zone)
    ntp = state.get("NTP", "no") == "yes"
    synced = state.get("NTPSynchronized", "no") == "yes"
    local_rtc = state.get("LocalRTC", "no") == "yes"

    clock = [
        form.info("Local time", state.get("TimeUSec", "unknown").split(".", 1)[0], mono=True),
        form.info("Hardware clock", state.get("RTCTimeUSec", "unknown").split(".", 1)[0], mono=True),
        form.info("Synchronised", "yes" if synced else "no",
                  tone="ok" if synced else "warn"),
        form.info("Time service", "systemd-timesyncd" if ntp else "manual"),
    ]

    settings = [
        form.choice("timezone", "Time zone", current_zone, zones,
                    help="Written with timedatectl; needs administrator authentication."),
        form.toggle("ntp", "Set time automatically", ntp,
                    help="Enables NTP through systemd-timesyncd."),
        form.toggle("local_rtc", "Hardware clock uses local time", local_rtc,
                    help="Leave off unless dual-booting with Windows."),
    ]

    return base.make_page("datetime", [
        form.section("Clock", clock),
        form.section("Settings", settings),
        form.section("Maintenance", [
            form.action("Synchronise now", "datetime.sync", variant="default"),
            form.action("Show time service status", "datetime.status"),
            form.note("All writes run through pkexec and are logged by systemd.", "info"),
        ]),
    ])


def apply(changes: dict) -> dict:
    details: list[str] = []
    try:
        if "timezone" in changes:
            zone = str(changes["timezone"]).strip()
            if not zone:
                return base.fail("Time zone cannot be empty")
            result = priv.run_priv(["timedatectl", "set-timezone", zone])
            if not result.ok:
                return base.denied(f"Could not set time zone: {result.text.strip()}",
                                   priv.command_for(["timedatectl", "set-timezone", zone]))
            details.append(f"timedatectl set-timezone {zone}")

        if "ntp" in changes:
            value = "true" if changes["ntp"] else "false"
            result = priv.run_priv(["timedatectl", "set-ntp", value])
            if not result.ok:
                return base.denied(f"Could not change NTP: {result.text.strip()}",
                                   priv.command_for(["timedatectl", "set-ntp", value]))
            details.append(f"timedatectl set-ntp {value}")

        if "local_rtc" in changes:
            value = "1" if changes["local_rtc"] else "0"
            result = priv.run_priv(["timedatectl", "set-local-rtc", value])
            if not result.ok:
                return base.denied(f"Could not change the hardware clock: {result.text.strip()}",
                                   priv.command_for(["timedatectl", "set-local-rtc", value]))
            details.append(f"timedatectl set-local-rtc {value}")
    except Exception as exc:  # noqa: BLE001 - report, never crash the RPC
        return base.fail(f"{type(exc).__name__}: {exc}")

    if not details:
        return base.ok("Nothing to change")
    return base.ok("Date & time updated", details=details)


def action(name: str, args: dict) -> dict:
    if name == "datetime.sync":
        result = priv.run_priv(["timedatectl", "set-ntp", "true"])
        if not result.ok:
            return base.fail(f"Could not enable synchronisation: {result.text.strip()}")
        return base.ok("Network time synchronisation enabled", details=["timedatectl set-ntp true"])
    if name == "datetime.status":
        result = util.run(["timedatectl", "timesync-status"], timeout=10)
        text = result.text.strip()
        if not text:
            text = util.run(["timedatectl", "status"], timeout=10).text.strip()
        return base.ok("Time service status", details=text.splitlines())
    return base.fail(f"unknown action {name!r}")
