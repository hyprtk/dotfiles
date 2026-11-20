"""The frozen-screen canvas: selection, annotation drawing and the dim veil.

One QQuickPaintedItem does all of it, because the geometry is the part that is
easy to get wrong in QML and easy to test in Python: the image is fitted into
the item, every mouse point is mapped back into image pixels, and the selection
is the crop that gets saved.

The final render comes from :mod:`hyprtk_shot.annotate`, so the preview and the
written file are drawn by the same code.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtQuick import QQuickPaintedItem

from .annotate import Shape, paint_shape, render

HANDLE = 7


class CaptureCanvas(QQuickPaintedItem):
    selChanged = Signal()
    textRequested = Signal(float, float)
    toolChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.setAntialiasing(True)
        self.setSmooth(True)
        self.setOpaquePainting(True)
        self._bridge = None
        self._cache: QImage | None = None
        self._cache_rev = -1
        self._cache_size = (0, 0)
        self._draft: Shape | None = None
        self._text_point: tuple[float, float] | None = None
        self._moving = False
        self._move_origin: tuple[float, float] | None = None
        self._move_rect: QRectF | None = None
        self._selecting = False
        self._select_origin: tuple[float, float] | None = None

    # -- bridge ----------------------------------------------------------
    def _get_bridge(self):
        return self._bridge

    def _set_bridge(self, value):
        self._bridge = value
        if value is not None:
            value.shapesChanged.connect(self._invalidate)
            value.selectionChanged.connect(self._sync)
            value.sessionChanged.connect(self._on_session)
        self._invalidate()

    bridge = Property(QObject, _get_bridge, _set_bridge, notify=toolChanged)

    def _on_session(self) -> None:
        self._draft = None
        self._cache = None
        self._cache_rev = -1
        self._sync()
        self.update()

    def _invalidate(self) -> None:
        self._cache = None
        self._sync()
        self.update()

    # -- geometry --------------------------------------------------------
    def _session(self):
        return self._bridge.session() if self._bridge is not None else None

    def _layout(self):
        session = self._session()
        if session is None or self.width() <= 0 or self.height() <= 0:
            return (1.0, 0.0, 0.0)
        iw, ih = session.width, session.height
        scale = min(self.width() / iw, self.height() / ih)
        ox = (self.width() - iw * scale) / 2.0
        oy = (self.height() - ih * scale) / 2.0
        return (scale, ox, oy)

    def to_image(self, x: float, y: float) -> tuple[float, float]:
        scale, ox, oy = self._layout()
        session = self._session()
        if session is None or scale <= 0:
            return (0.0, 0.0)
        ix = (x - ox) / scale
        iy = (y - oy) / scale
        return (min(max(ix, 0.0), session.width - 1), min(max(iy, 0.0), session.height - 1))

    def to_item(self, x: float, y: float) -> tuple[float, float]:
        scale, ox, oy = self._layout()
        return (ox + x * scale, oy + y * scale)

    @Property(float, notify=selChanged)
    def selX(self) -> float:
        session = self._session()
        if session is None:
            return 0.0
        return self.to_item(session.selection.x(), session.selection.y())[0]

    @Property(float, notify=selChanged)
    def selY(self) -> float:
        session = self._session()
        if session is None:
            return 0.0
        return self.to_item(session.selection.x(), session.selection.y())[1]

    @Property(float, notify=selChanged)
    def selW(self) -> float:
        session = self._session()
        if session is None:
            return 0.0
        scale, _ox, _oy = self._layout()
        return session.selection.width() * scale

    @Property(float, notify=selChanged)
    def selH(self) -> float:
        session = self._session()
        if session is None:
            return 0.0
        scale, _ox, _oy = self._layout()
        return session.selection.height() * scale

    @Property(bool, notify=selChanged)
    def hasSelection(self) -> bool:
        session = self._session()
        if session is None:
            return False
        return session.selection.width() >= 1 and session.selection.height() >= 1

    def _sync(self) -> None:
        self.selChanged.emit()
        self.update()

    # -- painting --------------------------------------------------------
    def _palette_color(self, key: str, fallback: str) -> QColor:
        if self._bridge is None:
            return QColor(fallback)
        value = self._bridge.palette.get(key) if hasattr(self._bridge, "palette") else None
        if isinstance(value, QColor):
            return value
        return QColor(str(value) if value else fallback)

    def paint(self, painter: QPainter) -> None:
        session = self._session()
        if session is None:
            painter.fillRect(self.contentsBoundingRect(), QColor("#000000"))
            return

        scale, ox, oy = self._layout()
        target = QRectF(ox, oy, session.width * scale, session.height * scale)

        rev = int(self._bridge.shapesRev)
        if self._cache is None or self._cache_rev != rev or self._cache_size != (session.width, session.height):
            self._cache = render(session.image, session.shapes, scale=session.ratio)
            self._cache_rev = rev
            self._cache_size = (session.width, session.height)

        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(target, self._cache)

        # Dim everything outside the selection with four rects: the selection
        # keeps the true colours, which is the whole point of the freeze.
        dim = float(self._bridge.config.get("dim", 0.55)) if self._bridge is not None else 0.55
        veil = self._palette_color("veil", "#1e1e2e")
        veil.setAlphaF(max(0.0, min(0.9, dim)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(veil)
        sel = session.selection
        left, top = self.to_item(sel.left(), sel.top())
        right, bottom = self.to_item(sel.right(), sel.bottom())
        painter.drawRect(QRectF(0, 0, self.width(), max(0.0, top)))
        painter.drawRect(QRectF(0, min(self.height(), bottom), self.width(), max(0.0, self.height() - bottom)))
        painter.drawRect(QRectF(0, max(0.0, top), max(0.0, left), max(0.0, bottom - top)))
        painter.drawRect(QRectF(min(self.width(), right), max(0.0, top), max(0.0, self.width() - right), max(0.0, bottom - top)))

        # Selection frame and corner handles.
        accent = self._palette_color("selection", "#22d3ee")
        frame = QPen(accent)
        frame.setWidthF(2.0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(frame)
        painter.drawRect(QRectF(left, top, max(1.0, right - left), max(1.0, bottom - top)))

        if not self._draft and not self._moving:
            painter.setBrush(accent)
            painter.setPen(Qt.NoPen)
            for hx, hy in ((left, top), (right, top), (left, bottom), (right, bottom)):
                painter.drawRect(QRectF(hx - HANDLE / 2, hy - HANDLE / 2, HANDLE, HANDLE))
            painter.setBrush(Qt.NoBrush)

        # In-progress annotation, drawn by the same function as the final one.
        if self._draft is not None:
            painter.save()
            painter.setClipRect(QRectF(left, top, max(1.0, right - left), max(1.0, bottom - top)))
            paint_shape(painter, self._draft, scale=scale, base=self._cache)
            painter.restore()

    # -- interaction -----------------------------------------------------
    def _clamp_to_selection(self, x: float, y: float) -> tuple[float, float]:
        session = self._session()
        rect = session.selection
        return (min(max(x, rect.left()), rect.right()),
                min(max(y, rect.top()), rect.bottom()))

    def mousePressEvent(self, event) -> None:
        session = self._session()
        if session is None:
            return
        if event.button() == Qt.RightButton:
            if self._draft is not None:
                self._draft = None
                self.update()
            else:
                self._bridge.selectAll()
            return

        x, y = self.to_image(event.position().x(), event.position().y())
        tool = str(self._bridge.tool)
        rect = session.selection

        if tool == "cursor":
            inside = rect.contains(QPointF(x, y))
            if inside:
                self._moving = True
                self._move_origin = (x, y)
                self._move_rect = QRectF(rect)
            else:
                self._selecting = True
                self._select_origin = (x, y)
                self._bridge.setSelection(x, y, 1, 1)
            return

        if not rect.contains(QPointF(x, y)):
            return
        self._draft = Shape(kind=tool, points=[(x, y)],
                            color=str(self._bridge.color),
                            width=float(self._bridge.stroke))
        if tool == "text":
            item_x, item_y = self.to_item(x, y)
            self._text_point = (x, y)
            self._draft = None
            self.textRequested.emit(item_x + 6, item_y + 14)
            return
        self.update()

    def mouseMoveEvent(self, event) -> None:
        session = self._session()
        if session is None:
            return
        x, y = self.to_image(event.position().x(), event.position().y())

        if self._selecting and self._select_origin is not None:
            ox, oy = self._select_origin
            self._bridge.setSelection(ox, oy, x - ox, y - oy)
            return

        if self._moving and self._move_origin is not None and self._move_rect is not None:
            dx = x - self._move_origin[0]
            dy = y - self._move_origin[1]
            rect = QRectF(self._move_rect).translated(dx, dy)
            # Keep the selection inside the image instead of letting it slide
            # off and producing an empty crop.
            if rect.left() < 0:
                rect.moveLeft(0)
            if rect.top() < 0:
                rect.moveTop(0)
            if rect.right() > session.width:
                rect.moveRight(session.width)
            if rect.bottom() > session.height:
                rect.moveBottom(session.height)
            self._bridge.setSelection(rect.x(), rect.y(), rect.width(), rect.height())
            return

        if self._draft is not None:
            if self._draft.kind in ("pen", "highlight"):
                last = self._draft.points[-1]
                if abs(x - last[0]) + abs(y - last[1]) > 1.2:
                    cx, cy = self._clamp_to_selection(x, y)
                    self._draft.add(cx, cy)
            else:
                cx, cy = self._clamp_to_selection(x, y)
                self._draft.points = [self._draft.points[0], (cx, cy)]
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        session = self._session()
        if session is None:
            return
        if self._selecting:
            self._selecting = False
            self._select_origin = None
            if session.selection.width() < 4 or session.selection.height() < 4:
                self._bridge.selectAll()
            return
        if self._moving:
            self._moving = False
            self._move_origin = None
            self._move_rect = None
            return
        if self._draft is not None:
            draft, self._draft = self._draft, None
            if draft.kind in ("pen", "highlight") and len(draft.points) < 2:
                self.update()
                return
            if draft.kind in ("line", "arrow", "rect", "ellipse") and len(draft.points) < 2:
                self.update()
                return
            self._bridge.addShapeObject(draft)
            self.update()

    def commitText(self, text: str) -> None:
        if not text.strip() or self._text_point is None or self._bridge is None:
            self._text_point = None
            return
        x, y = self._text_point
        self._text_point = None
        shape = Shape(kind="text", points=[(x, y)],
                      color=str(self._bridge.color),
                      width=float(self._bridge.stroke),
                      text=text)
        self._bridge.addShapeObject(shape)

    # -- QML helpers -----------------------------------------------------
    def hoverMoveEvent(self, event) -> None:
        if self._bridge is None:
            return
        if str(self._bridge.tool) != "cursor":
            self.setCursor(Qt.CrossCursor)
            return
        session = self._session()
        if session is None:
            return
        x, y = self.to_image(event.position().x(), event.position().y())
        self.setCursor(Qt.OpenHandCursor if session.selection.contains(QPointF(x, y)) else Qt.CrossCursor)
