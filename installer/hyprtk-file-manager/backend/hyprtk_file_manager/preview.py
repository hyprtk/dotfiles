"""Preview and thumbnail generation."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import subprocess
from pathlib import Path

CACHE_ROOT = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "hyprtk-file-manager" / "thumbs"
TEXT_LIMIT = 64 * 1024


def _cache_key(path: str, mtime_ns: int, size: int) -> str:
    raw = f"{path}:{mtime_ns}:{size}".encode("utf-8", "replace")
    return hashlib.sha1(raw).hexdigest()


def _run(command, timeout=15):
    try:
        return subprocess.run(command, capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None


def _mime(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    if guessed:
        return guessed
    proc = _run(["file", "-b", "--mime-type", path], timeout=5)
    if proc and proc.returncode == 0:
        return proc.stdout.decode("utf-8", "replace").strip() or "application/octet-stream"
    return "application/octet-stream"


def _looks_text(path: str) -> bool:
    try:
        chunk = Path(path).read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in chunk


def _thumb(key: str, extension: str) -> Path:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return CACHE_ROOT / f"{key}.{extension}"


def build_preview(path: str) -> dict:
    target = Path(path).expanduser()
    stat = target.stat(follow_symlinks=False)
    mime = _mime(str(target))
    meta = {
        "path": str(target),
        "name": target.name,
        "mime": mime,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mode": stat.st_mode,
    }
    if target.is_symlink():
        meta["target"] = os.readlink(target)
    if target.is_dir():
        return {"kind": "dir", "meta": meta}

    major = mime.split("/")[0]
    key = _cache_key(str(target), stat.st_mtime_ns, stat.st_size)

    if major == "image":
        out = _thumb(key, "jpg")
        if not out.exists():
            _run(["vipsthumbnail", str(target), "-s", "512", "-o", str(out)])
        if out.exists():
            return {"kind": "image", "thumb": str(out), "meta": meta}
    elif major == "video":
        out = _thumb(key, "jpg")
        if not out.exists():
            _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0", "-i", str(target),
                  "-frames:v", "1", "-vf", "scale=512:-1", str(out)])
        if out.exists():
            return {"kind": "video", "thumb": str(out), "meta": meta}
    elif mime == "application/pdf":
        prefix = CACHE_ROOT / key
        out = prefix.with_suffix(".png")
        if not out.exists():
            _run(["pdftoppm", "-f", "1", "-singlefile", "-scale-to", "512",
                  "-png", str(target), str(prefix)])
        if out.exists():
            return {"kind": "pdf", "thumb": str(out), "meta": meta}

    if major == "text" or _looks_text(str(target)):
        try:
            data = target.read_bytes()[:TEXT_LIMIT]
        except OSError:
            data = b""
        return {
            "kind": "text",
            "text": data.decode("utf-8", "replace"),
            "truncated": stat.st_size > TEXT_LIMIT,
            "meta": meta,
        }

    return {"kind": "binary", "meta": meta}
