"""Scrollback search: pattern building, matching and column mapping.

Pure list work over a VT-like object (``line_text``, ``line_cells``,
``scrollback_len``, ``rows``), so the whole thing is testable without a display
and without libvterm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A terminal history can be huge; stop early rather than freeze the UI.
MAX_MATCHES = 2000


@dataclass(frozen=True, slots=True)
class Match:
    line: int        # absolute line (scrollback + screen)
    start: int       # first column
    end: int         # one past the last column


def build_pattern(query: str, case_sensitive: bool = False, regex: bool = False):
    """Compiled pattern, or None for an empty query / invalid regex."""
    if not query:
        return None
    flags = 0 if case_sensitive else re.IGNORECASE
    if regex:
        try:
            return re.compile(query, flags)
        except re.error:
            return None
    return re.compile(re.escape(query), flags)


def flatten(cells: list[str]) -> tuple[str, list[int]]:
    """Text plus a character-index to column map.

    ``line_cells`` marks the right half of a wide glyph with ``""``; dropping
    those keeps the columns right without shifting the text.
    """
    chars: list[str] = []
    cols: list[int] = []
    for col, ch in enumerate(cells):
        if not ch:
            continue
        chars.append(ch)
        cols.append(col)
    return "".join(chars), cols


def find_matches(vt, query: str, case_sensitive: bool = False,
                 regex: bool = False, limit: int = MAX_MATCHES) -> list[Match]:
    """Every match in history + screen, oldest first."""
    pattern = build_pattern(query, case_sensitive, regex)
    if pattern is None:
        return []

    hits: list[tuple[int, int, int]] = []
    total = vt.scrollback_len + vt.rows
    for line in range(total):
        text = vt.line_text(line)
        if not text:
            continue
        for found in pattern.finditer(text):
            if found.start() == found.end():
                continue                       # zero-width regex
            hits.append((line, found.start(), found.end()))
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break

    out: list[Match] = []
    maps: dict[int, list[int]] = {}
    for line, start, end in hits:
        cols = maps.get(line)
        if cols is None:
            _text, cols = flatten(vt.line_cells(line))
            maps[line] = cols
        if not cols:
            continue
        first = cols[start] if start < len(cols) else cols[-1] + 1
        last = cols[end - 1] + 1 if 0 < end <= len(cols) else cols[-1] + 1
        out.append(Match(line, first, max(first + 1, last)))
    return out


def line_of_next(matches: list[Match], current: int, direction: int = 1) -> int:
    """Index of the next match, wrapping around the list."""
    if not matches:
        return -1
    return (current + direction) % len(matches)


def scroll_for_line(line: int, scrollback_len: int, rows: int) -> int:
    """Scrollback offset that puts ``line`` about a third down the view."""
    target_top = line - max(0, rows // 3)
    return max(0, min(scrollback_len, scrollback_len - target_top))
