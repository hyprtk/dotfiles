"""Print and PDF rendering.

The live document is never printed directly: it carries the dark pywal palette
in its char formats, so on paper it would be pale text on white. This module
builds a *separate* light-theme document from the plain text and re-applies the
Pygments spans in print colours, which also keeps the on-screen formats (search
highlights, current line, brackets) out of the output.
"""

from __future__ import annotations

import os
import time

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPdfWriter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)

from .highlight import spans

# A light theme: the page is the one surface that is not the desktop.
PRINT_SYNTAX = {
    "comment": "#6a737d",
    "keyword": "#8250df",
    "type": "#0550ae",
    "constant": "#0550ae",
    "string": "#0a7a40",
    "number": "#0550ae",
    "function": "#6639ba",
    "class": "#953800",
    "builtin": "#0550ae",
    "tag": "#116329",
    "attribute": "#0550ae",
    "variable": "#953800",
    "operator": "#24292f",
    "punctuation": "#24292f",
    "heading": "#0550ae",
    "added": "#116329",
    "deleted": "#cf222e",
    "error": "#cf222e",
}
BODY_COLOUR = "#1f2328"
DIM_COLOUR = "#6a737d"
FONT_SIZE = 10
MAX_COLOUR_CHARS = 400_000


def build(
    text: str,
    title: str = "",
    alias: str = "text",
    family: str = "monospace",
    size: int = FONT_SIZE,
    colour: bool = True,
    stamp: str = "",
):
    """Return a standalone light-theme ``QTextDocument`` for printing."""
    document = QTextDocument()
    font = QFont(family, size)
    document.setDefaultFont(font)
    document.setDocumentMargin(0)  # page margins come from the printer

    cursor = QTextCursor(document)

    heading = QTextCharFormat()
    heading.setFont(font)
    heading.setFontWeight(QFont.DemiBold)
    heading.setForeground(QColor(BODY_COLOUR))
    cursor.insertText(title or "Untitled", heading)
    cursor.insertBlock()

    dim = QTextCharFormat()
    dim.setFont(font)
    dim.setForeground(QColor(DIM_COLOUR))
    cursor.insertText(stamp or time.strftime("%Y-%m-%d %H:%M"), dim)
    cursor.insertBlock()
    cursor.insertBlock()

    body = QTextCharFormat()
    body.setFont(font)
    body.setForeground(QColor(BODY_COLOUR))

    use_colour = bool(colour) and len(text) <= MAX_COLOUR_CHARS
    span_map = spans(text, alias or "text") if use_colour else {}

    lines = text.split("\n")
    for index, line in enumerate(lines):
        _insert_line(cursor, line, span_map.get(index, ()), body)
        if index != len(lines) - 1:
            cursor.insertBlock()
    return document


def _insert_line(cursor: QTextCursor, line: str, line_spans, body: QTextCharFormat) -> None:
    position = 0
    for start, length, style in line_spans or ():
        if start > position:
            cursor.insertText(line[position:start], body)
        chunk = line[start:start + length]
        if chunk:
            fmt = QTextCharFormat()
            fmt.setFont(body.font())
            fmt.setForeground(QColor(PRINT_SYNTAX.get(style, BODY_COLOUR)))
            if style == "comment":
                fmt.setFontItalic(True)
            cursor.insertText(chunk, fmt)
        position = max(position, start + length)
    if position < len(line):
        cursor.insertText(line[position:], body)


def _fit(document: QTextDocument, device) -> None:
    """Lay the document out at the device's body size.

    ``QTextDocument.print_`` adds its own margin when the document has no page
    size (ink landed 22 mm from the corner even with 0 mm device margins), and
    it cannot paginate without a height. Setting the body rect fixes both.
    """
    rect = device.pageLayout().paintRect(QPageLayout.Point)
    if rect.width() > 1 and rect.height() > 1:
        document.setPageSize(QSizeF(rect.width(), rect.height()))


def write_pdf(document: QTextDocument, path: str, title: str = "") -> int:
    """Write ``document`` to ``path`` as A4 PDF; returns the file size in bytes."""
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setResolution(300)
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)
    writer.setTitle(title or os.path.basename(str(path)))
    _fit(document, writer)
    document.print_(writer)
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def prepare_printer(title: str = ""):
    """A high-resolution printer for ``QPrintDialog`` to configure."""
    from PySide6.QtPrintSupport import QPrinter

    printer = QPrinter(QPrinter.HighResolution)
    printer.setDocName(title or "hyprtk-editor document")
    printer.setPageOrientation(QPageLayout.Portrait)
    return printer


def print_to(printer, document: QTextDocument) -> None:
    _fit(document, printer)
    document.print_(printer)
