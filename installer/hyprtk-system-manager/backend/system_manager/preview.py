"""Dry-run capture for ``apply()``.

A panel writes through :func:`system_manager.util.atomic_write` (user files) or
:func:`system_manager.systemfiles.write` (root files). With a capture active both
record the intended content and return without touching the disk, so the front
end can show exactly what an Apply would change.

What a preview does *not* do: undo external commands a panel runs while applying
(a Hyprland reload, ``powerprofilesctl set``). Panels that only act on the system
declare ``PREVIEW = ""`` and are refused instead of pretending.
"""

from __future__ import annotations

import difflib
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_STATE = threading.local()


def active() -> bool:
    return bool(getattr(_STATE, "active", False))


def entries() -> list[dict]:
    return list(getattr(_STATE, "entries", ()))


def unified(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile=f"a{path}", tofile=f"b{path}",
    ))


def record(path: str | Path, before: str, after: str) -> None:
    if not active():
        return
    if before == after:
        return
    _STATE.entries.append({
        "path": str(path),
        "before": before,
        "after": after,
        "diff": unified(str(path), before, after),
    })


@contextmanager
def capture() -> Iterator[list[dict]]:
    """Collect would-be writes instead of performing them."""
    previous = active()
    previous_entries = entries()
    _STATE.active = True
    _STATE.entries = []
    try:
        yield _STATE.entries
    finally:
        _STATE.active = previous
        _STATE.entries = previous_entries


def read_before(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
