"""Wayland system-clipboard integration for file copy/cut/paste.

The file manager shares the session clipboard with the bar's cliphist history
and with other applications. A file selection is published as the GNOME
de-facto ``x-special/gnome-copied-files`` MIME type (a ``copy``/``cut`` header
line followed by ``file://`` URIs) so cliphist/bar-qt and desktop file managers
see the same clipboard. Pasting accepts that type, ``text/uri-list``, and the
plain-text form that cliphist hands back when a history entry is restored.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

FILE_MIME = "x-special/gnome-copied-files"
URI_MIME = "text/uri-list"
_TEXT_TYPES = {"text/plain", "text/plain;charset=utf-8", "UTF8_STRING", "STRING", "TEXT"}


def available() -> bool:
    return bool(shutil.which("wl-copy") and shutil.which("wl-paste"))


def selection_payload(paths, cut: bool = False) -> bytes:
    header = "cut" if cut else "copy"
    uris = [Path(str(path)).expanduser().as_uri() for path in paths]
    return (header + "\n" + "\n".join(uris) + "\n").encode("utf-8")


def parse_selection(text: str) -> dict:
    """Parse a URI-list style selection into ``{mode, paths}``.

    Accepts ``x-special/gnome-copied-files`` (``copy``/``cut`` first line),
    plain ``text/uri-list``, and the plain-text form cliphist stores (the
    header and URIs are preserved, so both look alike here).
    """
    mode = "copy"
    paths: list[str] = []
    first = True
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if first and line.lower() in ("copy", "cut"):
            mode = line.lower()
            first = False
            continue
        first = False
        if not line.lower().startswith("file://"):
            return {"mode": mode, "paths": []}
        parsed = urlparse(line)
        if parsed.netloc not in ("", "localhost"):
            return {"mode": mode, "paths": []}
        path = unquote(parsed.path)
        if path:
            paths.append(path)
    return {"mode": mode, "paths": paths}


def _run(args, timeout: float = 3.0):
    if not shutil.which(args[0]):
        return None
    try:
        return subprocess.run(args, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def _types() -> list[str]:
    proc = _run(["wl-paste", "--list-types"])
    if proc is None or proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.decode("utf-8", "replace").splitlines()
            if line.strip()]


def _read(mime: str | None = None) -> str:
    args = ["wl-paste", "--no-newline"]
    if mime:
        args += ["--type", mime]
    proc = _run(args)
    if proc is None or proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", "replace")


def get_files() -> dict:
    """Return the file selection currently on the shared clipboard."""
    types = _types()
    for mime in (FILE_MIME, URI_MIME):
        if mime in types:
            parsed = parse_selection(_read(mime))
            if parsed["paths"]:
                return parsed
    for mime in types:
        if mime in _TEXT_TYPES or mime.startswith("text/plain"):
            parsed = parse_selection(_read(mime))
            if parsed["paths"]:
                return parsed
    return {"mode": "copy", "paths": []}


def set_files(paths, cut: bool = False) -> bool:
    """Publish a file selection on the shared clipboard (copy or cut)."""
    items = [str(path) for path in paths if str(path)]
    if not items or not shutil.which("wl-copy"):
        return False
    try:
        proc = subprocess.Popen(
            ["wl-copy", "--type", FILE_MIME],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        proc.communicate(selection_payload(items, cut), timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def clear() -> bool:
    proc = _run(["wl-copy", "--clear"])
    return proc is not None and proc.returncode == 0
