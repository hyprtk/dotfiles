"""Network — NetworkManager devices, Wi-Fi networks and radio state."""

from __future__ import annotations

from .. import form, util
from . import base


def parse_devices(text: str) -> list[dict]:
    devices: list[dict] = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue
        devices.append({
            "device": parts[0], "type": parts[1],
            "state": parts[2], "connection": parts[3] or "—",
        })
    return devices


def parse_wifi(text: str) -> list[dict]:
    networks: list[dict] = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = parts[0], parts[1], parts[2], parts[3]
        if not ssid:
            continue
        try:
            strength = int(signal)
        except ValueError:
            strength = 0
        networks.append({
            "ssid": ssid, "signal": strength,
            "security": security or "open",
            "active": in_use.strip() == "*",
        })
    networks.sort(key=lambda item: (-int(item["active"]), -item["signal"]))
    return networks


def probe() -> dict:
    if util.which("nmcli") is None:
        return base.make_page("network", [
            form.section("Unavailable", [base.missing_note("nmcli", "NetworkManager")]),
        ])

    devices = parse_devices(util.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], timeout=10).out)
    wifi = parse_wifi(util.run(
        ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"], timeout=25).out)
    radio = util.run(["nmcli", "-t", "-f", "WIFI,WWAN", "radio"], timeout=8).out.strip()

    device_items = [
        {"title": f"{item['device']} · {item['type']}", "subtitle": f"{item['state']} — {item['connection']}",
         "badges": ["connected"] if "connected" in item["state"] else [], "actions": []}
        for item in devices if item["type"] != "loopback"
    ]
    wifi_items = [
        {"title": item["ssid"],
         "subtitle": f"{item['signal']}% · {item['security']}",
         "badges": ["connected"] if item["active"] else [], "actions": []}
        for item in wifi[:40]
    ]

    return base.make_page("network", [
        form.section("Devices", [
            form.list_row(device_items) if device_items else form.note("No network devices.", "warn"),
        ]),
        form.section("Wi-Fi", [
            form.info("Radio", radio or "unknown", mono=True),
            form.list_row(wifi_items) if wifi_items else
            form.note("No Wi-Fi networks visible (radio may be off).", "info"),
        ]),
        form.section("Actions", [
            form.action("Turn Wi-Fi on", "network.wifi_on"),
            form.action("Turn Wi-Fi off", "network.wifi_off", variant="danger"),
            form.action("Rescan", "network.rescan"),
            form.note("Joining a network needs a password conversation; connect with nmcli "
                      "or the bar's network module for now.", "info"),
        ]),
    ], status="partial")


def action(name: str, args: dict) -> dict:
    if util.which("nmcli") is None:
        return base.fail("nmcli is not installed")
    if name == "network.wifi_on":
        result = util.run(["nmcli", "radio", "wifi", "on"], timeout=15)
    elif name == "network.wifi_off":
        result = util.run(["nmcli", "radio", "wifi", "off"], timeout=15)
    elif name == "network.rescan":
        result = util.run(["nmcli", "device", "wifi", "rescan"], timeout=25)
    else:
        return base.fail(f"unknown action {name!r}")
    if not result.ok:
        return base.fail(result.text.strip() or "nmcli failed")
    return base.ok("Done", details=[f"nmcli {name.split('.', 1)[1]}"])
