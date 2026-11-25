"""Remote and virtual locations: SFTP/SMB mounts, MTP devices, cloud drives.

Mounting is delegated to :mod:`hyprtk_file_manager.network`, which already owns
the GVfs/Gio mounting and credential handling. This module is the *inventory*:
what is mounted under ``/run/user/<uid>/gvfs``, what kind it is, and a stable
label. The UI navigates to the local GVfs path, so a remote behaves like a
folder and every existing operation keeps working.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import network

CLOUD_PREFIXES = ("google-drive", "nextcloud", "owncloud", "dav", "onedrive",
                  "dropbox")


def gvfs_root() -> Path:
    return Path("/run/user") / str(os.getuid()) / "gvfs"


def classify(uri: str) -> str:
    text = (uri or "").strip().lower()
    if text.startswith("sftp://"):
        return "sftp"
    if text.startswith("smb://"):
        return "smb"
    if text.startswith("nfs://"):
        return "nfs"
    if text.startswith("mtp://"):
        return "mtp"
    if text.startswith(("dav://", "davs://")):
        return "cloud"
    if text.startswith(("ftp://", "ftps://")):
        return "other"
    return ""


def kind_of_mount(name: str) -> str:
    if name.startswith("sftp:"):
        return "sftp"
    if name.startswith("smb-share:"):
        return "smb"
    if name.startswith("nfs-share:"):
        return "nfs"
    if name.startswith("mtp:") or name.startswith("gphoto2:"):
        return "mtp"
    if any(name.startswith(prefix) for prefix in CLOUD_PREFIXES):
        return "cloud"
    return "other"


def label_for(name: str) -> str:
    if name.startswith("smb-share:"):
        return name.split("=")[-1] or name
    if name.startswith("mtp:"):
        return "MTP device"
    if name.startswith("sftp:"):
        return name.replace("sftp:", "").replace("=", "/")
    return name.split("=")[-1] or name


def mounts() -> list[dict]:
    root = gvfs_root()
    if not root.is_dir():
        return []
    out: list[dict] = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if entry.is_dir():
            out.append({"name": entry.name, "kind": kind_of_mount(entry.name),
                        "path": str(entry), "label": label_for(entry.name)})
    return out


def connect(uri: str, username: str = "", password: str = "", domain: str = "") -> dict:
    kind = classify(uri)
    if kind == "":
        raise RuntimeError("expected a sftp://, smb://, nfs://, dav:// or ftp:// address")
    result = network.mount(uri, username, password, domain)
    result["remote_kind"] = kind
    return result


def devices() -> list[dict]:
    """MTP phones and cloud drives, separated from network shares."""
    return [item for item in mounts() if item["kind"] in ("mtp", "cloud")]
