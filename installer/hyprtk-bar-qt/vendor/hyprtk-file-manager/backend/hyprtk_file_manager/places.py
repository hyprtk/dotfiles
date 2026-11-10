"""Places, GTK bookmarks, removable/block devices, and device mounting."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote

USER_DIR_NAMES = {
    "XDG_DESKTOP_DIR": "Desktop",
    "XDG_DOWNLOAD_DIR": "Downloads",
    "XDG_DOCUMENTS_DIR": "Documents",
    "XDG_PICTURES_DIR": "Pictures",
    "XDG_MUSIC_DIR": "Music",
    "XDG_VIDEOS_DIR": "Videos",
    "XDG_TEMPLATES_DIR": "Templates",
    "XDG_PUBLICSHARE_DIR": "Public",
}

MOUNT_TYPES = {
    "ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs",
    "vfat", "exfat", "ntfs", "ntfs3", "iso9660", "udf", "hfsplus", "apfs",
}


def home_dir() -> Path:
    return Path(os.environ.get("HOME") or Path.home())


def config_home(home: Path | None = None) -> Path:
    home = home or home_dir()
    return Path(os.environ.get("XDG_CONFIG_HOME") or (home / ".config"))


def parse_user_dirs(home: Path | None = None, config: Path | None = None) -> dict[str, str]:
    home = home or home_dir()
    cfg = (config or config_home(home)) / "user-dirs.dirs"
    out: dict[str, str] = {}
    if cfg.is_file():
        for line in cfg.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            if key not in USER_DIR_NAMES:
                continue
            value = raw.strip().strip('"').replace("$HOME", str(home))
            out[USER_DIR_NAMES[key]] = value
    for name in USER_DIR_NAMES.values():
        out.setdefault(name, str(home / name))
    return out


def _default_places(home: Path | None = None, config: Path | None = None) -> list[dict]:
    home = home or home_dir()
    dirs = parse_user_dirs(home, config)
    items = [{"name": "Home", "path": str(home), "icon": "user-home"}]
    for name in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"):
        target = Path(dirs[name])
        if target.is_dir():
            items.append({"name": name, "path": str(target), "icon": name.lower()})
    data_home = Path(os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share"))
    trash = data_home / "Trash" / "files"
    if trash.is_dir():
        items.append({"name": "Trash", "path": str(trash), "icon": "user-trash"})
    return items


def _bookmarks_path(home: Path | None = None, config: Path | None = None) -> Path:
    home = home or home_dir()
    return (config or config_home(home)) / "gtk-3.0" / "bookmarks"


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError:
        return []


def _write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def bookmarks(home: Path | None = None, config: Path | None = None) -> list[dict]:
    path = _bookmarks_path(home, config)
    out = []
    seen = set()
    for line in _read_lines(path):
        line = line.strip()
        if not line.startswith("file://"):
            continue
        uri, _, label = line.partition(" ")
        target = Path(unquote(uri[len("file://"):]))
        if not target.is_dir():
            continue
        key = str(target)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": label.strip() or target.name or str(target),
                "path": key,
                "icon": "folder",
                "custom": True,
            }
        )
    return out


def places(home: Path | None = None, config: Path | None = None) -> list[dict]:
    items = _default_places(home, config)
    seen = {os.path.realpath(item["path"]) for item in items}
    for item in bookmarks(home, config):
        key = os.path.realpath(item["path"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def add_bookmark(path: str, label: str | None = None, home: Path | None = None,
                 config: Path | None = None) -> dict:
    target = Path(path).expanduser()
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    bookmark_file = _bookmarks_path(home, config)
    lines = _read_lines(bookmark_file)
    wanted = str(target)
    for line in lines:
        uri = line.split(" ", 1)[0]
        if uri.startswith("file://") and unquote(uri[len("file://"):]) == wanted:
            return {"kind": "bookmark", "path": wanted, "added": False}
    name = (label or target.name or wanted).strip()
    uri = "file://" + quote(wanted, safe="/")
    lines.append(f"{uri} {name}")
    _write_lines(bookmark_file, lines)
    return {"kind": "bookmark", "path": wanted, "added": True}


def remove_bookmark(path: str, home: Path | None = None, config: Path | None = None) -> dict:
    target = str(Path(path).expanduser())
    bookmark_file = _bookmarks_path(home, config)
    keep = []
    removed = False
    for line in _read_lines(bookmark_file):
        uri = line.split(" ", 1)[0]
        if uri.startswith("file://") and unquote(uri[len("file://"):]) == target:
            removed = True
            continue
        keep.append(line)
    if removed:
        _write_lines(bookmark_file, keep)
    return {"kind": "bookmark", "path": target, "removed": removed}


def _device_icon(fstype: str, removable: bool) -> str:
    if removable:
        return "drive-removable-media-usb"
    if fstype == "iso9660":
        return "media-optical"
    return "drive-harddisk"


def _device_entry(node: dict, mounts: list[str], fstype: str, parent: dict | None = None) -> list[dict]:
    label = (node.get("label") or "").strip()
    name = node.get("name") or ""
    device = f"/dev/{name}" if name else ""
    parent = parent or {}
    tran = (node.get("tran") or parent.get("tran") or "").lower()
    removable = bool(node.get("rm") or parent.get("rm")) or tran in EXTERNAL_TRANSPORTS
    external = removable or any(
        str(mount).startswith(("/run/media/", "/media/", "/Volumes/")) for mount in mounts
    )
    size = node.get("size") or ""
    icon = _device_icon(fstype, removable)
    entries = []
    if mounts:
        for mount in mounts:
            if mount == "/":
                display = label or "System"
            elif len(mounts) == 1:
                display = label or Path(mount).name or name
            else:
                display = Path(mount).name or label or name
            entries.append({
                "name": display,
                "path": mount,
                "icon": icon,
                "device": device,
                "removable": removable,
                "external": external,
                "fs": fstype,
                "size": size,
                "mounted": True,
                "label": label,
                "uuid": node.get("uuid"),
                "partuuid": node.get("partuuid"),
                "partlabel": node.get("partlabel"),
                "tran": tran or None,
            })
    else:
        entries.append({
            "name": label or name,
            "path": None,
            "icon": icon,
            "device": device,
            "removable": removable,
            "external": external,
            "fs": fstype,
            "size": size,
            "mounted": False,
            "label": label,
            "uuid": node.get("uuid"),
            "partuuid": node.get("partuuid"),
            "partlabel": node.get("partlabel"),
            "tran": tran or None,
        })
    return entries


def parse_devices(blockdevices: list[dict]) -> list[dict]:
    out: list[dict] = []

    def walk(node: dict, parent: dict | None = None) -> None:
        fstype = node.get("fstype")
        mounts = node.get("mountpoints")
        if mounts is None:
            mount = node.get("mountpoint")
            mounts = [mount] if mount else []
        if fstype in MOUNT_TYPES:
            out.extend(_device_entry(node, list(mounts), fstype, parent))
        for child in node.get("children") or []:
            walk(child, node)

    for node in blockdevices or []:
        walk(node)
    return out


def parse_fstab(path: str | None = None) -> dict:
    paths = [Path(path)] if path else [Path("/etc/fstab")]
    if path is None:
        extra = Path("/etc/fstab.d")
        if extra.is_dir():
            paths.extend(sorted(extra.glob("*")))
    mountpoints: set[str] = set()
    devs: set[str] = set()
    uuids: set[str] = set()
    labels: set[str] = set()
    partuuids: set[str] = set()
    partlabels: set[str] = set()
    for file in paths:
        try:
            lines = file.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            source, mount, fstype = parts[0], parts[1], parts[2]
            if mount not in ("none", "swap"):
                mountpoints.add(os.path.normpath(mount))
            if fstype == "swap":
                continue
            if source.startswith("/dev/"):
                devs.add(source)
                try:
                    devs.add(os.path.realpath(source))
                except OSError:
                    pass
            elif source.startswith("UUID="):
                uuids.add(source[5:].strip().upper())
            elif source.startswith("LABEL="):
                labels.add(source[6:].strip())
            elif source.startswith("PARTUUID="):
                partuuids.add(source[9:].strip().upper())
            elif source.startswith("PARTLABEL="):
                partlabels.add(source[10:].strip())
    return {
        "mountpoints": mountpoints,
        "devices": devs,
        "uuids": uuids,
        "labels": labels,
        "partuuids": partuuids,
        "partlabels": partlabels,
    }


def _is_fstab(entry: dict, rules: dict) -> bool:
    path = entry.get("path")
    if path and os.path.normpath(path) in rules["mountpoints"]:
        return True
    device = entry.get("device")
    if device:
        if device in rules["devices"]:
            return True
        try:
            if os.path.realpath(device) in rules["devices"]:
                return True
        except OSError:
            pass
    if (entry.get("uuid") or "").upper() in rules["uuids"]:
        return bool(entry.get("uuid"))
    if entry.get("label") and entry["label"] in rules["labels"]:
        return True
    if (entry.get("partuuid") or "").upper() in rules["partuuids"]:
        return bool(entry.get("partuuid"))
    if entry.get("partlabel") and entry["partlabel"] in rules["partlabels"]:
        return True
    return False


EXTERNAL_TRANSPORTS = {"usb", "mmc", "sdio", "ieee1394"}


def _hide_internal_unmounted(entry: dict) -> bool:
    if entry.get("mounted"):
        return False
    if entry.get("removable"):
        return False
    if (entry.get("tran") or "").lower() in EXTERNAL_TRANSPORTS:
        return False
    return True


def _filesystem_entry(entries: list[dict]) -> dict:
    root = next((entry for entry in entries if entry.get("path") == "/"), None)
    if root:
        return {**root, "name": "File System", "icon": "drive-harddisk",
                "removable": False, "external": False}
    return {
        "name": "File System", "path": "/", "icon": "drive-harddisk",
        "device": "", "removable": False, "external": False, "fs": "", "size": "",
        "mounted": True, "label": "", "uuid": None, "partuuid": None,
        "partlabel": None, "tran": None,
    }


def _filter_devices(entries: list[dict], rules: dict | None = None) -> list[dict]:
    rules = parse_fstab() if rules is None else rules
    kept = [entry for entry in entries if not _is_fstab(entry, rules)]
    kept = [entry for entry in kept if entry.get("path") != "/"]
    kept = [entry for entry in kept if not _hide_internal_unmounted(entry)]
    kept.insert(0, _filesystem_entry(entries))
    return kept


def devices() -> list[dict]:
    for fields in (
        "NAME,LABEL,FSTYPE,SIZE,MOUNTPOINTS,RM,TYPE,MODEL,TRAN,UUID,PARTUUID,PARTLABEL",
        "NAME,LABEL,FSTYPE,SIZE,MOUNTPOINT,RM,TYPE,MODEL,TRAN,UUID,PARTUUID,PARTLABEL",
    ):
        try:
            proc = subprocess.run(
                ["lsblk", "-J", "-o", fields],
                capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue
        return _filter_devices(parse_devices(data.get("blockdevices") or []))
    return _filter_devices(drives())


def drives() -> list[dict]:
    out = []
    seen = set()
    try:
        text = Path("/proc/mounts").read_text(errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount, fstype = parts[0], parts[1], parts[2]
        if fstype not in MOUNT_TYPES or not device.startswith("/dev/"):
            continue
        if mount in seen or mount.startswith(("/proc", "/sys", "/dev")):
            continue
        seen.add(mount)
        out.append({
            "name": Path(mount).name or mount,
            "path": mount,
            "icon": "drive-harddisk",
            "device": device,
            "removable": False,
            "external": mount.startswith(("/run/media/", "/media/")),
            "fs": fstype,
            "size": "",
            "mounted": True,
            "tran": None,
        })
    return sorted(out, key=lambda item: item["path"])


def mount_device(device: str) -> dict:
    device = str(device)
    try:
        proc = subprocess.run(
            ["udisksctl", "mount", "-b", device],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"mount failed: {exc}") from exc
    message = (proc.stdout + "\n" + proc.stderr).strip()
    already = re.search(r"already mounted at `?([^`\n]+)`?", message, re.IGNORECASE)
    if already:
        path = already.group(1).strip().rstrip(".")
        return {"kind": "device_mount", "device": device, "path": path}
    if proc.returncode != 0:
        raise RuntimeError(message or "mount failed")
    match = re.search(r"\bat (.+?)\.?$", proc.stdout.strip(), re.IGNORECASE)
    path = match.group(1).strip().rstrip(".") if match else ""
    if not path:
        for item in devices():
            if item.get("device") == device and item.get("path"):
                path = item["path"]
                break
    if not path:
        raise RuntimeError("mount succeeded but no mountpoint was reported")
    return {"kind": "device_mount", "device": device, "path": path}


def eject_device(device: str) -> dict:
    device = str(device or "").strip()
    if not device.startswith("/dev/"):
        raise ValueError("not a block device")
    path = ""
    for item in devices():
        if item.get("device") == device and item.get("path"):
            path = item["path"]
            break
    if path == "/":
        raise RuntimeError("cannot eject the file system")
    try:
        proc = subprocess.run(
            ["udisksctl", "unmount", "-b", device],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"unmount failed: {exc}") from exc
    message = (proc.stdout + "\n" + proc.stderr).strip()
    unmounted = proc.returncode == 0 or "not mounted" in message.lower()
    if not unmounted:
        raise RuntimeError(message or "unmount failed")
    return {
        "kind": "device_eject",
        "device": device,
        "path": path,
        "unmounted": True,
        "ejected": True,
        "powered_off": False,
    }
