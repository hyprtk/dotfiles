"""Compare folders, find duplicate files, measure directory usage."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duplicates(root: str | Path, min_size: int = 1, max_groups: int = 50) -> dict:
    """Groups of byte-identical files under *root* (size first, then hash)."""
    base = Path(root).expanduser()
    if not base.is_dir():
        raise RuntimeError(f"{base} is not a directory")
    by_size: dict[int, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith(".git"))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            if size < max(1, int(min_size)):
                continue
            by_size.setdefault(size, []).append(path)

    groups: list[dict] = []
    hashed: dict[str, list[str]] = {}
    for size, paths in sorted(by_size.items(), reverse=True):
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                digest = _hash(path)
            except OSError:
                continue
            hashed.setdefault(digest, []).append(str(path))
    for digest, paths in sorted(hashed.items(), key=lambda item: -len(item[1])):
        if len(paths) < 2:
            continue
        groups.append({"hash": digest, "size": os.path.getsize(paths[0]),
                       "paths": sorted(paths)})
        if len(groups) >= max_groups:
            break
    wasted = sum(group["size"] * (len(group["paths"]) - 1) for group in groups)
    return {"groups": groups, "wasted": wasted}


def directory_size(path: str | Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(path, onerror=lambda _error: None):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).lstat().st_size
            except OSError:
                continue
    return total


def usage(root: str | Path, limit: int = 40) -> dict:
    """Size of every immediate child of *root*, largest first."""
    base = Path(root).expanduser()
    if not base.is_dir():
        raise RuntimeError(f"{base} is not a directory")
    items: list[dict] = []
    for child in sorted(base.iterdir()):
        try:
            if child.is_symlink():
                size = child.lstat().st_size
            elif child.is_dir():
                size = directory_size(child)
            else:
                size = child.stat().st_size
        except OSError:
            continue
        items.append({"name": child.name, "path": str(child),
                      "size": size, "dir": child.is_dir()})
    items.sort(key=lambda item: -item["size"])
    total = sum(item["size"] for item in items) or 1
    for item in items:
        item["ratio"] = item["size"] / total
    return {"total": total, "items": items[:limit]}


def _walk(root: Path) -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _error: None):
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        rel = os.path.relpath(dirpath, root)
        for name in filenames:
            path = Path(dirpath) / name
            key = os.path.normpath(os.path.join(rel, name)) if rel != "." else name
            try:
                out[key] = (path.stat().st_size, _hash(path))
            except OSError:
                continue
    return out


def compare(left: str | Path, right: str | Path) -> dict:
    """Recursive name/size comparison of two directory trees."""
    a, b = Path(left).expanduser(), Path(right).expanduser()
    if not a.is_dir() or not b.is_dir():
        raise RuntimeError("compare needs two directories")
    files_a, files_b = _walk(a), _walk(b)
    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))
    differing = sorted(name for name in set(files_a) & set(files_b)
                       if files_a[name] != files_b[name])
    same = len(set(files_a) & set(files_b)) - len(differing)
    return {"left": str(a), "right": str(b),
            "only_left": only_a[:500], "only_right": only_b[:500],
            "differing": differing[:500], "same": same,
            "counts": {"only_left": len(only_a), "only_right": len(only_b),
                       "differing": len(differing), "same": same}}
