"""Calculation history, appended to a JSONL file under the config dir.

One record per line keeps appends cheap and a truncated tail harmless: a crash
mid-write loses the last entry, never the file.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

from .settings import config_dir


def history_path() -> str:
    override = os.environ.get("HYPRTK_CALC_HISTORY")
    return override or os.path.join(config_dir(), "history.jsonl")


@dataclass
class Entry:
    expression: str
    result: str
    at: str

    def as_row(self) -> dict:
        return {"expression": self.expression, "result": self.result, "at": self.at}


class History:
    def __init__(self, path: str | None = None, limit: int = 500) -> None:
        self.path = path or history_path()
        self.limit = limit
        self._entries: list[Entry] = []
        self.load()

    # -- io
    def load(self) -> None:
        self._entries = []
        try:
            with open(self.path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    expression = record.get("expression")
                    result = record.get("result")
                    if isinstance(expression, str) and isinstance(result, str):
                        self._entries.append(
                            Entry(expression, result, str(record.get("at") or ""))
                        )
        except OSError:
            pass
        if len(self._entries) > self.limit:
            self._entries = self._entries[-self.limit:]

    def _append_line(self, entry: Entry) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.as_row(), sort_keys=True) + "\n")

    def _rewrite(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=directory or ".",
                                        prefix=".history.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for entry in self._entries:
                    handle.write(json.dumps(entry.as_row(), sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    # -- api
    def add(self, expression: str, result: str) -> Entry:
        entry = Entry(expression.strip(), result, datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if not entry.expression:
            return entry
        # The newest entry replaces an identical one, like a shell history that
        # ignores repeats: pressing Enter twice should not fill the list.
        if self._entries and self._entries[-1].expression == entry.expression:
            self._entries.pop()
            self._rewrite()
        self._entries.append(entry)
        self._append_line(entry)
        if len(self._entries) > self.limit:
            self._entries = self._entries[-self.limit:]
            self._rewrite()
        return entry

    def entries(self) -> list[Entry]:
        return list(self._entries)

    def newest_first(self, count: int | None = None) -> list[Entry]:
        rows = list(reversed(self._entries))
        return rows[:count] if count else rows

    def find(self, query: str, count: int = 50) -> list[Entry]:
        needle = query.strip().lower()
        if not needle:
            return self.newest_first(count)
        return [
            entry for entry in self.newest_first()
            if needle in entry.expression.lower() or needle in entry.result.lower()
        ][:count]

    def clear(self) -> None:
        self._entries = []
        try:
            os.remove(self.path)
        except OSError:
            pass

    def __len__(self) -> int:
        return len(self._entries)
