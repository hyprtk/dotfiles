"""Transactional file edits with snapshots.

Before a panel writes anything it opens a :class:`Session`, which copies each
touched file into ``~/.config/hyprtk-system-manager/backups/<stamp>/`` and
records a manifest. A failure rolls every file back; a success leaves a
restorable snapshot behind.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .util import atomic_write, read_text, write_json

_LOCK = threading.Lock()


class TransactionError(RuntimeError):
    pass


@dataclass
class Session:
    reason: str
    stamp: str = ""
    originals: dict[str, str] = field(default_factory=dict)
    missing: set[str] = field(default_factory=set)
    files: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.time)
    finished: bool = False

    def __post_init__(self) -> None:
        self.stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
        paths.ensure_state()

    # ── recording ──────────────────────────────────────────────────────
    def touch(self, path: str | Path) -> Path:
        target = Path(path).expanduser()
        key = str(target)
        if key in self.originals:
            return target
        if key in self.missing:
            return target
        if target.is_file():
            with _LOCK:
                self.originals[key] = read_text(target)
        else:
            self.missing.add(key)
        return target

    def write(self, path: str | Path, text: str) -> None:
        target = self.touch(path)
        atomic_write(target, text)
        if str(target) not in self.files:
            self.files.append(str(target))

    def write_json(self, path: str | Path, data: object) -> None:
        self.write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # ── finishing ──────────────────────────────────────────────────────
    def rollback(self) -> None:
        for name, text in self.originals.items():
            try:
                atomic_write(name, text)
            except OSError:
                pass
        for name in self.missing:
            try:
                Path(name).unlink()
            except OSError:
                pass
        self.finished = True

    def commit(self, status: str = "ok", error: str | None = None) -> dict:
        manifest = {
            "stamp": self.stamp,
            "reason": self.reason,
            "status": status,
            "error": error,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.started)),
            "files": self.files,
        }
        if status == "ok" and self.files:
            root = paths.BACKUP_ROOT / self.stamp
            root.mkdir(parents=True, exist_ok=True)
            for name in self.files:
                source = Path(name)
                if not source.is_file():
                    continue
                rel = str(source).lstrip("/").replace("/", "__")
                try:
                    shutil.copy2(source, root / rel)
                except OSError:
                    pass
            (root / "original").mkdir(exist_ok=True)
            for name, text in self.originals.items():
                rel = str(Path(name)).lstrip("/").replace("/", "__")
                try:
                    atomic_write(root / "original" / rel, text)
                except OSError:
                    pass
            write_json(root / "manifest.json", manifest)
        self.finished = True
        return manifest


def backups() -> list[dict]:
    root = paths.BACKUP_ROOT
    if not root.is_dir():
        return []
    items: list[dict] = []
    for child in sorted(root.iterdir(), reverse=True):
        manifest = child / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            items.append(data)
    return items


def restore(stamp: str) -> dict:
    root = paths.BACKUP_ROOT / stamp
    manifest_file = root / "manifest.json"
    if not manifest_file.is_file():
        raise TransactionError(f"no backup {stamp!r}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    restored: list[str] = []
    for name in manifest.get("files") or []:
        rel = str(Path(name)).lstrip("/").replace("/", "__")
        source = root / "original" / rel
        if not source.is_file():
            continue
        atomic_write(name, read_text(source))
        restored.append(name)
    return {"stamp": stamp, "restored": restored}
