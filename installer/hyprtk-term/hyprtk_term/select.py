"""Selection and text extraction.

Kept out of the QML item so the behaviour can be tested without a display: the
view turns mouse coordinates into a ``(line, col)`` pair, everything below is
pure list work.
"""

from __future__ import annotations

WordTest = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"


def is_word(ch: str) -> bool:
    return bool(ch) and ch in WordTest


def word_bounds(cells: list[str], col: int) -> tuple[int, int]:
    """Half-open ``(start, end)`` of the word around ``col``.

    Punctuation selects the single cell under the cursor, which is what xterm
    and every other terminal do.
    """
    if not cells:
        return 0, 0
    col = max(0, min(col, len(cells) - 1))
    if not is_word(cells[col]):
        return col, col + 1
    start = col
    while start > 0 and is_word(cells[start - 1]):
        start -= 1
    end = col + 1
    while end < len(cells) and is_word(cells[end]):
        end += 1
    return start, end


def line_text(cells: list[str]) -> str:
    """A line's cells as text, with trailing blanks removed."""
    return "".join(cells).rstrip()


def selection_text(vt, selection: tuple[int, int, int, int] | None) -> str:
    """Text for an absolute ``(line0, col0, line1, col1)`` selection."""
    if not selection:
        return ""
    l0, c0, l1, c1 = selection
    if (l1, c1) < (l0, c0):
        l0, c0, l1, c1 = l1, c1, l0, c0
    out: list[str] = []
    cols = getattr(vt, "cols", 0)
    cached = getattr(vt, "line_text", None)
    for line in range(l0, l1 + 1):
        # Whole lines come from the cached scrollback text; building cells for
        # 10k lines is one ctypes call per cell (~0.55 s for a full copy).
        first_partial = line == l0 and c0 > 0
        last_partial = line == l1 and (c1 < cols if cols else True)
        if cached is not None and cols and not first_partial and not last_partial:
            out.append(cached(line))
            continue
        cells = vt.line_cells(line)
        if not cells:
            out.append("")
            continue
        start = c0 if first_partial else 0
        end = c1 if last_partial else len(cells)
        out.append(line_text(cells[start:end]))
    return "\n".join(out)


def normalize(selection: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    l0, c0, l1, c1 = selection
    if (l1, c1) < (l0, c0):
        return l1, c1, l0, c0
    return l0, c0, l1, c1
