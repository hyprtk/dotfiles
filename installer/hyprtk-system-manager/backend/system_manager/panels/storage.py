"""Storage — block devices, mounts, fstab and removable media."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .. import form, priv, systemfiles, util
from . import base

FSTAB = Path("/etc/fstab")
FSTYPES = [
    "ext4", "ext3", "xfs", "btrfs", "f2fs", "vfat", "exfat", "ntfs3", "swap",
]
FORMAT_TYPES = ("ext4", "exfat", "vfat")
DEVICE_RE = re.compile(r"^(/dev/\S+|UUID=\S+|LABEL=\S+|PARTUUID=\S+|//\S+|\S+@\S+:\S*)$")
OPTION_RE = re.compile(r"^[A-Za-z0-9_.:=+@,/-]+$")


# Apply is a pure file edit, so a dry run can show it as a diff.
PREVIEW = "files"

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


# ── fstab ────────────────────────────────────────────────────────────────────

def parse_fstab(text: str) -> list[dict]:
    """Parse fstab into entries, keeping the source line index."""
    entries: list[dict] = []
    for index, line in enumerate((text or "").splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        try:
            dump = int(parts[4]) if len(parts) > 4 else 0
            passno = int(parts[5]) if len(parts) > 5 else 0
        except ValueError:
            dump, passno = 0, 0
        entries.append({
            "index": index,
            "device": parts[0],
            "mountpoint": parts[1],
            "fstype": parts[2],
            "options": parts[3],
            "dump": dump,
            "pass": passno,
            "line": line,
        })
    return entries


def validate_entry(entry: dict, existing: list[dict], *, exists=os.path.exists) -> list[str]:
    """Structural validation for one fstab entry (pure, testable)."""
    problems: list[str] = []
    device = str(entry.get("device") or "").strip()
    mount = str(entry.get("mountpoint") or "").strip()
    fstype = str(entry.get("fstype") or "").strip()
    options = str(entry.get("options") or "defaults").strip()

    if not DEVICE_RE.match(device):
        problems.append("device must be /dev/…, UUID=…, LABEL=…, PARTUUID=… or a network path")
    elif device.startswith("/dev/") and not exists(device):
        problems.append(f"{device} does not exist")
    if not mount.startswith("/"):
        problems.append("mount point must be an absolute path")
    elif any(char.isspace() for char in mount):
        problems.append("mount point cannot contain spaces")
    if fstype in ("", "auto"):
        problems.append("choose a filesystem type")
    elif not re.match(r"^[a-z0-9]+$", fstype):
        problems.append(f"unusual filesystem type {fstype!r}")
    if not OPTION_RE.match(options):
        problems.append("mount options may only use letters, digits and , . : = + @ _ - /")
    for other in existing:
        if other.get("mountpoint") == mount and other.get("index") != entry.get("index"):
            problems.append(f"{mount} is already mounted by another entry")
            break
    try:
        if int(entry.get("pass", 0)) not in (0, 1, 2):
            problems.append("fsck pass must be 0, 1 or 2")
        if int(entry.get("dump", 0)) not in (0, 1):
            problems.append("dump must be 0 or 1")
    except (TypeError, ValueError):
        problems.append("dump and fsck pass must be numbers")
    return problems


def verify_fstab(text: str) -> dict:
    """Run ``findmnt --verify`` against a candidate file (no root needed)."""
    if util.which("findmnt") is None:
        return {"ok": True, "checked": False, "errors": [], "warnings": []}
    fd, tmp = tempfile.mkstemp(prefix="hyprtk-fstab-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        result = util.run(["findmnt", "--verify", "--tab-file", tmp], timeout=20)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    errors, warnings = [], []
    for line in result.lines():
        stripped = line.strip()
        if stripped.startswith("[E]"):
            errors.append(stripped[3:].strip())
        elif stripped.startswith("[W]"):
            warnings.append(stripped[3:].strip())
    return {"ok": not errors and result.code in (0, 1), "checked": True,
            "errors": errors, "warnings": warnings,
            "output": result.text.strip()}


def _entry_line(entry: dict) -> str:
    return " ".join([
        str(entry["device"]), str(entry["mountpoint"]), str(entry["fstype"]),
        str(entry.get("options") or "defaults"), str(int(entry.get("dump", 0))),
        str(int(entry.get("pass", 0))),
    ])


# ── probe ────────────────────────────────────────────────────────────────────

def _devices() -> list[dict]:
    if util.which("lsblk") is None:
        return []
    payload = util.run_json([
        "lsblk", "-J", "-o",
        "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,ROTA,TRAN,LABEL",
    ], timeout=15)
    return parse_lsblk(payload)


def _device_rows(devices: list[dict]) -> list[dict]:
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
        if device.get("type") in ("part", "lvm") and device.get("fstype") and util.which("udisksctl"):
            if mounted:
                actions.append({"label": "Unmount", "action": "storage.unmount",
                                "args": {"device": f"/dev/{device['name']}"}})
            else:
                actions.append({"label": "Mount", "action": "storage.mount",
                                "args": {"device": f"/dev/{device['name']}"}})
        if (device.get("type") == "part" and device.get("tran") == "usb"
                and not mounted):
            name = str(device.get("name"))
            for fstype in FORMAT_TYPES:
                if util.which(f"mkfs.{fstype}") is None:
                    continue
                actions.append({
                    "label": f"Format {fstype}", "action": "storage.format",
                    "args": {"device": f"/dev/{name}", "fstype": fstype},
                    "danger": True, "confirm": name,
                    "message": f"Erase every file on /dev/{name} and write a {fstype} "
                               f"filesystem. Type {name} to confirm.",
                })
        items.append({"title": str(title), "subtitle": subtitle,
                      "badges": ["mounted"] if mounted else [], "actions": actions})
    return items


def _fstab_section() -> list[dict]:
    text = util.read_text(FSTAB)
    entries = parse_fstab(text)
    if not entries:
        return [form.note("/etc/fstab has no active entries.", "warn")]
    items: list[dict] = []
    for entry in entries:
        subtitle = f"{entry['device']} · {entry['fstype']} · {entry['options']}"
        actions = [{
            "label": "Remove entry", "action": "storage.fstab_remove",
            "args": {"line": entry["index"]},
            "danger": True, "confirm": "remove",
            "message": f"Remove the entry for {entry['mountpoint']} from /etc/fstab? "
                       "The filesystem is not touched and the current mount stays "
                       "until you unmount it.",
        }]
        items.append({
            "title": entry["mountpoint"], "subtitle": subtitle,
            "badges": ["fstab"], "actions": actions,
        })
    return [form.list_row(items)]


def _add_form_rows() -> list[dict]:
    return [
        form.note("A new entry is validated with findmnt before anything is written. "
                  "The mount point is created, /etc/fstab is backed up first and the "
                  "write needs root.", "info"),
        form.text("fstab_device", "Device", "",
                  placeholder="/dev/sdb1 or UUID=…", mono=True),
        form.path("fstab_mount", "Mount point", "/mnt/data", mode="dir", mono=True),
        form.choice("fstab_type", "Filesystem", "ext4",
                    [{"value": item, "label": item} for item in FSTYPES]),
        form.text("fstab_options", "Options", "defaults", mono=True),
        form.number("fstab_pass", "fsck pass", 2, minimum=0, maximum=2),
        form.action("Validate /etc/fstab", "storage.fstab_verify"),
    ]


def probe() -> dict:
    devices = _devices()
    disk = util.disk_usage("/")
    sections = [form.section("System disk", [
        form.info("Used", util.human_bytes(disk["used"])),
        form.info("Free", util.human_bytes(disk["free"])),
        form.info("Total", util.human_bytes(disk["total"])),
    ])]

    if util.which("lsblk") is None:
        sections.append(form.section("Devices", [base.missing_note("lsblk", "util-linux")]))
    else:
        rows = _device_rows(devices)
        sections.append(form.section("Devices", [
            form.list_row(rows) if rows else form.note("No block devices found.", "warn"),
        ]))

    sections.append(form.section("Mounted at boot (/etc/fstab)", _fstab_section()))
    sections.append(form.section("Add a mount", _add_form_rows()))
    sections.append(form.section("Notes", [
        form.note("Mounting removable media uses udisks2 and needs no root. "
                  "Formatting a device is only offered for unmounted removable "
                  "partitions and always asks for the device name.", "info"),
    ]))
    status = "full" if util.which("udisksctl") and util.which("findmnt") else "partial"
    return base.make_page("storage", sections, status=status)


# ── apply ────────────────────────────────────────────────────────────────────

def _fstab_changes(changes: dict) -> dict:
    text = util.read_text(FSTAB)
    entries = parse_fstab(text)
    entry = {
        "device": str(changes.get("fstab_device") or "").strip(),
        "mountpoint": str(changes.get("fstab_mount") or "").strip(),
        "fstype": str(changes.get("fstab_type") or "").strip(),
        "options": str(changes.get("fstab_options") or "defaults").strip(),
        "dump": 0,
        "pass": changes.get("fstab_pass", 2),
    }
    problems = validate_entry(entry, entries)
    if problems:
        return base.fail("Cannot add the entry", details=problems)

    mountpoint = Path(entry["mountpoint"])
    if not mountpoint.is_dir():
        result = priv.run_priv(["install", "-d", "-m", "0755", str(mountpoint)], timeout=30,
                             action="storage")
        if not result.ok:
            return base.denied(result.text.strip() or "Could not create the mount point",
                               priv.command_for(["install", "-d", str(mountpoint)], "storage"))

    candidate = text.rstrip("\n") + "\n" + _entry_line(entry) + "\n"
    verified = verify_fstab(candidate)
    if verified.get("errors"):
        return base.fail("findmnt rejected the entry", details=verified["errors"])
    result = systemfiles.write_with_backup(FSTAB, candidate, action="storage")
    if not result.ok:
        return base.denied(result.text.strip() or "Could not write /etc/fstab",
                           priv.command_for(["install", str(FSTAB)], "storage"))
    details = [f"{entry['device']} → {entry['mountpoint']} ({entry['fstype']})"]
    details += [f"warning: {item}" for item in verified.get("warnings") or []]
    return base.ok("Added the entry to /etc/fstab", details=details)


def apply(changes: dict) -> dict:
    if any(key.startswith("fstab_") for key in changes):
        return _fstab_changes(changes)
    return base.ok("Nothing to change")


# ── actions ──────────────────────────────────────────────────────────────────

def _fstab_remove(line_index) -> dict:
    text = util.read_text(FSTAB)
    lines = text.splitlines()
    try:
        index = int(line_index)
    except (TypeError, ValueError):
        return base.fail("Invalid fstab entry")
    if index < 0 or index >= len(lines):
        return base.fail("Invalid fstab entry")
    if lines[index].strip().startswith("#") or not lines[index].strip():
        return base.fail("That line is not an active entry")
    removed = lines[index]
    remaining = lines[:index] + lines[index + 1:]
    candidate = "\n".join(remaining).rstrip("\n") + "\n"
    verified = verify_fstab(candidate)
    if verified.get("errors"):
        return base.fail("findmnt rejected the result", details=verified["errors"])
    result = systemfiles.write_with_backup(FSTAB, candidate, action="storage")
    if not result.ok:
        return base.denied(result.text.strip() or "Could not write /etc/fstab",
                           priv.command_for(["install", str(FSTAB)], "storage"))
    return base.ok("Entry removed from /etc/fstab", details=[removed.strip()])


def _verify_current() -> dict:
    verified = verify_fstab(util.read_text(FSTAB))
    if not verified.get("checked"):
        return base.fail("findmnt is not installed")
    if verified.get("errors"):
        return base.fail("Problems found", details=verified["errors"])
    details = [f"warning: {item}" for item in verified.get("warnings") or []]
    return base.ok("No errors in /etc/fstab", details=details)


def action(name: str, args: dict) -> dict:
    device = str(args.get("device") or "")
    if name in ("storage.mount", "storage.unmount"):
        if not device.startswith("/dev/"):
            return base.fail("Invalid device")
        if util.which("udisksctl") is None:
            return base.fail("udisksctl is not installed")
        result = util.run(["udisksctl", "unmount" if name.endswith("unmount") else "mount",
                           "-b", device], timeout=30)
        if not result.ok:
            return base.fail(result.text.strip() or "udisksctl failed")
        return base.ok("Done", details=result.out.strip().splitlines())
    if name == "storage.fstab_remove":
        return _fstab_remove(args.get("line"))
    if name == "storage.fstab_verify":
        return _verify_current()
    if name == "storage.format":
        fstype = str(args.get("fstype") or "")
        if fstype not in FORMAT_TYPES:
            return base.fail("Unsupported filesystem")
        if not device.startswith("/dev/"):
            return base.fail("Invalid device")
        binary = util.which(f"mkfs.{fstype}")
        if binary is None:
            return base.fail(f"mkfs.{fstype} is not installed")
        mount = util.run(["findmnt", "-n", "-S", device], timeout=8)
        if mount.ok and mount.out.strip():
            return base.fail(f"{device} is mounted; unmount it first")
        result = priv.run_priv([binary, "-F", device] if fstype != "exfat"
                               else [binary, device], timeout=300, action="storage")
        if not result.ok:
            return base.denied(result.text.strip() or "Formatting failed",
                               priv.command_for([binary, device], "storage"))
        return base.ok(f"Formatted {device} as {fstype}")
    return base.fail(f"unknown action {name!r}")
