"""Backups, atomic writes and verified transactions."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .paths import BACKUP_ROOT


class TransactionError(RuntimeError):
    pass


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Transaction:
    """Stage edits, back up, write, verify; roll back on any failure."""

    def __init__(self, root: Path, reason: str) -> None:
        self.root = Path(root).expanduser()
        self.reason = reason
        self._staged: dict[str, tuple[str, str]] = {}

    def stage(self, edit) -> None:
        rel = str(edit.relpath)
        if rel in self._staged:
            # Fold a second edit into the same file.
            original, _ = self._staged[rel]
            self._staged[rel] = (original, edit.updated)
        else:
            self._staged[rel] = (edit.original, edit.updated)

    @property
    def files(self) -> list[str]:
        return [k for k, (orig, new) in self._staged.items() if orig != new]

    def commit(self, verify: Callable[[], None] | None = None) -> dict | None:
        changed = {rel: self._staged[rel] for rel in self.files}
        if not changed:
            return None

        stamp = _stamp()
        dest = BACKUP_ROOT / stamp
        manifest = {
            "stamp": stamp,
            "reason": self.reason,
            "root": str(self.root),
            "files": sorted(changed),
            "created": stamp,
            "status": "pending",
        }
        for rel, (original, _) in changed.items():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(original, encoding="utf-8")
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        written: list[str] = []
        try:
            for rel, (_, new) in changed.items():
                atomic_write(self.root / rel, new)
                written.append(rel)
            if verify is not None:
                verify()
            manifest["status"] = "ok"
        except BaseException as exc:
            for rel in written:
                try:
                    atomic_write(self.root / rel, changed[rel][0])
                except OSError:
                    pass
            manifest["status"] = "rolled-back"
            manifest["error"] = str(exc)
            (dest / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            raise
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return manifest


class Session:
    """Sequential, verified edits on disk with a shared backup record.

    Edits are computed one at a time (so each probe sees the previous change),
    and every touched file is backed up before its first write. Any failure
    restores all of them byte-identically.
    """

    def __init__(self, root: Path, reason: str) -> None:
        self.root = Path(root).expanduser()
        self.reason = reason
        self.stamp = _stamp()
        self.dir = BACKUP_ROOT / self.stamp
        self.saved: dict[str, str] = {}
        self.files: list[str] = []

    def write(self, edit) -> bool:
        rel = str(edit.relpath)
        if not edit.changed:
            return False
        if rel not in self.saved:
            self.saved[rel] = edit.original
            target = self.dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(edit.original, encoding="utf-8")
        atomic_write(self.root / rel, edit.updated)
        if rel not in self.files:
            self.files.append(rel)
        return True

    def _manifest(self, status: str, error: str | None = None) -> dict:
        data = {
            "stamp": self.stamp,
            "reason": self.reason,
            "root": str(self.root),
            "files": sorted(self.files),
            "created": self.stamp,
            "status": status,
        }
        if error:
            data["error"] = error
        if self.saved:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / "manifest.json").write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
        return data

    def rollback(self) -> None:
        for rel, original in self.saved.items():
            try:
                atomic_write(self.root / rel, original)
            except OSError:
                pass

    def finish(self, status: str = "ok", error: str | None = None) -> dict | None:
        if not self.saved:
            return None
        return self._manifest(status, error)


def backups() -> list[dict]:
    out: list[dict] = []
    if not BACKUP_ROOT.is_dir():
        return out
    for entry in sorted(BACKUP_ROOT.iterdir(), reverse=True):
        manifest = entry / "manifest.json"
        if manifest.is_file():
            try:
                out.append(json.loads(manifest.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return out


def restore(stamp: str, *, root: Path | None = None) -> dict:
    src = BACKUP_ROOT / stamp
    manifest_path = src / "manifest.json"
    if not manifest_path.is_file():
        raise TransactionError(f"no backup {stamp}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = Path(root).expanduser() if root else Path(manifest.get("root") or "")
    if not root or not str(root):
        raise TransactionError("backup has no root")

    restored: list[str] = []
    for rel in manifest.get("files") or []:
        backup = src / rel
        if not backup.is_file():
            continue
        atomic_write(root / rel, backup.read_text(encoding="utf-8"))
        restored.append(rel)

    manifest.setdefault("restores", []).append(_stamp())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"stamp": stamp, "root": str(root), "restored": restored}


def prune(keep: int = 30) -> list[str]:
    """Keep the newest `keep` backup dirs; return removed stamps."""
    if not BACKUP_ROOT.is_dir():
        return []
    dirs = [d for d in BACKUP_ROOT.iterdir() if d.is_dir()]
    dirs.sort(reverse=True)
    removed = []
    for d in dirs[keep:]:
        shutil.rmtree(d, ignore_errors=True)
        removed.append(d.name)
    return removed
