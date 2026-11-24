"""Network — NetworkManager devices, Wi-Fi networks and saved connections.

Connecting to a secured network never puts the password in argv. A temporary
``0600`` passwd-file is handed to ``nmcli connection up ... passwd-file`` and
unlinked immediately afterwards; the password is not logged or returned.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .. import form, util
from . import base


def _split_terse(line: str) -> list[str]:
    """Split an ``nmcli -t`` line on unescaped colons."""
    out: list[str] = []
    current = ""
    escaped = False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            out.append(current)
            current = ""
        else:
            current += char
    out.append(current)
    return out


def parse_devices(text: str) -> list[dict]:
    devices: list[dict] = []
    for line in text.splitlines():
        parts = _split_terse(line)
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
        parts = _split_terse(line)
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
            "security": security.strip(),
            "active": in_use.strip() == "*",
        })
    networks.sort(key=lambda item: (-int(item["active"]), -item["signal"]))
    return networks


def parse_connections(text: str,
                      kinds: tuple[str, ...] = ("wifi", "802-11-wireless", "wireless")) -> list[dict]:
    connections: list[dict] = []
    for line in text.splitlines():
        parts = _split_terse(line)
        if len(parts) < 2:
            continue
        name, kind = parts[0], parts[1]
        device = parts[2] if len(parts) > 2 else ""
        if kind not in kinds:
            continue
        connections.append({
            "name": name, "type": kind, "device": device, "active": bool(device),
        })
    return connections


def _devices() -> list[dict]:
    return parse_devices(util.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], timeout=10).out)


def _wifi() -> list[dict]:
    return parse_wifi(util.run(
        ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
        timeout=25).out)


def _saved() -> list[dict]:
    return parse_connections(util.run(
        ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show"], timeout=10).out)


VPN_PLUGIN_DIRS = ("/usr/lib/NetworkManager/VPN", "/usr/lib64/NetworkManager/VPN",
                   "/usr/lib/networkmanager/VPN")
PLUGIN_ROOT = Path("/usr/lib/NetworkManager")


def vpn_plugin(kind: str) -> str:
    """Path of the NetworkManager plugin for *kind*, or "" when absent.

    WireGuard is built into NetworkManager; OpenVPN needs a separate package
    (networkmanager-openvpn). Without it ``nmcli connection import`` fails with
    "unknown VPN plugin", so the panel checks first instead of offering a button
    that cannot work.
    """
    if kind == "wireguard":
        return "built-in"
    for directory in VPN_PLUGIN_DIRS:
        root = Path(directory)
        if not root.is_dir():
            continue
        for path in sorted(root.glob(f"*{kind}*")):
            return str(path)
    for path in sorted(PLUGIN_ROOT.glob(f"*{kind}*")):
        return str(path)
    return ""


def _saved_vpn() -> list[dict]:
    return parse_connections(util.run(
        ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show"], timeout=10).out,
        kinds=("vpn", "wireguard"))


def _is_secured(network: dict) -> bool:
    return bool(network.get("security")) and network["security"].lower() != "open"


def probe() -> dict:
    if util.which("nmcli") is None:
        return base.make_page("network", [
            form.section("Unavailable", [base.missing_note("nmcli", "NetworkManager")]),
        ])

    devices = _devices()
    wifi = _wifi()
    saved = _saved()
    radio = util.run(["nmcli", "-t", "-f", "WIFI,WWAN", "radio"], timeout=8).out.strip()
    wifi_device = next((item["device"] for item in devices if item["type"] == "wifi"), "")

    device_items = [
        {"title": f"{item['device']} · {item['type']}",
         "subtitle": f"{item['state']} — {item['connection']}",
         "badges": ["connected"] if "connected" in item["state"] else [], "actions": []}
        for item in devices if item["type"] != "loopback"
    ]

    wifi_items = []
    for network in wifi[:40]:
        actions = []
        if not network["active"]:
            action = {
                "label": "Connect", "action": "network.connect",
                "args": {
                    "ssid": network["ssid"],
                    "security": network["security"],
                    "device": wifi_device,
                },
            }
            if _is_secured(network):
                action["needs"] = "wifi"
            actions.append(action)
        wifi_items.append({
            "title": network["ssid"],
            "subtitle": f"{network['signal']}% · {network['security'] or 'open'}",
            "badges": ["connected"] if network["active"] else [],
            "actions": actions,
        })

    vpn = _saved_vpn()
    vpn_items = []
    for connection in vpn:
        actions = []
        if connection["active"]:
            actions.append({
                "label": "Disconnect", "action": "network.vpn_disconnect",
                "args": {"name": connection["name"]},
            })
        else:
            actions.append({
                "label": "Connect", "action": "network.vpn_connect",
                "args": {"name": connection["name"]},
            })
        actions.append({
            "label": "Forget", "action": "network.vpn_forget",
            "args": {"name": connection["name"]},
            "variant": "danger", "danger": True, "confirm": connection["name"],
        })
        vpn_items.append({
            "title": connection["name"],
            "subtitle": connection["type"],
            "badges": ["connected"] if connection["active"] else [],
            "actions": actions,
        })

    vpn_rows: list[dict] = [
        form.list_row(vpn_items) if vpn_items else
        form.note("No VPN connections.", "info"),
    ]
    if vpn_plugin("openvpn"):
        vpn_rows.append(form.action("Import VPN…", "network.vpn_import", needs="file"))
        vpn_rows.append(form.note("OpenVPN (.ovpn) and WireGuard (.conf) profiles are "
                                  "imported by NetworkManager.", "info"))
    else:
        vpn_rows.append(form.note(
            "OpenVPN support is not installed (networkmanager-openvpn), so only a "
            "WireGuard .conf can be imported here.", "warn"))

    saved_items = []
    for connection in saved:
        actions = []
        if connection["active"]:
            actions.append({
                "label": "Disconnect", "action": "network.disconnect",
                "args": {"name": connection["name"]},
            })
        actions.append({
            "label": "Forget", "action": "network.forget",
            "args": {"name": connection["name"]},
            "variant": "danger", "danger": True, "confirm": connection["name"],
        })
        saved_items.append({
            "title": connection["name"],
            "subtitle": connection["device"] or "saved",
            "badges": ["connected"] if connection["active"] else [],
            "actions": actions,
        })

    return base.make_page("network", [
        form.section("Devices", [
            form.list_row(device_items) if device_items else form.note("No network devices.", "warn"),
        ]),
        form.section("Wi-Fi", [
            form.info("Radio", radio or "unknown", mono=True),
            form.action("Turn Wi-Fi on", "network.wifi_on"),
            form.action("Turn Wi-Fi off", "network.wifi_off", variant="danger"),
            form.action("Rescan", "network.rescan"),
            form.note("A secured network asks for its password. It is handed to "
                      "NetworkManager through a private 0600 passwd-file and never "
                      "stored by this application.", "info"),
        ]),
        # Saved and VPN connections come before the (long) scan list: they are the
        # sections a user acts on, and the scan list can run for many screens.
        form.section("Saved networks", [
            form.list_row(saved_items) if saved_items else
            form.note("No saved Wi-Fi connections.", "info"),
        ]),
        form.section("VPN", vpn_rows),
        form.section("Available networks", [
            form.list_row(wifi_items) if wifi_items else
            form.note("No Wi-Fi networks visible (the radio may be off).", "info"),
        ]),
    ], status="partial")


@contextmanager
def _passwd_file(password: str):
    directory = os.environ.get("XDG_RUNTIME_DIR") or None
    fd, path = tempfile.mkstemp(prefix="hyprtk-wifi-", suffix=".secret", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"802-11-wireless-security.psk:{password}\n")
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _connect(params: dict) -> dict:
    ssid = str(params.get("ssid") or "").strip()
    if not ssid or any(ord(char) < 32 for char in ssid):
        return base.fail("Invalid network name")
    security = str(params.get("security") or "").strip()
    password = str(params.get("password") or "")
    device = str(params.get("device") or "").strip()
    secured = bool(security) and security.lower() != "open"
    if secured and not password:
        return base.fail("This network needs a password")

    existing = next((item for item in _saved() if item["name"] == ssid), None)
    created = False
    if existing is None:
        argv = ["nmcli", "connection", "add", "type", "wifi", "con-name", ssid]
        if device:
            argv += ["ifname", device]
        argv += ["ssid", ssid]
        if secured:
            argv += ["wifi-sec.key-mgmt", "wpa-psk"]
        result = util.run(argv, timeout=30)
        if not result.ok:
            return base.fail(result.text.strip() or "Could not create the connection")
        created = True

    up = ["nmcli", "--wait", "30", "connection", "up", "id", ssid]
    if secured:
        with _passwd_file(password) as secrets:
            result = util.run(up + ["passwd-file", secrets], timeout=90)
    else:
        result = util.run(up, timeout=90)

    if not result.ok:
        if created:
            util.run(["nmcli", "connection", "delete", "id", ssid], timeout=20)
        return base.fail(result.text.strip() or f"Could not connect to {ssid}")
    return base.ok(f"Connected to {ssid}",
                   details=[f"nmcli connection up id {ssid}"],
                   note="The password was passed to NetworkManager, not stored here.")


def action(name: str, args: dict) -> dict:
    if util.which("nmcli") is None:
        return base.fail("nmcli is not installed")
    if name == "network.connect":
        return _connect(args)
    if name == "network.vpn_import":
        path = Path(str(args.get("path") or "")).expanduser()
        if not path.is_file():
            return base.fail("Choose a VPN profile file")
        kind = "wireguard" if path.suffix.lower() in (".conf", ".wg") else "openvpn"
        if not vpn_plugin(kind):
            label = "OpenVPN" if kind == "openvpn" else "WireGuard"
            return base.fail(f"{label} support is not installed "
                             f"(networkmanager-{kind})")
        result = util.run(
            ["nmcli", "connection", "import", "type", kind, "file", str(path)], timeout=60)
        if not result.ok:
            return base.fail(result.text.strip() or "nmcli import failed")
        return base.ok(f"Imported {path.name}",
                       details=[f"nmcli connection import type {kind}"])
    if name in ("network.vpn_connect", "network.vpn_disconnect", "network.vpn_forget"):
        connection = str(args.get("name") or "")
        if not connection:
            return base.fail("No VPN connection given")
        argv = {
            "network.vpn_connect": ["nmcli", "--wait", "30", "connection", "up", "id", connection],
            "network.vpn_disconnect": ["nmcli", "connection", "down", "id", connection],
            "network.vpn_forget": ["nmcli", "connection", "delete", "id", connection],
        }[name]
        result = util.run(argv, timeout=90)
        if not result.ok:
            return base.fail(result.text.strip() or "nmcli failed")
        return base.ok("Done", details=[f"nmcli {name.split('.', 1)[1]} {connection}"])
    if name == "network.disconnect":
        connection = str(args.get("name") or "")
        if not connection:
            return base.fail("No connection given")
        result = util.run(["nmcli", "connection", "down", "id", connection], timeout=30)
    elif name == "network.forget":
        connection = str(args.get("name") or "")
        if not connection:
            return base.fail("No connection given")
        result = util.run(["nmcli", "connection", "delete", "id", connection], timeout=30)
    elif name == "network.wifi_on":
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
