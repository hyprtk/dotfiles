"""Syntax highlighting for a QML TextArea.

Two facts drove this design, both measured on this stack:

* ``QSyntaxHighlighter`` applies formats per block and every block emits a
  document change that QML's text node honours; a whole-document
  ``rehighlight()`` is therefore quadratic (76 KiB took 2.4 s, 305 KiB 40 s).
* ``QTextLayout.setFormats`` in bulk is fast (54 ms for 24k blocks) but
  QQuickTextEdit does not paint formats applied that way.

So highlighting is **viewport-scoped**: Pygments tokenises the document once
(135 ms for 6,000 lines) into per-line spans, and only the blocks on screen
(plus the block being edited) are pushed through ``rehighlightBlock``. Edits
stay at 2-8 ms even in a 24,000-line file.
"""

from __future__ import annotations

import bisect
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat

from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)

from . import languages

MAX_HIGHLIGHT_CHARS = 400_000
PAGE_BLOCKS = 60


def style_for(ttype) -> str | None:
    if ttype in Error:
        return "error"
    if ttype in Comment:
        return "comment"
    if ttype in Keyword.Type:
        return "type"
    if ttype in Keyword.Constant:
        return "constant"
    if ttype in Keyword:
        return "keyword"
    if ttype in Name.Function or ttype in Name.Decorator:
        return "function"
    if ttype in Name.Class or ttype in Name.Exception or ttype in Name.Namespace:
        return "class"
    if ttype in Name.Builtin:
        return "builtin"
    if ttype in Name.Tag:
        return "tag"
    if ttype in Name.Attribute:
        return "attribute"
    if ttype in Name.Constant:
        return "constant"
    if ttype in Name.Variable:
        return "variable"
    if ttype in String:
        return "string"
    if ttype in Number:
        return "number"
    if ttype in Operator:
        return "operator"
    if ttype in Punctuation:
        return "punctuation"
    if ttype in Generic.Heading or ttype in Generic.Subheading:
        return "heading"
    if ttype in Generic.Inserted:
        return "added"
    if ttype in Generic.Deleted:
        return "deleted"
    if ttype in Text:
        return None
    if ttype in Literal:
        return "constant"
    return None


def spans(text: str, alias: str) -> dict[int, list[tuple[int, int, str]]]:
    """Tokenise ``text`` into ``{line: [(column, length, style), ...]}``."""
    if len(text) > MAX_HIGHLIGHT_CHARS:
        return {}
    lexer = languages.lexer_for(alias or "text")
    out: dict[int, list[tuple[int, int, str]]] = {}
    line = 0
    column = 0
    try:
        tokens = lexer.get_tokens(text)
        for ttype, value in tokens:
            if not value:
                continue
            style = style_for(ttype)
            parts = value.split("\n")
            for index, part in enumerate(parts):
                if index:
                    line += 1
                    column = 0
                if part and style is not None and not part.isspace():
                    out.setdefault(line, []).append((column, len(part), style))
                column += len(part)
    except Exception:
        return {}
    return out


def plain_spans(text: str, style: str = "punctuation") -> dict:
    """Fallback used when a lexer explodes: one span per non-empty line."""
    out: dict[int, list[tuple[int, int, str]]] = {}
    for index, line in enumerate(text.split("\n")):
        if line.strip():
            out[index] = [(0, len(line), style)]
    return out


class Highlighter(QSyntaxHighlighter):
    def __init__(self, document, palette: dict, settings: dict | None = None) -> None:
        super().__init__(document)
        self.syntax = dict(palette.get("syntax") or {})
        self.theme = palette
        self.opts = settings or {}
        self.spans: dict[int, list[tuple[int, int, str]]] = {}
        self.search: list[tuple[int, int, bool]] = []
        self._search_starts: list[int] = []
        self.current_line = -1
        self.brackets: set[tuple[int, int]] = set()
        self.enabled = True
        self._formats: dict[str, QTextCharFormat] = {}
        self._line_bg = self._alpha_format(palette.get("accent", "#c084fc"), 0.10)
        self._match_bg = self._alpha_format(palette.get("warning", "#f9e2af"), 0.28)
        self._match_current_bg = self._alpha_format(palette.get("accent", "#c084fc"), 0.42)
        self._bracket_fmt = self._alpha_format(palette.get("accent2", "#22d3ee"), 0.38, bold=True)

    # -- formats ---------------------------------------------------------
    @staticmethod
    def _alpha_format(color: str, alpha: float, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        value = QColor(color)
        value.setAlphaF(alpha)
        fmt.setBackground(value)
        if bold:
            fmt.setFontWeight(700)
        return fmt

    def _format(self, style: str) -> QTextCharFormat:
        fmt = self._formats.get(style)
        if fmt is not None:
            return fmt
        color = QColor(self.syntax.get(style) or self.theme.get("foreground", "#e5e7eb"))
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        if style == "comment":
            fmt.setFontItalic(True)
        self._formats[style] = fmt
        return fmt

    def apply_palette(self, palette: dict) -> None:
        self.theme = palette
        self.syntax = dict(palette.get("syntax") or {})
        self._formats.clear()
        self._line_bg = self._alpha_format(palette.get("accent", "#c084fc"), 0.10)
        self._match_bg = self._alpha_format(palette.get("warning", "#f9e2af"), 0.28)
        self._match_current_bg = self._alpha_format(palette.get("accent", "#c084fc"), 0.42)
        self._bracket_fmt = self._alpha_format(palette.get("accent2", "#22d3ee"), 0.38, bold=True)

    # -- state -----------------------------------------------------------
    def set_spans(self, value: dict) -> None:
        self.spans = value or {}

    def set_search(self, ranges: list[tuple[int, int, bool]]) -> None:
        self.search = sorted(ranges or [], key=lambda item: item[0])
        self._search_starts = [item[0] for item in self.search]

    def set_current_line(self, line: int) -> None:
        self.current_line = int(line)

    def set_brackets(self, positions) -> None:
        self.brackets = {(int(line), int(col)) for line, col in (positions or [])}

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    # -- painting --------------------------------------------------------
    def highlightBlock(self, text: str) -> None:
        if not self.enabled:
            return
        block = self.currentBlock()
        line = block.blockNumber()

        for start, length, style in self.spans.get(line, ()):
            if length > 0:
                self.setFormat(start, min(length, max(0, len(text) - start)), self._format(style))

        if self.opts.get("highlight_current_line", True) and line == self.current_line:
            self.setFormat(0, len(text), self._line_bg)

        if self.search:
            block_start = block.position()
            block_end = block_start + len(text)
            index = max(0, bisect.bisect_right(self._search_starts, block_start) - 1)
            while index < len(self.search):
                start, length, current = self.search[index]
                if start >= block_end:
                    break
                end = start + length
                if end > block_start:
                    lo = max(start, block_start) - block_start
                    hi = min(end, block_end) - block_start
                    if hi > lo:
                        fmt = self._match_current_bg if current else self._match_bg
                        self.setFormat(lo, hi - lo, fmt)
                index += 1

        for bracket_line, column in self.brackets:
            if bracket_line == line and 0 <= column < len(text):
                self.setFormat(column, 1, self._bracket_fmt)
