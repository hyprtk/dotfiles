"""Bluetooth — BlueZ adapter state and paired devices."""

from __future__ import annotations

from .. import form, util
from . import base


def parse_show(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def parse_devices(text: str) -> list[dict]:
    devices: list[dict] = []
    for line in text.splitlines():
        bits = line.split(maxsplit=2)
        if len(bits) >= 2 and bits[0] == "Device":
            devices.append({"mac": bits[1], "name": bits[2] if len(bits) > 2 else bits[1]})
    return devices


def probe() -> dict:
    if util.which("bluetoothctl") is None:
        return base.make_page("bluetooth", [
            form.section("Unavailable", [base.missing_note("bluetoothctl", "BlueZ")]),
        ])

    state = parse_show(util.run(["bluetoothctl", "show"], timeout=10).out)
    powered = state.get("Powered") == "yes"
    paired = parse_devices(util.run(["bluetoothctl", "devices", "Paired"], timeout=10).out)
    all_devices = parse_devices(util.run(["bluetoothctl", "devices"], timeout=10).out)

    items = [
        {"title": device["name"], "subtitle": device["mac"],
         "badges": ["paired"] if any(p["mac"] == device["mac"] for p in paired) else [],
         "actions": [
             {"label": "Forget", "action": "bluetooth.forget",
              "args": {"mac": device["mac"]}, "variant": "danger", "danger": True,
              "confirm": device["name"]},
         ]}
        for device in all_devices
    ]

    return base.make_page("bluetooth", [
        form.section("Adapter", [
            form.info("Controller", state.get("Controller", "none"), mono=True),
            form.info("Name", state.get("Alias") or state.get("Name") or "unknown"),
            form.info("Powered", "yes" if powered else "no", tone="ok" if powered else "warn"),
            form.info("Discoverable", state.get("Discoverable", "no")),
            form.toggle("powered", "Enable Bluetooth", powered),
        ]),
        form.section("Devices", [
            form.list_row(items) if items else form.note("No devices seen by the adapter.", "info"),
        ]),
        form.section("Actions", [
            form.action("Scan for devices", "bluetooth.scan"),
            form.note("Pairing is done with bluetoothctl for now: pairing needs a PIN "
                      "conversation that this scaffold does not model yet.", "warn"),
        ]),
    ], status="partial")


def apply(changes: dict) -> dict:
    if "powered" in changes:
        value = "on" if changes["powered"] else "off"
        result = util.run(["bluetoothctl", "power", value], timeout=10)
        if not result.ok:
            return base.fail(result.text.strip() or "bluetoothctl failed")
        return base.ok(f"Bluetooth {value}", details=[f"bluetoothctl power {value}"])
    return base.ok("Nothing to change")


def action(name: str, args: dict) -> dict:
    if name == "bluetooth.scan":
        result = util.run(["bluetoothctl", "--timeout", "8", "scan", "on"], timeout=14)
        devices = parse_devices(util.run(["bluetoothctl", "devices"], timeout=10).out)
        return base.ok(f"{len(devices)} device(s) known", details=[d["name"] for d in devices[:20]])
    if name == "bluetooth.forget":
        mac = str(args.get("mac") or "")
        if not mac:
            return base.fail("No device address")
        result = util.run(["bluetoothctl", "remove", mac], timeout=10)
        if not result.ok:
            return base.fail(result.text.strip() or "bluetoothctl failed")
        return base.ok("Device removed", details=[f"bluetoothctl remove {mac}"])
    return base.fail(f"unknown action {name!r}")
