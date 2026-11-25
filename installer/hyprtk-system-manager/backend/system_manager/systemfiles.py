"""Edits to root-owned system files through the privilege layer.

Panels that change ``/etc/fstab`` or a kernel sysfs threshold cannot use
:class:`system_manager.state.Session` — that writes as the current user. This
module keeps the same contract (read the original, write atomically, keep a
snapshot and a way back) for files only root may write.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from . import paths, priv
from .util import RunResult, read_text


class SystemFileError(RuntimeError):
    pass


def read(path: str | Path) -> str:
    return read_text(path)


def write(path: str | Path, text: str, *, mode: str = "0644",
          action: str = "system") -> RunResult:
    """Install *text* as *path* through sudo/pkexec.

    ``install`` is an absolute system binary, so it works under ``pkexec``,
    which sanitises PATH. The temporary file lives in the user's state dir so a
    root process can always read it. In preview mode nothing is installed.
    """
    from . import preview

    if preview.active():
        preview.record(path, read(path), text)
        return RunResult(0, "", "", ["(preview)", "install", str(path)])
    root = paths.ensure_state() / "staging"
    root.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(root), prefix="edit-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        return priv.run_priv(["install", "-m", mode, tmp, str(path)], timeout=60,
                             action=action)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def snapshot(path: str | Path, text: str | None = None) -> Path:
    """Keep the pre-edit contents under the state dir; return the file."""
    root = paths.ensure_state() / "system"
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    name = str(path).lstrip("/").replace("/", "__")
    target = root / f"{name}.{stamp}"
    from .util import atomic_write

    atomic_write(target, read_text(path) if text is None else text)
    return target


def write_with_backup(path: str | Path, text: str, *, mode: str = "0644",
                       action: str = "system") -> RunResult:
    snapshot(path, read(path))
    return write(path, text, mode=mode, action=action)
