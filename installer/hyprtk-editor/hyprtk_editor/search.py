"""Incremental, regex and replace-all search over a document.

Pure functions over ``str`` so they are testable without Qt. Match positions
are absolute character offsets; the QML editor and the highlighter both work in
those terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_MATCHES = 20_000
MAX_PATTERN_LENGTH = 1_000

# A quantified group whose body is itself quantified (`(a+)+`, `(.*)*`) is the
# shape that backtracks exponentially. Python's `re` cannot be interrupted, so
# such a pattern on a 36 KB document froze the editor for minutes with no way
# out; refuse it up front instead.
_NESTED_QUANTIFIER = re.compile(
    r"""\(\s*(?:\?:|\?=|\?!|\?<=|\?<!)?[^()]*[*+][^()]*\)\s*(?:[*+]|\{\d*,?\d*\})"""
)


class SearchError(RuntimeError):
    """A pattern that cannot be run safely (or a bad replacement template)."""


def validate(query: "Query") -> str:
    """Return "" when the query is safe to run, else a user-facing reason."""
    if not query.text:
        return ""
    if len(query.text) > MAX_PATTERN_LENGTH:
        return f"pattern is longer than {MAX_PATTERN_LENGTH} characters"
    if query.regex and _NESTED_QUANTIFIER.search(query.text):
        return "nested quantifiers like (a+)+ can hang the search"
    return ""


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
        if not self.text or validate(self):
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
        try:
            new_text, n = pattern.subn(repl, text)
        except re.error as exc:
            raise SearchError(str(exc)) from exc
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


# -- fuzzy matching (quick open, command palette) ------------------------
# A subsequence match, scored so that the ranking feels like an editor's
# "type three letters and get the right file": adjacency beats scattering,
# a match at a word start beats one mid-word, and a shorter candidate beats a
# longer one that contains the same letters.
SEPARATORS = "/\\._- "


def fuzzy_score(needle: str, haystack: str) -> int | None:
    """Score ``needle`` against ``haystack``; ``None`` when it does not match.

    +1 per matched character, +6 when it is adjacent to the previous match,
    +4 when it starts a word, minus a small penalty for long candidates.
    Adjacency has to outweigh a word start: otherwise ``m_a_i_n.py`` would beat
    ``main.py``, because every underscore looks like the start of a word.
    """
    if not needle:
        return 0
    hay = str(haystack or "").lower()
    if not hay:
        return None
    score = 0
    position = -1
    previous = -2
    for char in needle.lower():
        index = hay.find(char, position + 1)
        if index < 0:
            return None
        score += 1
        if index == previous + 1:
            score += 6
        if index == 0 or hay[index - 1] in SEPARATORS:
            score += 4
        previous = index
        position = index
    score -= max(0, len(hay) - len(needle)) // 8
    return score


def rank(items, query: str, keys=("name", "path"), limit: int = 200) -> list[dict]:
    """Rank ``items`` (dicts) by their best score over ``keys``.

    An empty query keeps the incoming order and respects ``limit`` — that is
    what "show recents first" means. Ties keep the incoming order too.
    """
    rows = [item for item in (items or []) if isinstance(item, dict)]
    if not query:
        return rows[:limit]
    scored = []
    for order, item in enumerate(rows):
        best = None
        for key in keys:
            value = item.get(key)
            if not value:
                continue
            score = fuzzy_score(query, str(value))
            if score is not None and (best is None or score > best):
                best = score
        if best is not None:
            scored.append((-best, order, item))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in scored[:limit]]
