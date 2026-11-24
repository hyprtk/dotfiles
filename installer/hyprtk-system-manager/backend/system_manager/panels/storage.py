"""Storage — block devices, usage and removable media."""

from __future__ import annotations

from .. import form, util
from . import base


def _flatten(nodes: list[dict], depth: int = 0) -> list[dict]:
    out: list[dict] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        item = dict(node)
        item["depth"] = depth
        out.append(item)
        out.extend(_flatten(node.get("children") or [], depth + 1))
    return out


def parse_lsblk(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    return _flatten(payload.get("blockdevices") or [])


def probe() -> dict:
    if util.which("lsblk") is None:
        return base.make_page("storage", [
            form.section("Unavailable", [base.missing_note("lsblk", "util-linux")]),
        ])

    payload = util.run_json([
        "lsblk", "-J", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,ROTA,TRAN,LABEL",
    ], timeout=15)
    devices = parse_lsblk(payload)

    items = []
    for device in devices:
        if device.get("type") not in ("disk", "part", "crypt", "lvm"):
            continue
        mounted = device.get("mountpoint")
        title = device.get("label") or device.get("name")
        subtitle = " · ".join(part for part in [
            device.get("name"), device.get("size"), device.get("fstype"),
            ("mounted at " + str(mounted)) if mounted else "not mounted",
            "removable" if device.get("tran") == "usb" else "",
        ] if part)
        actions = []
        if device.get("type") == "part" and device.get("fstype") and util.which("udisksctl"):
            if mounted:
                actions.append({"label": "Unmount", "action": "storage.unmount",
                                "args": {"device": f"/dev/{device['name']}"}})
            else:
                actions.append({"label": "Mount", "action": "storage.mount",
                                "args": {"device": f"/dev/{device['name']}"}})
        items.append({"title": str(title), "subtitle": subtitle,
                      "badges": ["mounted"] if mounted else [], "actions": actions})

    disk = util.disk_usage("/")
    return base.make_page("storage", [
        form.section("System disk", [
            form.info("Used", util.human_bytes(disk["used"])),
            form.info("Free", util.human_bytes(disk["free"])),
            form.info("Total", util.human_bytes(disk["total"])),
        ]),
        form.section("Devices", [
            form.list_row(items) if items else form.note("No block devices found.", "warn"),
        ]),
        form.section("Notes", [
            form.note("Mounting removable media uses udisks2 and needs no root. Formatting, "
                      "LUKS and fstab editing are deliberately not exposed yet.", "info"),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    device = str(args.get("device") or "")
    if not device.startswith("/dev/"):
        return base.fail("Invalid device")
    if util.which("udisksctl") is None:
        return base.fail("udisksctl is not installed")
    if name == "storage.mount":
        result = util.run(["udisksctl", "mount", "-b", device], timeout=30)
    elif name == "storage.unmount":
        result = util.run(["udisksctl", "unmount", "-b", device], timeout=30)
    else:
        return base.fail(f"unknown action {name!r}")
    if not result.ok:
        return base.fail(result.text.strip() or "udisksctl failed")
    return base.ok("Done", details=result.out.strip().splitlines())
