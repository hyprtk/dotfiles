"""Directory listing with per-directory name and sort caches."""

from __future__ import annotations

import functools
import mimetypes
import os
from pathlib import Path

ICON_FALLBACK = "text-x-generic"
MIME_ICONS = {
    "application/pdf": "application-pdf",
    "application/zip": "package-x-generic",
    "application/x-tar": "package-x-generic",
    "application/x-7z-compressed": "package-x-generic",
    "application/vnd.rar": "package-x-generic",
    "application/gzip": "package-x-generic",
    "application/x-bzip2": "package-x-generic",
    "application/x-xz": "package-x-generic",
}
MAJOR_ICONS = {
    "image": "image-x-generic",
    "video": "video-x-generic",
    "audio": "audio-x-generic",
    "text": "text-x-generic",
}


def icon_for(name: str, is_dir: bool, is_link: bool) -> str:
    if is_dir:
        return "folder"
    if is_link:
        return "emblem-symbolic-link"
    mime, _encoding = mimetypes.guess_type(name)
    if mime in MIME_ICONS:
        return MIME_ICONS[mime]
    return MAJOR_ICONS.get((mime or "").split("/")[0], ICON_FALLBACK)


def _raw_scan(path: Path):
    rows = []
    with os.scandir(path) as it:
        for entry in it:
            try:
                rows.append((entry.name, entry.is_dir(follow_symlinks=False), entry.is_symlink()))
            except OSError:
                rows.append((entry.name, False, False))
    return rows


class DirCache:
    def __init__(self, limit: int = 64):
        self.limit = limit
        self._names: dict[str, tuple[int | None, list]] = {}
        self._sorted: dict[tuple, list] = {}

    def _evict(self, store: dict) -> None:
        while len(store) > self.limit:
            store.pop(next(iter(store)))

    def names(self, path: Path):
        key = str(path)
        try:
            mtime = os.stat(path).st_mtime_ns
        except OSError:
            mtime = None
        hit = self._names.get(key)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        rows = _raw_scan(path)
        self._names[key] = (mtime, rows)
        self._evict(self._names)
        return rows

    def sorted_names(self, path: Path, sort: str, desc: bool, hidden: bool, dirs_first: bool):
        rows = self.names(path)
        mtime = self._names[str(path)][0]
        cache_key = (str(path), mtime, sort, bool(desc), bool(hidden), bool(dirs_first))
        hit = self._sorted.get(cache_key)
        if hit is not None:
            return hit

        rows = [row for row in rows if hidden or not row[0].startswith(".")]
        stats: dict[str, tuple[int, float]] = {}
        if sort in ("size", "mtime"):
            for name, _is_dir, _is_link in rows:
                try:
                    stat = os.stat(os.path.join(path, name), follow_symlinks=False)
                    stats[name] = (stat.st_size, stat.st_mtime)
                except OSError:
                    stats[name] = (0, 0.0)

        def primary(row):
            name, _is_dir, _is_link = row
            if sort == "size":
                return stats[name][0]
            if sort == "mtime":
                return stats[name][1]
            if sort == "type":
                return os.path.splitext(name)[1].lower()
            return name.lower()

        def compare(a, b):
            if dirs_first and a[1] != b[1]:
                return -1 if a[1] else 1
            pa, pb = primary(a), primary(b)
            if pa < pb:
                result = -1
            elif pa > pb:
                result = 1
            else:
                na, nb = a[0].lower(), b[0].lower()
                result = -1 if na < nb else (1 if na > nb else 0)
            return -result if desc else result

        rows.sort(key=functools.cmp_to_key(compare))
        self._sorted[cache_key] = rows
        self._evict(self._sorted)
        return rows


def list_dir(
    cache: DirCache,
    path: str,
    offset: int = 0,
    limit: int = 250,
    sort: str = "name",
    desc: bool = False,
    hidden: bool = False,
    dirs_first: bool = True,
    query: str = "",
) -> dict:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(str(target))
    if not target.is_dir():
        raise NotADirectoryError(str(target))

    rows = cache.sorted_names(target, sort, desc, hidden, dirs_first)
    if query:
        lowered = str(query).lower()
        rows = [row for row in rows if lowered in row[0].lower()]
    total = len(rows)
    offset = max(0, int(offset))
    limit = max(1, int(limit))
    window = rows[offset:offset + limit]

    entries = []
    for name, is_dir, is_link in window:
        try:
            stat = os.stat(os.path.join(target, name), follow_symlinks=False)
            size, mtime, mode = stat.st_size, stat.st_mtime, stat.st_mode
        except OSError:
            size, mtime, mode = 0, 0.0, 0
        entries.append(
            {
                "name": name,
                "dir": is_dir,
                "link": is_link,
                "size": size,
                "mtime": mtime,
                "mode": mode,
                "icon": icon_for(name, is_dir, is_link),
            }
        )

    return {"path": str(target), "total": total, "offset": offset, "entries": entries}
