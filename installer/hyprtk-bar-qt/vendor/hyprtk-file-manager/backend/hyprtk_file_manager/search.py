"""Recursive name and content search (ripgrep when available)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .listing import icon_for


def _entry(path: str, line: str | None = None, lineno=None):
    target = Path(path)
    try:
        stat = target.stat(follow_symlinks=False)
    except OSError:
        return None
    name = target.name
    is_dir = target.is_dir()
    is_link = target.is_symlink()
    return {
        "path": str(target),
        "name": name,
        "dir": is_dir,
        "link": is_link,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mode": stat.st_mode,
        "icon": icon_for(name, is_dir, is_link, str(target), bool(stat.st_mode & 0o111)),
        "line": line,
        "lineno": lineno,
    }


def _walk_names(root: str, query: str, hidden: bool, limit: int) -> dict:
    lowered = query.lower()
    results = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if not hidden:
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        for name in list(dirnames) + filenames:
            if not hidden and name.startswith("."):
                continue
            if lowered not in name.lower():
                continue
            entry = _entry(os.path.join(dirpath, name))
            if entry:
                results.append(entry)
            if len(results) >= limit:
                truncated = True
                return {"results": results, "truncated": truncated}
    return {"results": results, "truncated": truncated}


def _rg_content(root: str, query: str, hidden: bool, no_ignore: bool, limit: int) -> dict:
    args = ["rg", "--json", "--max-count", "1", "--fixed-strings", "-i", "--no-messages"]
    if hidden:
        args.append("--hidden")
    if no_ignore:
        args.append("--no-ignore")
    args += ["--", query, root]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    results = []
    truncated = False
    try:
        for line in proc.stdout:
            if len(results) >= limit:
                truncated = True
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "match":
                continue
            data = event.get("data") or {}
            path = (data.get("path") or {}).get("text")
            if not path:
                continue
            lineno = data.get("line_number")
            text = ((data.get("lines") or {}).get("text") or "").rstrip("\n")
            entry = _entry(path, text, lineno)
            if entry:
                results.append(entry)
    finally:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass
        if proc.stdout:
            proc.stdout.close()
    return {"results": results, "truncated": truncated}


def search(root: str, query: str, mode: str = "name", hidden: bool = False,
           no_ignore: bool = False, limit: int = 500) -> dict:
    target = str(Path(root).expanduser())
    query = (query or "").strip()
    limit = max(1, min(int(limit), 2000))
    if not query:
        return {"kind": "search", "mode": mode, "query": query, "root": target,
                "results": [], "truncated": False}
    if mode == "content":
        if not shutil.which("rg"):
            raise RuntimeError("ripgrep (rg) is required for content search")
        found = _rg_content(target, query, hidden, no_ignore, limit)
    else:
        found = _walk_names(target, query, hidden, limit)
    return {
        "kind": "search",
        "mode": mode,
        "query": query,
        "root": target,
        "results": found["results"],
        "truncated": found["truncated"],
    }
