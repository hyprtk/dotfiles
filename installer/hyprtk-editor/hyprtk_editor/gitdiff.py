"""Working-tree diff status for the editor's gutter.

One ``git diff --unified=0`` per file, parsed into new-side line numbers and
cached by (mtime, size). The gutter only needs to know *which* lines changed
and how, so hunk parsing is enough — no porcelain parsing, no libgit2, no
per-keystroke subprocess.

Everything degrades quietly: outside a repository, without git installed, or
when the call times out, ``Status.ok`` is false and the gutter shows nothing.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field

# @@ -12,3 +12,4 @@  — the counts are omitted when they are 1.
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

MAX_UNTRACKED_LINES = 20_000
TIMEOUT = 2.0
# Total wall time one status() may spend in git subprocesses.
BUDGET_S = 1.2


@dataclass(frozen=True)
class Status:
    ok: bool = False
    repo: str = ""
    kind: str = "none"            # none | tracked | untracked | error
    lines: dict = field(default_factory=dict)   # {"12": "add"} — string keys for QML
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "repo": self.repo,
            "kind": self.kind,
            "lines": self.lines,
            "error": self.error,
        }


def parse_diff(text: str) -> dict[str, str]:
    """Map new-side line numbers to ``add`` / ``mod`` / ``del``.

    A hunk with no old lines is a pure insertion, one with no new lines is a
    pure deletion, and anything else replaces lines in place.
    """
    out: dict[str, str] = {}
    for raw in (text or "").splitlines():
        match = HUNK.match(raw)
        if match is None:
            continue
        old_count = int(match.group(2)) if match.group(2) is not None else 1
        start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) is not None else 1
        if old_count == 0:
            kind = "add"
        elif new_count == 0:
            kind = "del"
        else:
            kind = "mod"
        if new_count == 0:
            # The deletion sits at (or just before) the new-side line git names.
            out[str(max(1, start))] = "del"
            continue
        for number in range(max(1, start), start + new_count):
            out.setdefault(str(number), kind)
    return out


_DEADLINE = [0.0]


def _run(args: list[str], cwd: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "LC_ALL": "C"})
    budget = TIMEOUT
    if _DEADLINE[0]:
        budget = max(0.1, min(TIMEOUT, _DEADLINE[0] - time.monotonic()))
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=budget,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return done.returncode, done.stdout, done.stderr


def _line_count(path: str) -> int:
    try:
        with open(path, "rb") as handle:
            data = handle.read(4 * 1024 * 1024)
    except OSError:
        return 0
    count = data.count(b"\n")
    if data and not data.endswith(b"\n"):
        count += 1
    return min(count, MAX_UNTRACKED_LINES)


class GitDiff:
    """Per-path diff status with a mtime-keyed cache.

    ``status()`` is budgeted: one file's diff is capped at ``BUDGET_S`` total,
    so the save/load/settings paths cannot stack three two-second timeouts into
    a multi-second freeze on the GUI thread.
    """

    def __init__(self, on_change=None) -> None:
        self._roots: dict[str, str] = {}
        self._cache: dict[str, tuple[tuple[int, int], Status]] = {}
        self._deadline = 0.0
        self._on_change = on_change

    def cached(self, path: str):
        """Last computed status for *path*, or None. Never runs git."""
        entry = self._cache.get(os.path.abspath(str(path or "")))
        return entry[1] if entry else None

    def invalidate(self, path: str = "") -> None:
        if path:
            self._cache.pop(os.path.abspath(path), None)
        else:
            self._cache.clear()

    def status(self, path: str) -> Status:
        """Diff status for a file, with a per-path refresh budget."""
        path = os.path.abspath(str(path or ""))
        if not path or not os.path.isfile(path):
            return Status(ok=False)
        try:
            info = os.stat(path)
        except OSError:
            return Status(ok=False)
        key = (info.st_mtime_ns, info.st_size)
        cached = self._cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]
        _DEADLINE[0] = time.monotonic() + BUDGET_S
        try:
            result = self._compute(path)
        finally:
            _DEADLINE[0] = 0.0
        self._cache[path] = (key, result)
        return result

    # -- internals -------------------------------------------------------
    def _root(self, directory: str) -> str:
        if directory in self._roots:
            return self._roots[directory]
        code, out, _ = _run(["rev-parse", "--show-toplevel"], directory)
        root = out.strip() if code == 0 else ""
        self._roots[directory] = root
        return root

    def _compute(self, path: str) -> Status:
        root = self._root(os.path.dirname(path))
        if not root:
            return Status(ok=False, kind="none")
        rel = os.path.relpath(path, root)

        tracked = _run(["ls-files", "--error-unmatch", "--", rel], root)[0] == 0
        if not tracked:
            count = _line_count(path)
            lines = {str(number): "add" for number in range(1, count + 1)}
            return Status(ok=True, repo=root, kind="untracked", lines=lines)

        code, out, err = _run(
            ["diff", "HEAD", "--unified=0", "--no-color", "--no-ext-diff", "--", rel], root
        )
        if code not in (0, 1):
            # A repository with no commits yet has no HEAD to diff against.
            code, out, err = _run(
                ["diff", "--unified=0", "--no-color", "--no-ext-diff", "--", rel], root
            )
            if code not in (0, 1):
                return Status(ok=False, repo=root, kind="error", error=err.strip()[:200])
        return Status(ok=True, repo=root, kind="tracked", lines=parse_diff(out))
