"""Where recordings go and how long they are.

Same split as the rest of the suite: finished files in an XDG directory the app
does not own, the app's own log in ``$XDG_CONFIG_HOME/hyprtk-rec``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

CONTAINERS = ("mp4", "mkv", "webm")


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config"))


def config_dir() -> Path:
    override = os.environ.get("HYPRTK_REC_CONFIG_DIR")
    return Path(override) if override else _config_home() / "hyprtk-rec"


def videos_dir() -> Path:
    override = os.environ.get("HYPRTK_REC_DIR")
    if override:
        return Path(os.path.expanduser(override))
    if shutil.which("xdg-user-dir"):
        try:
            result = subprocess.run(["xdg-user-dir", "VIDEOS"], capture_output=True,
                                    text=True, timeout=5, check=False)
            value = (result.stdout or "").strip()
            if value and value != os.path.expanduser("~"):
                return Path(value)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return Path(os.path.expanduser("~")) / "Videos"


def default_dir() -> Path:
    return videos_dir() / "Recordings"


def make_name(source: str, *, ts: datetime | None = None, ext: str = "mp4") -> str:
    stamp = (ts or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    safe = "".join(ch for ch in (source or "capture") if ch.isalnum() or ch in "-_") or "capture"
    ext = ext.lstrip(".") or "mp4"
    if ext not in CONTAINERS:
        ext = "mp4"
    return f"hyprtk-{stamp}-{safe}.{ext}"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"too many recordings named {path.name}")


def human_duration(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0))))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_size(count: int | float) -> str:
    value = float(count or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


class History:
    """Append-only JSONL of finished recordings."""

    def __init__(self, path: str | os.PathLike | None = None, *, limit: int = 200) -> None:
        self.path = Path(path) if path else config_dir() / "history.jsonl"
        self.limit = max(1, int(limit))

    def add(self, entry: dict) -> dict:
        entry = dict(entry)
        entry.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        self._trim()
        return entry

    def _trim(self) -> None:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if len(lines) <= self.limit:
            return
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text("\n".join(lines[-self.limit:]) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def entries(self, count: int = 60) -> list[dict]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        rows = []
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
            if len(rows) >= count:
                break
        return rows

    def recent_paths(self, count: int = 60) -> list[dict]:
        return [row for row in self.entries(count)
                if Path(str(row.get("path") or "")).expanduser().is_file()]

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
