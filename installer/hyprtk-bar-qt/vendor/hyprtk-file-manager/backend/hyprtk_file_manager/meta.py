"""File metadata, permissions, and checksums."""

from __future__ import annotations

import grp
import hashlib
import os
import pwd
from pathlib import Path


def file_info(path: str) -> dict:
    target = Path(path).expanduser()
    stat = target.lstat()
    if target.is_symlink():
        kind = "link"
    elif target.is_dir():
        kind = "dir"
    else:
        kind = "file"
    try:
        owner = pwd.getpwuid(stat.st_uid).pw_name
    except KeyError:
        owner = str(stat.st_uid)
    try:
        group = grp.getgrgid(stat.st_gid).gr_name
    except KeyError:
        group = str(stat.st_gid)
    return {
        "kind": "stat",
        "path": str(target),
        "name": target.name,
        "type": kind,
        "size": stat.st_size,
        "mode": stat.st_mode,
        "mode_octal": format(stat.st_mode & 0o7777, "04o"),
        "mtime": stat.st_mtime,
        "ctime": stat.st_ctime,
        "atime": stat.st_atime,
        "uid": stat.st_uid,
        "gid": stat.st_gid,
        "owner": owner,
        "group": group,
        "inode": stat.st_ino,
        "nlink": stat.st_nlink,
        "target": os.readlink(target) if target.is_symlink() else None,
    }


def chmod(path: str, mode) -> dict:
    target = Path(path).expanduser()
    if isinstance(mode, str):
        raw = mode.strip()
        if raw.lower().startswith("0o"):
            raw = raw[2:]
        value = int(raw, 8)
    elif isinstance(mode, int):
        value = mode
    else:
        raise ValueError("invalid mode")
    if value < 0 or value > 0o7777:
        raise ValueError("invalid mode")
    os.chmod(target, value)
    return {
        "kind": "chmod",
        "path": str(target),
        "mode": value,
        "mode_octal": format(value & 0o7777, "04o"),
    }


def checksum(path: str, algo: str = "sha256") -> dict:
    if algo not in ("sha256", "sha1", "md5"):
        raise ValueError("unsupported checksum")
    target = Path(path).expanduser()
    digest = hashlib.new(algo)
    size = 0
    with open(target, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "kind": "checksum",
        "path": str(target),
        "algo": algo,
        "hex": digest.hexdigest(),
        "size": size,
    }
