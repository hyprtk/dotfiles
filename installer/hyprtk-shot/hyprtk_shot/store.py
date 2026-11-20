"""Where captures go: naming, saving, the clipboard and the history log.

The rule the rest of the suite follows: user files in an XDG directory the app
does not own, app state in ``$XDG_CONFIG_HOME/hyprtk-shot``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

FORMATS = ("png", "jpg", "webp")
EXTENSIONS = {"png": "png", "jpg": "jpg", "webp": "webp"}


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config"))


def config_dir() -> Path:
    override = os.environ.get("HYPRTK_SHOT_CONFIG_DIR")
    return Path(override) if override else _config_home() / "hyprtk-shot"


def pictures_dir() -> Path:
    """The user's pictures directory, resolved the XDG way when possible."""
    override = os.environ.get("HYPRTK_SHOT_DIR")
    if override:
        return Path(os.path.expanduser(override))
    if shutil.which("xdg-user-dir"):
        try:
            result = subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True,
                                    text=True, timeout=5, check=False)
            value = (result.stdout or "").strip()
            if value and value != os.path.expanduser("~"):
                return Path(value)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return Path(os.path.expanduser("~")) / "Pictures"


def default_dir() -> Path:
    return pictures_dir() / "Screenshots"


def make_name(mode: str, *, ts: datetime | None = None, ext: str = "png") -> str:
    stamp = (ts or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    safe = "".join(ch for ch in (mode or "capture") if ch.isalnum() or ch in "-_") or "capture"
    return f"hyprtk-{stamp}-{safe}.{EXTENSIONS.get(ext, ext)}"


def unique_path(path: Path) -> Path:
    """Never overwrite a capture; append ``-2``, ``-3`` … instead."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"too many captures named {path.name}")


def write_bytes(path: Path, data: bytes) -> Path:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def save_image(image, path: Path, *, fmt: str | None = None, quality: int = 92) -> Path:
    """Save a QImage; returns the path actually written."""
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    kind = (fmt or path.suffix.lstrip(".") or "png").lower()
    if kind == "jpeg":
        kind = "jpg"
    if kind not in FORMATS:
        kind = "png"
    if str(path.suffix).lstrip(".").lower() not in EXTENSIONS and kind in EXTENSIONS:
        path = path.with_suffix("." + EXTENSIONS[kind])
    ok = image.save(str(path), kind.upper(), max(1, min(100, int(quality))))
    if not ok:
        raise OSError(f"could not write {path}")
    return path


def png_bytes(image) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise OSError("could not encode the capture as PNG")
    buffer.close()
    return bytes(data)


# ------------------------------------------------------------- clipboard ---

def copy_to_clipboard(data: bytes, *, mime: str = "image/png") -> bool:
    """Put bytes on the Wayland clipboard with wl-copy (X11 fallback: xclip)."""
    if shutil.which("wl-copy"):
        try:
            result = subprocess.run(["wl-copy", "--type", mime], input=data,
                                    timeout=8, check=False,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    if shutil.which("xclip"):
        try:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-t", mime, "-i"],
                                    input=data, timeout=8, check=False,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    return False


def copy_text(text: str) -> bool:
    return copy_to_clipboard(text.encode("utf-8"), mime="text/plain;charset=utf-8")


# --------------------------------------------------------------- history ---

class History:
    """Append-only JSONL of captures, newest last on disk, newest first to the UI."""

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
        keep = lines[-self.limit:]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text("\n".join(keep) + "\n", encoding="utf-8")
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
        rows = []
        for row in self.entries(count):
            path = Path(str(row.get("path") or "")).expanduser()
            if path.is_file():
                rows.append(row)
        return rows

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def human_size(count: int | float) -> str:
    value = float(count or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"
