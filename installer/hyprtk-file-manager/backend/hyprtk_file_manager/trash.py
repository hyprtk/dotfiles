"""Restore files from the home trash."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote


def trash_root() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "Trash"


def restore(path: str, root: Path | None = None) -> dict:
    target = Path(path)
    base = Path(root) if root else trash_root()
    info = base / "info" / (target.name + ".trashinfo")
    if not info.is_file():
        raise FileNotFoundError(str(info))
    original = None
    for line in info.read_text(errors="replace").splitlines():
        if line.startswith("Path="):
            original = unquote(line[5:].strip())
            break
    if not original:
        raise ValueError("trashinfo is missing Path")
    destination = Path(original)
    if destination.exists():
        raise FileExistsError(str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(destination))
    info.unlink()
    return {"kind": "restore", "path": str(target), "original": str(destination)}


def empty() -> dict:
    subprocess.run(["gio", "trash", "--empty"], check=True, capture_output=True, text=True)
    return {"kind": "trash_empty", "ok": True}
