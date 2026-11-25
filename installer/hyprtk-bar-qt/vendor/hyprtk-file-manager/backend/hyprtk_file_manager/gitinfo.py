"""Git status and diffs for the current directory.

Read-only: nothing here stages, commits or writes. A directory outside a
repository returns an empty status, which is how the UI hides the badges.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

DIFF_LIMIT = 200_000


def _git(cwd: str | Path, args: list[str], timeout: float = 15) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                          text=True, timeout=timeout)


def repo_root(path: str | Path) -> str:
    target = Path(path).expanduser()
    if target.is_file():
        target = target.parent
    if not target.is_dir():
        return ""
    try:
        result = _git(target, ["rev-parse", "--show-toplevel"], timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def parse_porcelain(data: bytes) -> dict[str, str]:
    """Map absolute-path-suffix → one-letter status from ``status -z`` output."""
    out: dict[str, str] = {}
    parts = data.split(b"\0")
    index = 0
    while index < len(parts):
        raw = parts[index]
        index += 1
        if len(raw) < 4:
            continue
        code = raw[:2].decode("utf-8", "replace")
        name = raw[3:].decode("utf-8", "replace")
        if code.startswith("R") or code.startswith("C"):
            # a rename/copy carries the original path in the next field
            index += 1
        letter = code.strip()[:1] or "?"
        out[name] = letter
    return out


def status(path: str | Path) -> dict:
    root = repo_root(path)
    if not root:
        return {"root": "", "files": {}}
    try:
        result = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=normal"],
                      timeout=20)
    except (OSError, subprocess.SubprocessError):
        return {"root": root, "files": {}}
    if result.returncode != 0:
        return {"root": root, "files": {}}
    parsed = parse_porcelain(result.stdout.encode("utf-8"))
    files = {os.path.join(root, name): letter for name, letter in parsed.items()}
    return {"root": root, "files": files}


def diff(path: str | Path) -> dict:
    target = Path(path).expanduser()
    root = repo_root(target)
    if not root:
        return {"path": str(target), "root": "", "text": "", "note": "not in a git repository"}
    rel = os.path.relpath(str(target), root)
    try:
        result = _git(root, ["diff", "--no-color", "--no-ext-diff", "--", rel], timeout=30)
        if not result.stdout.strip():
            # an untracked file has no diff; show it as added content
            result = _git(root, ["diff", "--no-color", "--no-index", "--", "/dev/null", rel],
                          timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"path": str(target), "root": root, "text": "", "note": str(exc)}
    text = result.stdout or ""
    truncated = len(text) > DIFF_LIMIT
    return {"path": str(target), "root": root, "text": text[:DIFF_LIMIT],
            "truncated": truncated,
            "note": "" if text.strip() else "no textual changes"}
