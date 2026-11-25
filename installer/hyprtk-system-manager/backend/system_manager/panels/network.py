"""Network — NetworkManager devices, Wi-Fi networks and saved connections.

Connecting to a secured network never puts the password in argv. A temporary
``0600`` passwd-file is handed to ``nmcli connection up ... passwd-file`` and
unlinked immediately afterwards; the password is not logged or returned.
"""

from __future__ import annotations

import ipaddress
import os
import re
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


def parse_all_connections(text: str) -> list[dict]:
    """Every terse connection row, regardless of type (no Wi-Fi filter)."""
    rows: list[dict] = []
    for line in text.splitlines():
        parts = _split_terse(line)
        if len(parts) < 3:
            continue
        rows.append({"name": parts[0], "type": parts[1], "device": parts[2],
                     "active": bool(parts[2])})
    return [row for row in rows if row["type"] != "loopback"]


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


def validate_dns(value: str) -> list[str]:
    problems = []
    for part in [item.strip() for item in (value or "").split(",") if item.strip()]:
        try:
            ipaddress.ip_address(part)
        except ValueError:
            problems.append(f"{part} is not an IP address")
    return problems


def validate_search(value: str) -> list[str]:
    problems = []
    for part in [item.strip() for item in (value or "").split(",") if item.strip()]:
        if not re.match(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$", part):
            problems.append(f"{part} is not a domain name")
    return problems


def _active_connections() -> list[dict]:
    text = util.run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show",
                     "--active"], timeout=10).out
    return parse_all_connections(text)


def parse_dns_state(lines) -> dict:
    values = [str(line).strip() for line in lines]
    while len(values) < 4:
        values.append("")
    return {"method": values[0], "dns": values[1], "search": values[2],
            "ignore_auto": values[3].lower() in ("yes", "true")}


def _dns_state(name: str) -> dict:
    result = util.run(["nmcli", "-g",
                       "ipv4.method,ipv4.dns,ipv4.dns-search,ipv4.ignore-auto-dns",
                       "connection", "show", name], timeout=8)
    return parse_dns_state(result.out.splitlines())


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

    active = _active_connections()
    dns_rows: list[dict] = []
    if active:
        current = active[0]
        state = _dns_state(current["name"])
        dns_rows = [
            form.choice("dns_connection", "Connection", current["name"],
                        [{"value": item["name"], "label": f"{item['name']} ({item['device']})"}
                         for item in active]),
            form.info("IPv4 method", state["method"] or "auto", mono=True),
            form.text("dns_servers", "DNS servers", state["dns"].replace(" ", ", "),
                      mono=True, placeholder="1.1.1.1, 9.9.9.9",
                      help="Comma-separated addresses. Empty follows the network."),
            form.text("dns_search", "Search domains", state["search"].replace(" ", ", "),
                      mono=True, placeholder="lan, example.com"),
            form.toggle("ignore_auto_dns", "Ignore DHCP DNS servers", state["ignore_auto"]),
            form.note("The change is written to the NetworkManager connection and is "
                      "used the next time it is activated.", "info"),
        ]
    else:
        dns_rows = [form.note("No active connection to configure DNS on.", "info")]

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
        form.section("DNS", dns_rows),
        form.section("VPN", vpn_rows),
        form.section("Available networks", [
            form.list_row(wifi_items) if wifi_items else
            form.note("No Wi-Fi networks visible (the radio may be off).", "info"),
        ]),
    ], status="full" if active else "partial")


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


def _apply_dns(changes: dict) -> dict:
    name = str(changes.get("dns_connection") or "").strip()
    known = [item["name"] for item in _active_connections()]
    if not name:
        name = known[0] if known else ""
    if not name:
        return base.fail("There is no active connection to configure")
    if name not in known and not util.run(
            ["nmcli", "-g", "NAME", "connection", "show", name], timeout=8).ok:
        return base.fail(f"No NetworkManager connection named {name!r}")

    dns = str(changes.get("dns_servers") or "").strip()
    search = str(changes.get("dns_search") or "").strip()
    problems = validate_dns(dns) + validate_search(search)
    if problems:
        return base.fail("Check the values", details=problems)

    argv = ["nmcli", "connection", "modify", name,
            "ipv4.dns", ", ".join(part.strip() for part in dns.split(",") if part.strip()),
            "ipv4.dns-search",
            ", ".join(part.strip() for part in search.split(",") if part.strip())]
    if "ignore_auto_dns" in changes:
        argv += ["ipv4.ignore-auto-dns",
                 "yes" if changes.get("ignore_auto_dns") else "no"]
    result = util.run(argv, timeout=20)
    if not result.ok:
        return base.fail(result.text.strip() or "nmcli failed")
    return base.ok(f"DNS saved for {name}", details=["activates on the next connection"])


def apply(changes: dict) -> dict:
    if any(str(key).startswith("dns_") or key == "ignore_auto_dns" for key in changes):
        return _apply_dns(changes)
    return base.ok("Nothing to change")


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
