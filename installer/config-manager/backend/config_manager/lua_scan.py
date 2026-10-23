"""Comment/string-aware scanning of Lua config text.

No dependencies: we only need to locate hl.* call spans and key/value spans
inside their argument tables so edits can be surgical. Every function works on
the *masked* text where comments and string contents are replaced by spaces,
which keeps byte offsets identical to the original.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_IDENT = re.compile(r"[A-Za-z_]\w*")
_LONG_OPEN = re.compile(r"\[(=*)\[")


def mask(text: str) -> str:
    """Return text with comments and string contents blanked out."""
    out = list(text)
    i, n = 0, len(text)

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = text[i]
        # long comment / long string
        if c == "-" and text.startswith("--", i):
            m = _LONG_OPEN.match(text, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                end = text.find(close, m.end())
                end = n if end < 0 else end + len(close)
                blank(i, end)
                i = end
            else:
                end = text.find("\n", i)
                end = n if end < 0 else end
                blank(i, end)
                i = end
            continue
        if c == "[":
            m = _LONG_OPEN.match(text, i)
            if m:
                close = "]" + m.group(1) + "]"
                end = text.find(close, m.end())
                end = n if end < 0 else end + len(close)
                blank(i + len(m.group(0)), end - len(close))
                i = end
                continue
        if c in ('"', "'"):
            quote = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == quote:
                    j += 1
                    break
                if text[j] == "\n":
                    break
                j += 1
            blank(i + 1, j - 1)
            i = j
            continue
        i += 1
    return "".join(out)


def _skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i].isspace():
        i += 1
    return i


def balanced(masked: str, open_idx: int) -> int:
    """Index of the bracket matching masked[open_idx]; -1 if unbalanced."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    opener = masked[open_idx]
    if opener not in pairs:
        raise ValueError(f"not an opener: {opener!r}")
    stack = [pairs[opener]]
    i = open_idx + 1
    while i < len(masked):
        c = masked[i]
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            if not stack or c != stack[-1]:
                return -1
            stack.pop()
            if not stack:
                return i
        i += 1
    return -1


@dataclass(frozen=True)
class Call:
    kind: str
    start: int          # index of 'hl'
    open_paren: int
    close_paren: int

    @property
    def end(self) -> int:
        return self.close_paren + 1


def find_calls(text: str, kinds: tuple[str, ...] | None = None) -> list[Call]:
    """All `hl.<kind>(...)` calls, in source order."""
    masked = mask(text)
    pattern = re.compile(r"\bhl\s*\.\s*([A-Za-z_]\w*)\s*\(")
    out: list[Call] = []
    for m in pattern.finditer(masked):
        kind = m.group(1)
        if kinds and kind not in kinds:
            continue
        open_paren = m.end() - 1
        close = balanced(masked, open_paren)
        if close < 0:
            continue
        out.append(Call(kind, m.start(), open_paren, close))
    return out


def first_table_arg(text: str, call: Call) -> int:
    """Index of the first '{' inside a call's parens, or -1."""
    masked = mask(text)
    i = _skip_ws(masked, call.open_paren + 1)
    return i if i < len(masked) and masked[i] == "{" else -1


@dataclass(frozen=True)
class Span:
    start: int
    end: int           # exclusive


def _value_end(masked: str, start: int, stop: int) -> int:
    """End of a value starting at `start`, before a top-level , or }."""
    i = start
    depth = 0
    while i < stop:
        c = masked[i]
        if c in "{[(":
            depth += 1
        elif c in "}])":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    end = i
    while end > start and masked[end - 1].isspace():
        end -= 1
    return end


def find_key(masked: str, open_brace: int, key: str) -> Span | None:
    """Value span for `key` at the top level of the table at open_brace."""
    close = balanced(masked, open_brace)
    if close < 0:
        return None
    i = open_brace + 1
    while i < close:
        i = _skip_ws(masked, i)
        if i >= close:
            break
        if masked.startswith("--", i):          # shouldn't survive mask
            i = masked.find("\n", i)
            if i < 0:
                break
            continue
        if masked[i] == ",":
            i += 1
            continue
        # key: identifier or ["string"] / ['string']
        m = _IDENT.match(masked, i)
        if m:
            name = m.group(0)
            eq = _skip_ws(masked, m.end())
        elif masked[i] == "[":
            q = masked.find("]", i)
            if q < 0:
                break
            name = None
            eq = _skip_ws(masked, q + 1)
        else:
            break
        if eq >= close or masked[eq] != "=" or masked.startswith("==", eq):
            # not a key = value entry; skip to next top-level comma
            i = _value_end(masked, i, close) + 1
            continue
        vstart = _skip_ws(masked, eq + 1)
        vend = _value_end(masked, vstart, close)
        if name == key:
            return Span(vstart, vend)
        i = vend + 1
    return None


def find_path(masked: str, open_brace: int, path: list[str]) -> Span | None:
    """Value span for a nested key path, descending into tables."""
    span = find_key(masked, open_brace, path[0])
    if span is None:
        return None
    if len(path) == 1:
        return span
    nested = _skip_ws(masked, span.start)
    if nested >= len(masked) or masked[nested] != "{":
        return None
    return find_path(masked, nested, path[1:])


def indent_of_line(text: str, index: int) -> str:
    line_start = text.rfind("\n", 0, index) + 1
    chunk = text[line_start:index]
    return chunk[: len(chunk) - len(chunk.lstrip())] if chunk.strip() == "" else ""


def insert_key(text: str, open_brace: int, key: str, literal: str) -> str:
    """Insert `key = literal` into the table, preserving indentation."""
    masked = mask(text)
    close = balanced(masked, open_brace)
    if close < 0:
        raise ValueError("unbalanced table")
    body = masked[open_brace + 1:close]
    if not body.strip():
        return text[: open_brace + 1] + f" {key} = {literal} " + text[close:]

    # Single-line table: append inline, comma first if the body needs one.
    if "\n" not in text[open_brace:close]:
        last = close - 1
        while last > open_brace and masked[last].isspace():
            last -= 1
        comma = "" if masked[last] == "," else ","
        return text[:close] + f"{comma} {key} = {literal} " + text[close:]

    close_indent = indent_of_line(text, close)
    # Prefer the indentation of the first key rather than the closing brace.
    first = _skip_ws(masked, open_brace + 1)
    key_indent = indent_of_line(text, first) or (close_indent + "    ")
    last = close - 1
    while last > open_brace and masked[last].isspace():
        last -= 1
    comma = "" if masked[last] == "," else ","
    insertion = f"{comma}\n{key_indent}{key} = {literal},"
    return text[:close] + insertion + text[close:]


def replace_span(text: str, span: Span, new: str) -> str:
    return text[: span.start] + new + text[span.end:]


def set_require_active(text: str, module: str) -> str:
    """Make `require(module)` the single active animations-* require."""
    lines = text.splitlines(keepends=True)
    pat = re.compile(
        r'^(?P<indent>\s*)(?P<comment>--\s*)?require\(\s*(["\'])'
        r'animations-[\w-]+\3\s*\)'
    )
    hits = [i for i, line in enumerate(lines) if pat.match(line)]
    if not hits:
        req = re.compile(r'^(?P<indent>\s*)require\(')
        anchors = [i for i, line in enumerate(lines) if req.match(line)]
        insert_at = (anchors[-1] + 1) if anchors else len(lines)
        indent = pat.match(lines[anchors[-1]]).group("indent") if anchors else ""
        lines.insert(insert_at, f'{indent}require("{module}")\n')
        return "".join(lines)

    anchor = hits[0]
    indent = pat.match(lines[anchor]).group("indent")
    for i in hits:
        name = re.search(r'animations-[\w-]+', lines[i]).group(0)
        if i == anchor:
            lines[i] = f'{indent}require("{module}")\n'
        else:
            lines[i] = f'{indent}-- require("{name}")\n'
    return "".join(lines)


def arg_spans(text: str, call: Call) -> list[Span]:
    """Top-level argument spans inside a call's parentheses."""
    masked = mask(text)
    spans: list[Span] = []
    i = call.open_paren + 1
    stop = call.close_paren
    while i < stop:
        i = _skip_ws(masked, i)
        if i >= stop:
            break
        end = _value_end(masked, i, stop)
        if end <= i:
            break
        spans.append(Span(i, end))
        i = end
        while i < stop and masked[i].isspace():
            i += 1
        if i < stop and masked[i] == ",":
            i += 1
        else:
            break
    return spans
