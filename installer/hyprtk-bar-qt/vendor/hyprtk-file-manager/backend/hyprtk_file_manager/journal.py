"""Undo/redo journal persisted under the user state directory."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path


class Journal:
    def __init__(self, path: Path, limit: int = 100):
        self.path = Path(path)
        self.limit = limit
        self.records, self.redo = self._load()
        self._lock = threading.RLock()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [], []
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)], []
        if isinstance(data, dict):
            records = data.get("records")
            redo = data.get("redo")
            return (
                records if isinstance(records, list) else [],
                redo if isinstance(redo, list) else [],
            )
        return [], []

    def _save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            payload = {"records": self.records, "redo": self.redo}
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)

    def add(self, record: dict) -> dict:
        with self._lock:
            record = dict(record)
            record["id"] = uuid.uuid4().hex[:12]
            record["time"] = time.time()
            record["undone"] = False
            self.records.append(record)
            self.records = self.records[-self.limit:]
            self.redo = []
            self._save()
            return record

    def last(self):
        with self._lock:
            for record in reversed(self.records):
                if not record.get("undone"):
                    return record
            return None

    def mark_undo(self, record: dict) -> None:
        with self._lock:
            record["undone"] = True
            record_id = record.get("id")
            if record_id and record_id not in self.redo:
                self.redo.append(record_id)
            self._save()

    def last_redo(self):
        with self._lock:
            if not self.redo:
                return None
            record_id = self.redo[-1]
            for record in self.records:
                if record.get("id") == record_id:
                    return record
            return None

    def mark_redo(self, record: dict) -> None:
        with self._lock:
            record_id = record.get("id")
            if record_id in self.redo:
                self.redo.remove(record_id)
            record["undone"] = False
            self._save()
