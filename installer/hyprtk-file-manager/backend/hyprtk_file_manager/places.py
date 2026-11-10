"""XDG places, GTK bookmarks, and mounted drives."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote

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


def places(home: Path | None = None, config: Path | None = None) -> list[dict]:
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


def bookmarks(home: Path | None = None, config: Path | None = None) -> list[dict]:
    home = home or home_dir()
    path = (config or config_home(home)) / "gtk-3.0" / "bookmarks"
    out = []
    seen = set()
    if not path.is_file():
        return out
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("file://"):
            continue
        uri, _, label = line.partition(" ")
        target = Path(unquote(uri[len("file://"):]))
        if not target.is_dir() or str(target) in seen:
            continue
        seen.add(str(target))
        out.append(
            {
                "name": label.strip() or target.name or str(target),
                "path": str(target),
                "icon": "folder",
            }
        )
    return out


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
        out.append(
            {
                "name": Path(mount).name or mount,
                "path": mount,
                "icon": "drive-harddisk",
                "device": device,
            }
        )
    return sorted(out, key=lambda item: item["path"])
