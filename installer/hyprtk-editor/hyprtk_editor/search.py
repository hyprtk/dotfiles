"""Incremental, regex and replace-all search over a document.

Pure functions over ``str`` so they are testable without Qt. Match positions
are absolute character offsets; the QML editor and the highlighter both work in
those terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_MATCHES = 20_000


@dataclass(frozen=True)
class Query:
    text: str = ""
    case: bool = False
    word: bool = False
    regex: bool = False
    multiline: bool = False

    @property
    def empty(self) -> bool:
        return self.text == ""

    def pattern(self) -> re.Pattern | None:
        if not self.text:
            return None
        flags = re.MULTILINE
        if self.multiline:
            flags |= re.DOTALL
        if not self.case:
            flags |= re.IGNORECASE
        body = self.text if self.regex else re.escape(self.text)
        if self.word:
            body = rf"\b(?:{body})\b"
        try:
            return re.compile(body, flags)
        except re.error:
            return None


def find_all(text: str, query: Query, limit: int = MAX_MATCHES) -> list[dict]:
    pattern = query.pattern()
    if pattern is None:
        return []
    out: list[dict] = []
    for match in pattern.finditer(text):
        start, end = match.span()
        if end == start:
            # Zero-width regex: advance one char so search still makes progress.
            out.append({"start": start, "length": 0})
            if len(out) >= limit:
                break
            continue
        out.append({"start": start, "length": end - start})
        if len(out) >= limit:
            break
    return out


def count(text: str, query: Query, limit: int = MAX_MATCHES) -> int:
    return len(find_all(text, query, limit))


def find_next(text: str, query: Query, position: int, backwards: bool = False) -> dict | None:
    pattern = query.pattern()
    if pattern is None:
        return None
    if backwards:
        last = None
        for match in pattern.finditer(text, 0, max(0, position)):
            if match.end() - match.start() == 0:
                continue
            last = match
        if last is not None:
            return {"start": last.start(), "length": last.end() - last.start()}
        return None
    match = pattern.search(text, max(0, position))
    if match is None:
        match = pattern.search(text, 0)
    if match is None:
        return None
    if match.end() == match.start():
        return None
    return {"start": match.start(), "length": match.end() - match.start()}


def replace_all(text: str, query: Query, replacement: str) -> tuple[str, int]:
    pattern = query.pattern()
    if pattern is None:
        return text, 0
    # Regex replacement keeps group references; accept the common $1 spelling
    # as well as Python's \1. Literal replacement never interprets backslashes.
    if query.regex:
        repl = re.sub(r"\$(\d+)", r"\\\1", replacement)
        new_text, n = pattern.subn(repl, text)
        return new_text, n

    def _literal(match: re.Match) -> str:
        return replacement

    new_text, n = pattern.subn(_literal, text)
    return new_text, n


def replace_range(text: str, start: int, length: int, replacement: str) -> str:
    return text[:start] + replacement + text[start + length:]


def selection_for_matches(matches: list[dict], index: int) -> tuple[int, int]:
    if not matches:
        return (0, 0)
    index = max(0, min(index, len(matches) - 1))
    item = matches[index]
    return item["start"], item["start"] + item["length"]
