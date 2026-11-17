"""Session state and crash-recovery drafts.

Session: which files were open, where the caret and scroll were. Written on a
debounce by the UI, read at startup when ``restore_session`` is on.

Drafts: every modified buffer is written to the cache directory every few
seconds. A clean save or close deletes the draft; an unsaved close leaves it
behind, so the next launch can offer it back. This is the one file-editor
promise worth never breaking.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from .settings import cache_home, state_home


def _atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


class Session:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (state_home() / "session.json")

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"docs": [], "active": ""}
        if not isinstance(data, dict):
            return {"docs": [], "active": ""}
        docs = []
        for item in data.get("docs") or []:
            if not isinstance(item, dict):
                continue
            doc = {
                "id": str(item.get("id") or ""),
                "path": str(item.get("path") or ""),
                "cursor": int(item.get("cursor") or 0),
                "scroll": float(item.get("scroll") or 0.0),
                "language": str(item.get("language") or ""),
                "encoding": str(item.get("encoding") or ""),
            }
            if doc["id"]:
                docs.append(doc)
        return {"docs": docs, "active": str(data.get("active") or "")}

    def save(self, data: dict) -> None:
        payload = {
            "version": 1,
            "ts": time.time(),
            "active": str((data or {}).get("active") or ""),
            "docs": (data or {}).get("docs") or [],
        }
        _atomic_json(self.path, payload)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


class Drafts:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (cache_home() / "drafts")
        self.index_path = self.root / "index.json"

    def _index(self) -> list[dict]:
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return [item for item in data if isinstance(item, dict) and item.get("id")]

    def _write_index(self, items: list[dict]) -> None:
        _atomic_json(self.index_path, items)

    def _draft_path(self, doc_id: str) -> Path:
        safe = "".join(ch for ch in doc_id if ch.isalnum() or ch in "-_")[:64]
        return self.root / f"{safe}.json"

    def save(self, doc_id: str, path: str, title: str, text: str) -> None:
        if not doc_id:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        _atomic_json(
            self._draft_path(doc_id),
            {"id": doc_id, "path": path, "title": title, "text": text, "ts": time.time()},
        )
        items = [item for item in self._index() if item.get("id") != doc_id]
        items.append(
            {"id": doc_id, "path": path, "title": title, "ts": time.time(), "chars": len(text)}
        )
        self._write_index(items)

    def load(self, doc_id: str) -> dict | None:
        try:
            data = json.loads(self._draft_path(doc_id).read_text(encoding="utf-8"))
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def clear(self, doc_id: str) -> None:
        try:
            self._draft_path(doc_id).unlink()
        except OSError:
            pass
        items = [item for item in self._index() if item.get("id") != doc_id]
        self._write_index(items)

    def list(self, max_age_days: int = 30) -> list[dict]:
        cutoff = time.time() - max_age_days * 86400
        items = []
        for item in self._index():
            if float(item.get("ts") or 0) < cutoff:
                self.clear(str(item.get("id")))
                continue
            if not self._draft_path(str(item["id"])).exists():
                continue
            items.append(item)
        items.sort(key=lambda item: float(item.get("ts") or 0), reverse=True)
        return items

    def prune(self, max_age_days: int = 30) -> None:
        self.list(max_age_days)
