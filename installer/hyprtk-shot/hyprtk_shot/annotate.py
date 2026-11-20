"""Annotations: a small, serialisable shape model and its QPainter renderer.

The model is deliberately dumb — plain floats in image pixels, no Qt types —
so the CLI, the settings file and the undo stack can all hold it. Only
:func:`render` needs Qt, and it paints onto a *copy* of the capture.

Tools mirror what the good screenshot editors offer (Flameshot, Satty,
Spectacle): pen, line, arrow, rectangle, ellipse, highlighter, step marker,
text, blur and pixelate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

TOOLS = (
    "cursor",
    "pen",
    "line",
    "arrow",
    "rect",
    "ellipse",
    "highlight",
    "marker",
    "text",
    "blur",
    "pixelate",
)

#: Tools that are drawn as a drag between a start and an end point.
RECT_TOOLS = ("line", "arrow", "rect", "ellipse", "blur", "pixelate")

LABELS = {
    "cursor": "Select",
    "pen": "Pen",
    "line": "Line",
    "arrow": "Arrow",
    "rect": "Rectangle",
    "ellipse": "Ellipse",
    "highlight": "Highlighter",
    "marker": "Step",
    "text": "Text",
    "blur": "Blur",
    "pixelate": "Pixelate",
}

PALETTE = ("#fd4fb6", "#02dede", "#f9e2af", "#a6e3a1", "#89b4fa", "#ffffff")


@dataclass
class Shape:
    kind: str
    points: list[tuple[float, float]] = field(default_factory=list)
    color: str = "#fd4fb6"
    width: float = 4.0
    text: str = ""
    filled: bool = False

    # -- geometry
    @property
    def start(self) -> tuple[float, float]:
        return self.points[0] if self.points else (0.0, 0.0)

    @property
    def end(self) -> tuple[float, float]:
        return self.points[-1] if self.points else (0.0, 0.0)

    def bounds(self) -> tuple[float, float, float, float]:
        """``x, y, w, h`` in image pixels, always non-negative."""
        if not self.points:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def add(self, x: float, y: float) -> None:
        self.points.append((float(x), float(y)))

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "points": [[round(x, 2), round(y, 2)] for x, y in self.points],
            "color": self.color,
            "width": self.width,
            "text": self.text,
            "filled": self.filled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Shape":
        return cls(
            kind=str(data.get("kind") or "pen"),
            points=[(float(p[0]), float(p[1])) for p in data.get("points") or []],
            color=str(data.get("color") or "#fd4fb6"),
            width=float(data.get("width") or 4.0),
            text=str(data.get("text") or ""),
            filled=bool(data.get("filled")),
        )


def new_shape(kind: str, x: float, y: float, *, color: str, width: float, text: str = "") -> Shape:
    if kind not in TOOLS or kind == "cursor":
        raise ValueError(f"not an annotation tool: {kind}")
    return Shape(kind=kind, points=[(float(x), float(y))], color=color,
                 width=float(width), text=text)


# ------------------------------------------------------------- rendering ---

def _qrect(x: float, y: float, w: float, h: float):
    from PySide6.QtCore import QRectF

    return QRectF(float(x), float(y), float(w), float(h))


def _blurred(base, rect, *, pixelate: bool):
    """Block-blur or pixelate a patch of ``base``, in image pixels."""
    from PySide6.QtCore import QRect, Qt

    box = QRect(int(round(rect[0])), int(round(rect[1])),
                max(1, int(round(rect[2]))), max(1, int(round(rect[3]))))
    box = box.intersected(base.rect())
    if box.width() < 2 or box.height() < 2:
        return None, box
    patch = base.copy(box)
    if pixelate:
        block = 12
        small = patch.scaled(max(1, box.width() // block), max(1, box.height() // block),
                             Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return small.scaled(box.width(), box.height(), Qt.IgnoreAspectRatio, Qt.FastTransformation), box
    # A two-pass down/up sample is a cheap, dependency-free box blur that reads
    # as "redacted" without pulling in QtWidgets (QGraphicsBlurEffect).
    small = patch.scaled(max(1, box.width() // 9), max(1, box.height() // 9),
                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return small.scaled(box.width(), box.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation), box


def _arrow_head(painter, start, end, width: float) -> None:
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF

    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1.0:
        return
    ux, uy = dx / length, dy / length
    head = max(14.0, width * 4.5)
    spread = head * 0.42
    tip = QPointF(end[0], end[1])
    left = QPointF(end[0] - ux * head - uy * spread, end[1] - uy * head + ux * spread)
    right = QPointF(end[0] - ux * head + uy * spread, end[1] - uy * head - ux * spread)
    painter.drawPolygon(QPolygonF([tip, left, right]))


def _draw_text(painter, shape: Shape, scale: float) -> None:
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QFont

    if not shape.text:
        return
    font = QFont()
    for family in ("Inter", "Cantarell", "DejaVu Sans", "sans-serif"):
        font.setFamily(family)
        if font.exactMatch():
            break
    font.setPixelSize(max(12, int(round(22 * scale))))
    font.setBold(True)
    painter.setFont(font)
    x, y = shape.start
    # A dark halo keeps text readable on any wallpaper; the main colour goes on
    # top, which is what Satty's "contrast outline" does.
    painter.setPen(QColor(0, 0, 0, 170))
    for ox, oy in ((1.5, 1.5), (-1.5, 1.5), (1.5, -1.5), (-1.5, -1.5)):
        painter.drawText(QPointF(x + ox, y + oy), shape.text)
    painter.setPen(QColor(shape.color))
    painter.drawText(QPointF(x, y), shape.text)


def _draw_marker(painter, shape: Shape, index: int, scale: float) -> None:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont

    radius = max(11.0, 15.0 * scale)
    x, y = shape.start
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(shape.color))
    painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(10, int(round(radius * 1.15))))
    painter.setFont(font)
    painter.setPen(QColor("#11111b"))
    painter.drawText(QRectF(x - radius, y - radius, radius * 2, radius * 2),
                     Qt.AlignCenter, str(index))


def paint_shape(painter, shape: Shape, *, scale: float = 1.0, marker_index: int = 1,
                base=None) -> None:
    """Draw one annotation with an already-active ``QPainter``.

    Preview and final render share this, so what the user sees while dragging is
    the same code that writes the file. ``base`` is the untouched capture; only
    the blur and pixelate tools need it (they sample the original pixels).
    """
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QPen

    kind = shape.kind
    color = QColor(shape.color)
    pen = QPen(color)
    pen.setWidthF(max(1.0, shape.width * scale))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if kind in ("blur", "pixelate"):
        x, y, w, h = shape.bounds()
        if w < 1 or h < 1 or base is None:
            return
        patch, box = _blurred(base, (x, y, w, h), pixelate=(kind == "pixelate"))
        if patch is not None:
            painter.setClipRect(QRectF(box))
            painter.drawImage(box.topLeft(), patch)
            painter.setClipping(False)
        return

    if kind == "pen":
        for a, b in zip(shape.points, shape.points[1:]):
            painter.drawLine(QPointF(*a), QPointF(*b))
        return

    if kind == "highlight":
        highlighter = QColor(shape.color)
        highlighter.setAlpha(110)
        wide = QPen(highlighter)
        wide.setWidthF(max(6.0, 18.0 * scale * max(1.0, shape.width / 4.0)))
        wide.setCapStyle(Qt.RoundCap)
        wide.setJoinStyle(Qt.RoundJoin)
        painter.setPen(wide)
        for a, b in zip(shape.points, shape.points[1:]):
            painter.drawLine(QPointF(*a), QPointF(*b))
        return

    if kind == "line":
        painter.drawLine(QPointF(*shape.start), QPointF(*shape.end))
        return

    if kind == "arrow":
        painter.drawLine(QPointF(*shape.start), QPointF(*shape.end))
        painter.setBrush(color)
        _arrow_head(painter, shape.start, shape.end, max(1.0, shape.width * scale))
        painter.setBrush(Qt.NoBrush)
        return

    if kind == "rect":
        painter.drawRect(_qrect(*shape.bounds()))
        return

    if kind == "ellipse":
        painter.drawEllipse(_qr_from_bounds(shape.bounds()))
        return

    if kind == "marker":
        _draw_marker(painter, shape, marker_index, scale)
        return

    if kind == "text":
        _draw_text(painter, shape, scale)


def render(base, shapes: list[Shape], *, scale: float = 1.0):
    """Return a new image: ``base`` plus every annotation, in order.

    ``base`` is never modified. ``scale`` is the ratio between the physical
    capture and the logical size the user drew at (1.0 on a scale-1 output), so
    strokes keep the same apparent thickness on HiDPI.
    """
    from PySide6.QtGui import QImage, QPainter

    image = base.convertToFormat(QImage.Format_ARGB32_Premultiplied) if base.format() != QImage.Format_ARGB32_Premultiplied else base.copy()
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    marker_index = 0
    for shape in shapes:
        if shape.kind == "marker":
            marker_index += 1
        paint_shape(painter, shape, scale=scale, marker_index=marker_index, base=image)

    painter.end()
    return image


def _qr_from_bounds(bounds):
    from PySide6.QtCore import QRectF

    x, y, w, h = bounds
    return QRectF(x, y, w, h)


def render_to_png(base, shapes: list[Shape], *, scale: float = 1.0) -> bytes:
    """Encode the rendered image as PNG bytes (for the clipboard or stdout)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    image = render(base, shapes, scale=scale)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)
