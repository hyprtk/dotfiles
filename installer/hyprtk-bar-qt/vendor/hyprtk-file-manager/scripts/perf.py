#!/usr/bin/env python3
"""Performance regression: 10k-entry listing must stay within budget."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hyprtk_file_manager.listing import DirCache, list_dir  # noqa: E402

FIXTURE = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "hyprtk-fm-qa" / "10000"
COUNT = 10000
FIRST_BUDGET_MS = 300.0
CACHED_BUDGET_MS = 50.0


def make_fixture() -> None:
    if FIXTURE.is_dir():
        try:
            with os.scandir(FIXTURE) as entries:
                if sum(1 for _ in entries) == COUNT:
                    return
        except OSError:
            pass
        shutil.rmtree(FIXTURE, ignore_errors=True)
    FIXTURE.mkdir(parents=True, exist_ok=True)
    for index in range(COUNT):
        if index % 10 == 0:
            (FIXTURE / f"dir-{index:05d}").mkdir(exist_ok=True)
        else:
            (FIXTURE / f"file-{index:05d}.txt").touch()


def timed(call) -> float:
    best = None
    for _ in range(3):
        started = time.perf_counter()
        call()
        elapsed = (time.perf_counter() - started) * 1000.0
        best = elapsed if best is None else min(best, elapsed)
    return best


def main() -> int:
    make_fixture()
    cache = DirCache()
    started = time.perf_counter()
    list_dir(cache, str(FIXTURE), offset=0, limit=300)
    first = (time.perf_counter() - started) * 1000.0
    cached = timed(lambda: list_dir(cache, str(FIXTURE), offset=300, limit=300))
    print(f"10k first page:  {first:7.2f} ms (budget {FIRST_BUDGET_MS:.0f})")
    print(f"10k cached page: {cached:7.2f} ms (budget {CACHED_BUDGET_MS:.0f})")
    ok = first < FIRST_BUDGET_MS and cached < CACHED_BUDGET_MS
    print("PERF PASS" if ok else "PERF FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
