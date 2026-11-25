"""Archive support: inspect, extract and create zip/tar archives.

Extraction is the risky half, so every member name is checked before anything
is written: absolute paths, ``..`` segments and symlink targets that escape the
destination are refused. 7z archives are handled through the ``7z`` binary when
it is installed; zip and tar are handled in-process with the standard library.
"""

from __future__ import annotations

import os
import shutil
import tarfile
import time
import zipfile
from pathlib import Path, PurePosixPath

ARCHIVE_SUFFIXES = {
    ".zip": "zip",
    ".tar": "tar",
    ".tar.gz": "tar.gz",
    ".tgz": "tar.gz",
    ".tar.xz": "tar.xz",
    ".txz": "tar.xz",
    ".tar.bz2": "tar.bz2",
    ".tbz2": "tar.bz2",
    ".7z": "7z",
}

CREATE_FORMATS = [
    {"value": "zip", "label": "Zip (.zip)"},
    {"value": "tar.gz", "label": "Tar, gzip (.tar.gz)"},
    {"value": "tar.xz", "label": "Tar, xz (.tar.xz)"},
]


def kind_of(path: str | Path) -> str:
    """Archive kind from the file name (empty when it is not an archive)."""
    name = str(path).lower()
    for suffix in sorted(ARCHIVE_SUFFIXES, key=len, reverse=True):
        if name.endswith(suffix):
            return ARCHIVE_SUFFIXES[suffix]
    return ""


def safe_member(name: str) -> bool:
    """A member may not be absolute, climb out, or carry a drive/UNC prefix."""
    if not name or name.startswith(("/", "\\")) or ":" in name.split("/")[0]:
        return False
    parts = PurePosixPath(name.replace("\\", "/")).parts
    return ".." not in parts


def _seven_zip() -> str:
    return shutil.which("7z") or shutil.which("7zz") or shutil.which("7za") or ""


def list_archive(path: str | Path, inner: str = "") -> dict:
    """Entries of an archive (optionally one directory inside it)."""
    target = Path(path).expanduser()
    if not target.is_file():
        raise RuntimeError(f"{target} is not a file")
    kind = kind_of(target)
    if not kind:
        raise RuntimeError("not an archive this file manager can read")
    prefix = inner.strip("/")

    if kind == "7z":
        binary = _seven_zip()
        if not binary:
            raise RuntimeError("7z is not installed")
        return _list_7z(binary, target, prefix)
    if kind == "zip":
        return _list_zip(target, prefix)
    return _list_tar(target, prefix)


def _entry(name: str, size: int, modified: str, is_dir: bool) -> dict:
    base = PurePosixPath(name).name or name
    return {"name": base, "path": name, "size": int(size or 0),
            "modified": modified or "", "dir": bool(is_dir)}


def _child_entries(names: list[tuple[str, int, str, bool]], prefix: str) -> list[dict]:
    """Collapse member names into the immediate children of *prefix*."""
    seen: dict[str, dict] = {}
    head = prefix.strip("/")
    for name, size, modified, is_dir in names:
        clean = name.rstrip("/")
        if head:
            if not clean.startswith(head + "/"):
                continue
            clean = clean[len(head) + 1:]
        if not clean:
            continue
        first, _, rest = clean.partition("/")
        entry = seen.get(first)
        if entry is None:
            seen[first] = _entry(
                f"{head}/{first}" if head else first,
                size if not rest else 0, modified, bool(rest) or is_dir)
        elif not rest:
            entry["dir"] = entry["dir"] or is_dir
            entry["size"] = size
    return sorted(seen.values(), key=lambda item: (not item["dir"], item["name"].lower()))


def _list_zip(path: Path, prefix: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = [(info.filename, info.file_size,
                  "%04d-%02d-%02d %02d:%02d" % info.date_time[:5], info.is_dir())
                 for info in archive.infolist()]
    return {"path": str(path), "inner": prefix, "kind": "zip",
            "entries": _child_entries(names, prefix)}


def _list_tar(path: Path, prefix: str) -> dict:
    names = []
    with tarfile.open(path) as archive:
        for info in archive.getmembers():
            names.append((info.name, info.size,
                          time.strftime("%Y-%m-%d %H:%M", time.localtime(info.mtime or 0)),
                          info.isdir()))
    return {"path": str(path), "inner": prefix, "kind": "tar",
            "entries": _child_entries(names, prefix)}


def parse_7z_listing(text: str) -> list[tuple[str, int, str, bool]]:
    """Parse ``7z l -slt`` output (blank-line separated records)."""
    rows: list[tuple[str, int, str, bool]] = []
    current: dict[str, str] = {}
    for line in text.splitlines() + [""]:
        if not line.strip():
            if current.get("Path"):
                rows.append((current["Path"], int(current.get("Size") or 0),
                             current.get("Modified") or "", current.get("Folder") == "+"))
            current = {}
            continue
        key, _, value = line.partition(" = ")
        if key:
            current[key.strip()] = value.strip()
    return rows


def _list_7z(binary: str, path: Path, prefix: str) -> dict:
    import subprocess

    result = subprocess.run([binary, "l", "-slt", str(path)], capture_output=True,
                            text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "7z failed")
    rows = [row for row in parse_7z_listing(result.stdout)
            if row[0] not in ("", str(path))]
    return {"path": str(path), "inner": prefix, "kind": "7z",
            "entries": _child_entries(rows, prefix)}


def _destination(target: Path) -> Path:
    return target.parent


def _guard(destination: Path, member: str) -> Path:
    if not safe_member(member):
        raise RuntimeError(f"refusing unsafe archive member {member!r}")
    out = (destination / member).resolve()
    base = destination.resolve()
    if out != base and base not in out.parents:
        raise RuntimeError(f"refusing archive member outside the destination: {member!r}")
    return out


def extract(path: str | Path, inner: str = "", destination: str | Path | None = None) -> dict:
    """Extract one member (or the whole archive) into *destination*."""
    target = Path(path).expanduser()
    kind = kind_of(target)
    if not kind:
        raise RuntimeError("not an archive")
    dest = Path(destination).expanduser() if destination else _destination(target)
    dest.mkdir(parents=True, exist_ok=True)
    member = (inner or "").strip("/")
    extracted: list[str] = []

    if kind == "zip":
        with zipfile.ZipFile(target) as archive:
            for info in archive.infolist():
                if member and not (info.filename == member or
                                   info.filename.startswith(member + "/")):
                    continue
                out = _guard(dest, info.filename)
                if info.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, open(out, "wb") as handle:
                    shutil.copyfileobj(source, handle)
                extracted.append(str(out))
    elif kind == "7z":
        binary = _seven_zip()
        if not binary:
            raise RuntimeError("7z is not installed")
        import subprocess

        args = [binary, "x", "-y", f"-o{dest}", str(target)]
        if member:
            args.append(member)
        result = subprocess.run(args, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip() or "7z failed")
        extracted.append(str(dest / member if member else dest))
    else:
        with tarfile.open(target) as archive:
            for info in archive.getmembers():
                if member and not (info.name == member or info.name.startswith(member + "/")):
                    continue
                out = _guard(dest, info.name)
                if info.isdir():
                    out.mkdir(parents=True, exist_ok=True)
                elif info.issym() or info.islnk():
                    raise RuntimeError(f"refusing link member {info.name!r}")
                elif info.isfile():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(info)
                    if source is None:
                        continue
                    with source, open(out, "wb") as handle:
                        shutil.copyfileobj(source, handle)
                extracted.append(str(out))
    return {"extracted": extracted, "destination": str(dest)}


def _suffix(fmt: str) -> str:
    return {"zip": ".zip", "tar.gz": ".tar.gz", "tar.xz": ".tar.xz"}.get(fmt, ".zip")


def create(paths: list[str], destination: str | Path, fmt: str = "zip") -> dict:
    """Create an archive holding *paths* (files or directories) under *destination*."""
    if fmt not in ("zip", "tar.gz", "tar.xz"):
        raise RuntimeError(f"unsupported archive format {fmt!r}")
    if not paths:
        raise RuntimeError("nothing to archive")
    dest = Path(destination).expanduser()
    if dest.is_dir():
        name = Path(paths[0]).stem or "archive"
        dest = dest / (name + _suffix(fmt))
    dest.parent.mkdir(parents=True, exist_ok=True)

    mode = "w" if fmt == "zip" else {"tar.gz": "w:gz", "tar.xz": "w:xz"}[fmt]
    if fmt == "zip":
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in paths:
                source = Path(item).expanduser()
                if source.is_dir():
                    for root, dirs, files in os.walk(source):
                        dirs.sort()
                        rel = Path(root).relative_to(source.parent)
                        archive.write(root, str(rel))
                        for name in sorted(files):
                            path = Path(root) / name
                            archive.write(path, str(path.relative_to(source.parent)))
                elif source.is_file():
                    archive.write(source, source.name)
    else:
        with tarfile.open(dest, mode) as archive:
            for item in paths:
                source = Path(item).expanduser()
                archive.add(source, arcname=source.name)
    return {"path": str(dest), "format": fmt, "count": len(paths)}
