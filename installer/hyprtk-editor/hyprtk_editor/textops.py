"""Line and selection operations.

Everything is a pure ``str`` transform that also returns the new selection, so
the QML editor only has to write back ``text`` and restore two offsets. This
keeps the tricky part (multi-line selections, trailing newlines) testable.
"""

from __future__ import annotations

import re

WORD_RE = re.compile(r"\S+")


def line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, max(0, pos)) + 1


def line_end(text: str, pos: int) -> int:
    idx = text.find("\n", max(0, pos))
    return len(text) if idx < 0 else idx


def line_index(text: str, pos: int) -> int:
    return text.count("\n", 0, max(0, pos))


def selected_line_bounds(text: str, sel_start: int, sel_end: int) -> tuple[int, int]:
    start, end = sorted((max(0, sel_start), max(0, sel_end)))
    lo = line_start(text, start)
    # A selection that stops exactly at a line start does not include that line.
    if end > start and text[end - 1:end] == "\n":
        hi = end
    else:
        hi = min(len(text), line_end(text, end) + 1)
    return lo, hi


def _document_range(text: str, sel_start: int, sel_end: int) -> tuple[int, int]:
    """Document-wide ops apply to everything when nothing is selected."""
    start, end = sorted((max(0, sel_start), max(0, sel_end)))
    if start == end:
        return 0, len(text)
    return start, end


def _result(text: str, start: int, end: int) -> dict:
    length = len(text)
    return {
        "text": text,
        "selStart": max(0, min(start, length)),
        "selEnd": max(0, min(end, length)),
    }


def duplicate(text: str, sel_start: int, sel_end: int) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    block = text[lo:hi]
    if not block:
        return _result(text, sel_start, sel_end)
    if block.endswith("\n"):
        new = text[:hi] + block + text[hi:]
        return _result(new, hi, hi + len(block))
    new = text[:hi] + "\n" + block + text[hi:]
    return _result(new, hi + 1, hi + 1 + len(block))


def _swap(text: str, lo: int, hi: int, upwards: bool) -> dict:
    if lo <= 0 and upwards:
        return _result(text, lo, hi)
    if hi >= len(text) and not upwards:
        return _result(text, lo, hi)

    if upwards:
        prev_lo = line_start(text, lo - 1)
        prev = text[prev_lo:lo]
        block = text[lo:hi]
        new = text[:prev_lo] + block + prev + text[hi:]
        return _result(new, prev_lo, prev_lo + len(block))
    # Move down: swap the selected block with the following line.
    next_hi = min(len(text), line_end(text, hi) + 1)
    following = text[hi:next_hi]
    block = text[lo:hi]
    new = text[:lo] + following + block + text[next_hi:]
    return _result(new, lo + len(following), hi + len(following))


def move_up(text: str, sel_start: int, sel_end: int) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    return _swap(text, lo, hi, True)


def move_down(text: str, sel_start: int, sel_end: int) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    return _swap(text, lo, hi, False)


def delete_lines(text: str, sel_start: int, sel_end: int) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    new = text[:lo] + text[hi:]
    return _result(new, lo, lo)


def _lines(text: str, lo: int, hi: int) -> list[str]:
    block = text[lo:hi]
    if not block:
        return []
    trailing = block.endswith("\n")
    parts = block.split("\n")
    if trailing:
        parts = parts[:-1]
    return parts


def toggle_comment(
    text: str, sel_start: int, sel_end: int, prefix: str = "#"
) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    lines = _lines(text, lo, hi)
    if not lines:
        return _result(text, sel_start, sel_end)

    stripped = [ln.lstrip(" \t") for ln in lines]
    non_empty = [ln for ln in stripped if ln]
    commented = bool(non_empty) and all(ln.startswith(prefix) for ln in non_empty)

    if commented:
        out = []
        for line in lines:
            indent = line[: len(line) - len(line.lstrip(" \t"))]
            rest = line[len(indent):]
            if rest.startswith(prefix):
                rest = rest[len(prefix):]
                if rest.startswith(" "):
                    rest = rest[1:]
            out.append(indent + rest)
    else:
        out = []
        for line in lines:
            indent = line[: len(line) - len(line.lstrip(" \t"))]
            rest = line[len(indent):]
            if not rest:
                out.append(line)
            else:
                out.append(f"{indent}{prefix} {rest}")

    new = text[:lo] + "\n".join(out) + ("\n" if text[lo:hi].endswith("\n") else "") + text[hi:]
    return _result(new, lo, lo + len("\n".join(out)))


def sort_lines(
    text: str, sel_start: int, sel_end: int, reverse: bool = False, unique: bool = False
) -> dict:
    start, end = _document_range(text, sel_start, sel_end)
    lo, hi = selected_line_bounds(text, start, end)
    lines = _lines(text, lo, hi)
    if not lines:
        return _result(text, sel_start, sel_end)
    if unique:
        seen = set()
        deduped = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)
        lines = deduped
    lines.sort(reverse=reverse)
    block = "\n".join(lines)
    if text[lo:hi].endswith("\n"):
        block += "\n"
    new = text[:lo] + block + text[hi:]
    return _result(new, lo, lo + len(block))


def trim_trailing(text: str, sel_start: int, sel_end: int) -> dict:
    start, end = sorted((max(0, sel_start), max(0, sel_end)))
    if start == end:
        start, end = 0, len(text)
    lo = line_start(text, start)
    hi = min(len(text), line_end(text, end) + 1)
    block = re.sub(r"[ \t]+(?=\n|$)", "", text[lo:hi])
    new = text[:lo] + block + text[hi:]
    return _result(new, lo, lo + len(block))


def indent(text: str, sel_start: int, sel_end: int, width: int = 4, spaces: bool = True) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    lines = _lines(text, lo, hi)
    if not lines:
        return _result(text, sel_start, sel_end)
    unit = " " * max(1, width) if spaces else "\t"
    out = [(unit + line) if line else line for line in lines]
    block = "\n".join(out) + ("\n" if text[lo:hi].endswith("\n") else "")
    new = text[:lo] + block + text[hi:]
    return _result(new, sel_start + len(unit), sel_end + len(unit) * len(out))


def outdent(text: str, sel_start: int, sel_end: int, width: int = 4, spaces: bool = True) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    lines = _lines(text, lo, hi)
    if not lines:
        return _result(text, sel_start, sel_end)
    unit = " " * max(1, width) if spaces else "\t"
    out = []
    removed = 0
    for line in lines:
        if line.startswith(unit):
            out.append(line[len(unit):])
            removed += len(unit)
        elif line.startswith("\t"):
            out.append(line[1:])
            removed += 1
        else:
            stripped = line.lstrip(" ")
            cut = min(len(line) - len(stripped), max(1, width))
            out.append(line[cut:])
            removed += cut
    block = "\n".join(out) + ("\n" if text[lo:hi].endswith("\n") else "")
    new = text[:lo] + block + text[hi:]
    return _result(new, max(lo, sel_start - 1), max(lo, sel_end - removed))


def join_lines(text: str, sel_start: int, sel_end: int) -> dict:
    lo, hi = selected_line_bounds(text, sel_start, sel_end)
    lines = _lines(text, lo, hi)
    if len(lines) < 2:
        return _result(text, sel_start, sel_end)
    joined = " ".join(line.strip() for line in lines)
    new = text[:lo] + joined + ("\n" if text[lo:hi].endswith("\n") else "") + text[hi:]
    return _result(new, lo, lo + len(joined))


def change_case(text: str, sel_start: int, sel_end: int, mode: str) -> dict:
    start, end = sorted((max(0, sel_start), max(0, sel_end)))
    if start == end:
        start, end = line_start(text, start), line_end(text, start)
    chunk = text[start:end]
    if mode == "upper":
        chunk = chunk.upper()
    elif mode == "lower":
        chunk = chunk.lower()
    else:
        chunk = chunk.title()
    new = text[:start] + chunk + text[end:]
    return _result(new, start, start + len(chunk))


def convert_indent(
    text: str, sel_start: int, sel_end: int, to_spaces: bool, width: int = 4
) -> dict:
    start, end = _document_range(text, sel_start, sel_end)
    lo, hi = selected_line_bounds(text, start, end)
    lines = _lines(text, lo, hi)
    out = []
    for line in lines:
        if to_spaces:
            out.append(line.expandtabs(max(1, width)))
        else:
            stripped = line.lstrip(" ")
            count = len(line) - len(stripped)
            tabs, rest = divmod(count, max(1, width))
            out.append("\t" * tabs + " " * rest + stripped)
    block = "\n".join(out) + ("\n" if text[lo:hi].endswith("\n") else "")
    new = text[:lo] + block + text[hi:]
    return _result(new, lo, lo + len(block))


def stats(text: str, sel_start: int = 0, sel_end: int = 0) -> dict:
    start, end = sorted((max(0, sel_start), max(0, sel_end)))
    chunk = text[start:end] if end > start else text
    return {
        "chars": len(chunk),
        "words": len(WORD_RE.findall(chunk)),
        "lines": chunk.count("\n") + (1 if chunk else 0),
        "bytes": len(chunk.encode("utf-8")),
    }


def apply(text: str, sel_start: int, sel_end: int, op: str, **kwargs) -> dict:
    """Dispatch used by the QML bridge; keeps the op names in one place."""
    table = {
        "duplicate": duplicate,
        "moveUp": move_up,
        "moveDown": move_down,
        "deleteLines": delete_lines,
        "sortAsc": lambda t, s, e: sort_lines(t, s, e, False, False),
        "sortDesc": lambda t, s, e: sort_lines(t, s, e, True, False),
        "sortUnique": lambda t, s, e: sort_lines(t, s, e, False, True),
        "trimTrailing": trim_trailing,
        "joinLines": join_lines,
    }
    fn = table.get(op)
    if fn is None:
        return _result(text, sel_start, sel_end)
    return fn(text, sel_start, sel_end)
