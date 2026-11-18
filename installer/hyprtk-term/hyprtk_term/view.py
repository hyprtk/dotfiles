"""The painted terminal surface and all the user-facing behaviour.

Chrome (tabs, settings, toasts) is QML. Everything that needs to understand a
cell -- painting, selection, mouse reporting, key encoding -- lives here, on a
``QQuickPaintedItem``. Painting from Python was measured at ~3 ms for a full
80x24 grid, and the row-run cache means an idle screen costs nothing.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QPointF, QRectF, Property, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPainter, QPen
from PySide6.QtQuick import QQuickItem, QQuickPaintedItem

from . import boxdraw
from . import palette as palette_mod
from . import search as search_mod
from . import select as select_mod
from . import settings as settings_mod
from .terminal import Terminal
from .vt import (
    A_BLINK, A_BOLD, A_ITALIC, A_SMALL, A_STRIKE, A_UNDERLINE,
    BASELINE_SHIFT, UNDERLINE_STYLE_SHIFT, modifier_for,
)
from .vtcapi import KEY, MOUSE, CURSOR_BAR, CURSOR_UNDERLINE

KEYMAP = {
    Qt.Key_Return: KEY["ENTER"],
    Qt.Key_Enter: KEY["ENTER"],
    Qt.Key_Tab: KEY["TAB"],
    Qt.Key_Backtab: KEY["TAB"],
    Qt.Key_Backspace: KEY["BACKSPACE"],
    Qt.Key_Escape: KEY["ESCAPE"],
    Qt.Key_Up: KEY["UP"],
    Qt.Key_Down: KEY["DOWN"],
    Qt.Key_Left: KEY["LEFT"],
    Qt.Key_Right: KEY["RIGHT"],
    Qt.Key_Insert: KEY["INS"],
    Qt.Key_Delete: KEY["DEL"],
    Qt.Key_Home: KEY["HOME"],
    Qt.Key_End: KEY["END"],
    Qt.Key_PageUp: KEY["PAGEUP"],
    Qt.Key_PageDown: KEY["PAGEDOWN"],
}
for _n in range(1, 13):
    KEYMAP[getattr(Qt, f"Key_F{_n}")] = KEY["FUNCTION_0"] + _n


class _Canvas:
    """Adapter that lets :mod:`boxdraw` paint through a ``QPainter``.

    Rectangles are drawn without antialiasing on purpose: adjacent block
    elements must share an edge exactly, and a softened edge would leave a
    visible seam between two cells that should look like one shape.
    """

    __slots__ = ("_painter", "_colour")

    def __init__(self, painter: QPainter):
        self._painter = painter
        self._colour = QColor("#ffffff")

    def set_colour(self, colour: QColor) -> None:
        self._colour = colour

    def fill_rect(self, x: float, y: float, w: float, h: float,
                  alpha: float = 1.0) -> None:
        if w <= 0 or h <= 0:
            return
        colour = self._colour
        if alpha < 1.0:
            colour = QColor(colour)
            colour.setAlphaF(max(0.0, min(1.0, alpha)))
        self._painter.fillRect(QRectF(x, y, w, h), colour)

    def line(self, x0: float, y0: float, x1: float, y1: float,
             thickness: float) -> None:
        painter = self._painter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(self._colour, thickness)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        painter.restore()

    def arc(self, cx: float, cy: float, radius: float, start: float,
            span: float, thickness: float) -> None:
        painter = self._painter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(self._colour, thickness)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius),
                        int(start * 16), int(span * 16))
        painter.restore()



class TerminalView(QQuickPaintedItem):
    _startup_argv: list[str] | None = None
    _startup_cwd: str | None = None
    titleChanged = Signal()
    stateChanged = Signal()
    bell = Signal()
    exited = Signal(int)
    contextMenuRequested = Signal(float, float)
    selectionChanged = Signal()
    searchChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QQuickItem.ItemAcceptsInputMethod, True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.MiddleButton | Qt.RightButton)
        self.setAcceptHoverEvents(True)
        self.setRenderTarget(QQuickPaintedItem.Image)

        # The saved settings, not the dataclass defaults: the grid is derived
        # from the font, and the shell is spawned with it. Starting from the
        # defaults means every launch spawns at the wrong size and then resizes.
        self._cfg = settings_mod.Settings.load()
        self._colors = palette_mod.resolve()
        self._term: Terminal | None = None
        self._title = ""
        self._exited = False
        self._exit_status = 0
        self._scroll = 0
        self._cw = 8.0
        self._ch = 16.0
        self._font = QFont(self._cfg.font_family)
        self._font_cache: dict[tuple, QFont] = {}
        self._cursor_on = True
        self._cursor_row = -1
        self._sel = None                # (line0, col0, line1, col1) absolute
        self._sel_anchor = None
        self._selecting = False
        self._matches: list = []
        self._match_index = -1
        self._search_case = False
        self._search_regex = False
        self._search_query = ""
        self._default_argv: list[str] | None = None
        self._cwd: str | None = None
        self._font_size = self._cfg.font_size
        self._opacity = self._cfg.opacity
        self._bg = palette_mod.hex_to_int(self._colors.get("background", "#1e1e2e"), 0x1E1E2E)
        self._fg = palette_mod.hex_to_int(self._colors.get("foreground", "#e5e7eb"), 0xE5E7EB)
        self._accent = palette_mod.hex_to_int(self._colors.get("cursor", "#c084fc"), 0xC084FC)
        self._sel_color = palette_mod.hex_to_int(self._colors.get("selection", "#22d3ee"), 0x22D3EE)

        self._paint_timer = QTimer(self)
        self._paint_timer.setSingleShot(True)
        self._paint_timer.setInterval(8)
        self._paint_timer.timeout.connect(self.update)

        # Grid resizes are coalesced: see _resize_grid().
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(40)
        self._resize_timer.timeout.connect(self._apply_resize)

        # The shell is not spawned until the window has stopped being laid out.
        self._settle_timer = QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.setInterval(80)
        self._settle_timer.timeout.connect(self.spawn)

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(530)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start()

        self._apply_palette()
        self._metrics()

        # QQuickItem::geometryChanged is a C++ virtual that PySide does not
        # dispatch to Python overrides; the change signals do fire.
        self.widthChanged.connect(self._on_size_changed)
        self.heightChanged.connect(self._on_size_changed)

    def _on_size_changed(self) -> None:
        if self._term is None:
            # Still being laid out. Spawning the shell into a size that is
            # about to change means resizing it immediately, and a resize that
            # lands while the shell draws its first prompt can strand zsh's
            # partial-line marker on screen. Wait for the size to hold still.
            self._settle_timer.start()
            return
        self._resize_grid()

    # ------------------------------------------------------------ properties --

    def _get_title(self) -> str:
        return self._title

    title = Property(str, _get_title, notify=titleChanged)

    def _get_cols(self) -> int:
        return self._term.vt.cols if self._term else 0

    cols = Property(int, _get_cols, notify=stateChanged)

    def _get_rows(self) -> int:
        return self._term.vt.rows if self._term else 0

    rows = Property(int, _get_rows, notify=stateChanged)

    def _get_exited(self) -> bool:
        return self._exited

    exitedFlag = Property(bool, _get_exited, notify=stateChanged)

    def _get_at_bottom(self) -> bool:
        return self._scroll == 0

    atBottom = Property(bool, _get_at_bottom, notify=stateChanged)

    def _get_has_selection(self) -> bool:
        return self._sel is not None

    hasSelection = Property(bool, _get_has_selection, notify=selectionChanged)

    def _get_match_count(self) -> int:
        return len(self._matches)

    matchCount = Property(int, _get_match_count, notify=searchChanged)

    def _get_match_index(self) -> int:
        return self._match_index + 1 if self._matches else 0

    matchIndex = Property(int, _get_match_index, notify=searchChanged)

    # ------------------------------------------------------------- lifecycle --

    @classmethod
    def set_default_startup(cls, argv: list[str] | None = None,
                            cwd: str | None = None) -> None:
        """Command line for the first window (``hyprtk-term -e cmd``, ``-d dir``)."""
        cls._startup_argv = list(argv) if argv else None
        cls._startup_cwd = cwd

    def set_startup(self, argv: list[str] | None = None, cwd: str | None = None) -> None:
        """Called from QML before the child is spawned."""
        self._default_argv = argv
        self._cwd = cwd

    def componentComplete(self) -> None:            # noqa: N802 (Qt override)
        super().componentComplete()
        # Not spawned yet: see _on_size_changed().
        self._settle_timer.start()

    def spawn(self) -> None:
        if self._term is not None:
            return
        cols, rows = self._grid()
        self._term = Terminal(
            rows, cols,
            shell=self._cfg.shell or None,
            command=self._default_argv or TerminalView._startup_argv,
            cwd=self._cwd or TerminalView._startup_cwd or os.path.expanduser("~"),
            scrollback=self._cfg.scrollback,
            parent=self,
        )
        self._term.vt.set_theme(self._fg, self._bg, self._ansi())
        self._term.changed.connect(self._schedule_paint)
        self._term.titleChanged.connect(self._on_title)
        self._term.bell.connect(self._on_bell)
        self._term.exited.connect(self._on_exit)
        self._term.bind_clipboard(self._clipboard_get, self._clipboard_put)
        self._apply_resize()
        self._schedule_paint()
        self.stateChanged.emit()

    def _ansi(self) -> list[int]:
        return [palette_mod.hex_to_int(value, 0xFFFFFF)
                for value in (self._colors.get("ansi") or [])]

    def _apply_palette(self) -> None:
        self._bg = palette_mod.hex_to_int(self._colors.get("background", "#1e1e2e"), 0x1E1E2E)
        self._fg = palette_mod.hex_to_int(self._colors.get("foreground", "#e5e7eb"), 0xE5E7EB)
        self._accent = palette_mod.hex_to_int(self._colors.get("cursor", "#c084fc"), 0xC084FC)
        self._sel_color = palette_mod.hex_to_int(self._colors.get("selection", "#22d3ee"), 0x22D3EE)

    @Slot("QVariant", "QVariant")
    def applySettings(self, cfg, colors) -> None:   # noqa: N802
        """Called from QML with ``Bridge.config`` and ``Bridge.palette``."""
        new_cfg = settings_mod.Settings()
        if cfg is not None:
            try:
                new_cfg.update(dict(cfg))
            except (TypeError, ValueError):
                new_cfg = settings_mod.Settings()
        self._cfg = new_cfg
        self._font_size = new_cfg.font_size
        self._opacity = settings_mod.clamp_opacity(new_cfg.opacity)
        if colors is not None:
            try:
                self._colors = dict(colors)
            except (TypeError, ValueError):
                pass
        self._apply_palette()
        self._metrics()
        if self._term:
            self._term.vt.set_theme(self._fg, self._bg, self._ansi())
            self._term.vt.set_scrollback(self._cfg.scrollback)
        self._resize_grid()
        self.update()

    # -------------------------------------------------------------- geometry --

    def _metrics(self) -> None:
        font = QFont(self._cfg.font_family)
        if font.family() != self._cfg.font_family:
            font = QFont("monospace")
        font.setPointSizeF(max(4.0, float(self._font_size)))
        font.setHintingPreference(QFont.PreferFullHinting)
        font.setFixedPitch(True)
        self._font = font
        self._font_cache.clear()
        fm = QFontMetricsF(font)
        self._cw = max(1.0, fm.horizontalAdvance("M"))
        self._font_height = fm.height()
        self._ch = max(1.0, round(self._font_height * max(0.8, float(self._cfg.line_height))))
        self._ascent = fm.ascent()

    def _grid(self) -> tuple[int, int]:
        pad = max(0, int(self._cfg.padding))
        avail_w = max(1.0, self.width() - 2 * pad)
        avail_h = max(1.0, self.height() - 2 * pad)
        cols = max(1, int(avail_w // self._cw))
        rows = max(1, int(avail_h // self._ch))
        return cols, rows

    def _resize_grid(self) -> None:
        """Coalesce layout churn before any of it reaches the shell.

        A window is laid out more than once before it settles -- the compositor
        tiles it after the QML default size, so 940 becomes 1917 and then 1910.
        Every intermediate width is a SIGWINCH, and a resize that lands while
        the shell is drawing its prompt leaves the shell believing a width the
        grid no longer has: zsh then fills its partial-line marker with more
        spaces than fit, the marker's own erase wraps to the next line, and a
        stray ``%`` strands above the prompt. Only the settled size is worth
        telling the shell about, so the timer absorbs the rest.
        """
        if not self._term:
            return
        if not self._resize_timer.isActive():
            self._resize_timer.start()

    def _apply_resize(self) -> None:
        if not self._term:
            return
        cols, rows = self._grid()
        if self._term.resize(rows, cols):
            self._matches = []
            self._match_index = -1
            self.searchChanged.emit()
        self._scroll = min(self._scroll, self._term.vt.scrollback_len)

    def geometryChanged(self, new, old) -> None:    # noqa: N802
        super().geometryChanged(new, old)
        self._on_size_changed()

    # --------------------------------------------------------------- painting --

    def _schedule_paint(self) -> None:
        if not self._paint_timer.isActive():
            self._paint_timer.start()

    def _font_for(self, flags: int) -> QFont:
        bold = bool(flags & A_BOLD)
        italic = bool(flags & A_ITALIC)
        key = (bold, italic)
        font = self._font_cache.get(key)
        if font is None:
            font = QFont(self._font)
            font.setBold(bold)
            font.setItalic(italic)
            self._font_cache[key] = font
        return font

    def paint(self, painter: QPainter) -> None:
        if not self._term:
            return
        vt = self._term.vt
        pad = max(0, int(self._cfg.padding))
        bg = QColor(self._bg)
        if self._opacity < 1.0:
            bg.setAlphaF(max(0.0, min(1.0, self._opacity)))
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), bg)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setClipRect(QRectF(pad, pad, vt.cols * self._cw, vt.rows * self._ch))

        base_bg = self._bg
        top = self._top_line()
        blink_on = self._cursor_on or not self._blink_enabled()
        cell_w, cell_h = self._cw, self._ch
        canvas = _Canvas(painter)

        for row in range(vt.rows):
            line = top + row
            runs = self._runs_for(line)
            y = pad + row * cell_h

            # Pass 1: run backgrounds. Selection and search tints must land on
            # top of these but underneath the glyphs, so the row is drawn in
            # three passes rather than one.
            if runs:
                x = pad
                for run in runs:
                    width = run.cols * cell_w
                    if run.bg != base_bg:
                        painter.fillRect(QRectF(x, y, width, cell_h), QColor(run.bg))
                    x += width

            self._fill_selection_row(painter, line, y, pad)
            self._fill_matches_row(painter, line, y, pad)

            # Pass 2: the glyphs themselves.
            if not runs:
                continue
            x = pad
            for run in runs:
                width = run.cols * cell_w
                if run.flags & A_BLINK and not blink_on:
                    x += width
                    continue
                fg = QColor(run.fg)
                baseline = y + max(0.0, (cell_h - self._font_height) / 2) + self._ascent
                painted = False
                if len(run.text) == 1:
                    canvas.set_colour(fg)
                    painted = boxdraw.draw(canvas, run.text, x, y, width, cell_h)
                if not painted:
                    painter.setPen(fg)
                    painter.setFont(self._font_for(run.flags))
                    painter.drawText(QPointF(x, baseline), run.text)
                if run.flags & A_UNDERLINE:
                    style = (run.flags >> UNDERLINE_STYLE_SHIFT) & 0b11
                    pen = QPen(fg, 1.0)
                    if style == 3:
                        pen.setStyle(Qt.DotLine)
                    painter.setPen(pen)
                    uy = baseline + 1.5
                    painter.drawLine(QPointF(x, uy), QPointF(x + width, uy))
                    if style == 2:
                        painter.drawLine(QPointF(x, uy + 1.5), QPointF(x + width, uy + 1.5))
                if run.flags & A_STRIKE:
                    painter.setPen(QPen(fg, 1.0))
                    sy = y + cell_h / 2
                    painter.drawLine(QPointF(x, sy), QPointF(x + width, sy))
                x += width

        self._paint_cursor(painter, pad, top)

    def _runs_for(self, line: int):
        vt = self._term.vt
        if line < 0:
            return []
        if line < vt.scrollback_len:
            return vt.scrollback_runs(line)
        row = line - vt.scrollback_len
        if row >= vt.rows:
            return []
        return vt.row_runs(row)

    def _fill_selection_row(self, painter: QPainter, line: int, y: float, pad: int) -> None:
        if not self._sel:
            return
        l0, c0, l1, c1 = self._sel
        if not (l0 <= line <= l1):
            return
        start = c0 if line == l0 else 0
        end = c1 if line == l1 else self._term.vt.cols
        if end <= start:
            return
        colour = QColor(self._sel_color)
        colour.setAlpha(110)
        painter.fillRect(QRectF(pad + start * self._cw, y,
                                (end - start) * self._cw, self._ch), colour)

    def _fill_matches_row(self, painter: QPainter, line: int, y: float, pad: int) -> None:
        if not self._matches or not self._term:
            return
        base = palette_mod.hex_to_int(self._colors.get("search", "#f9e2af"), 0xF9E2AF)
        for index, match in enumerate(self._matches):
            if match.line != line:
                continue
            colour = QColor(base)
            colour.setAlpha(170 if index == self._match_index else 60)
            painter.fillRect(
                QRectF(pad + match.start * self._cw, y,
                       max(1, match.end - match.start) * self._cw, self._ch),
                colour)

    def _paint_cursor(self, painter: QPainter, pad: int, top: int) -> None:
        vt = self._term.vt
        cursor = vt.cursor
        if not cursor.visible or self._scroll or not self.isVisible():
            return
        if self._blink_enabled() and not self._cursor_on:
            return
        row = cursor.row
        col = cursor.col
        if not (0 <= row < vt.rows and 0 <= col < vt.cols):
            return
        x = pad + col * self._cw
        y = pad + row * self._ch
        colour = QColor(self._accent)
        if cursor.shape == CURSOR_UNDERLINE:
            painter.fillRect(QRectF(x, y + self._ch - 2, self._cw, 2), colour)
        elif cursor.shape == CURSOR_BAR:
            painter.fillRect(QRectF(x, y, 2, self._ch), colour)
        else:
            colour.setAlpha(110)
            painter.fillRect(QRectF(x, y, self._cw, self._ch), colour)

    def _blink_enabled(self) -> bool:
        return bool(self._cfg.cursor_blink) and bool(self._term and self._term.vt.cursor.blink)

    def _blink(self) -> None:
        if not self._term or not self.isVisible():
            return
        if not self._blink_enabled():
            if not self._cursor_on:
                self._cursor_on = True
                self._schedule_paint()
            return
        self._cursor_on = not self._cursor_on
        self._schedule_paint()

    def _top_line(self) -> int:
        vt = self._term.vt
        top = vt.scrollback_len - self._scroll
        return max(0, min(top, vt.scrollback_len))

    # ------------------------------------------------------------------ input --

    def keyPressEvent(self, event) -> None:         # noqa: N802
        if not self._term:
            return
        data = self._encode(event)
        if data:
            if self._scroll:
                self._scroll = 0
                self._schedule_paint()
            self._term.write(data)
        event.accept()

    def _encode(self, event) -> bytes:
        vt = self._term.vt
        mods = modifier_for(
            bool(event.modifiers() & Qt.ShiftModifier),
            bool(event.modifiers() & Qt.AltModifier),
            bool(event.modifiers() & Qt.ControlModifier),
        )
        code = KEYMAP.get(event.key())
        if code is not None:
            if event.key() == Qt.Key_Backtab:
                mods |= 1
            return vt.key(code, mods)
        text = event.text()
        if not text and 0x20 <= event.key() < 0x7F:
            text = chr(event.key()).lower() if event.modifiers() & Qt.ControlModifier else chr(event.key())
        if not text:
            return b""
        out = bytearray()
        for ch in text:
            cp = ord(ch)
            if cp < 0x20 or cp == 0x7F:
                out += vt.unichar(cp, 0)
            else:
                out += vt.unichar(cp, mods)
        return bytes(out)

    def inputMethodEvent(self, event) -> None:      # noqa: N802
        if not self._term:
            return
        text = event.commitString()
        if text:
            self._term.send(text)
        event.accept()

    def focusInEvent(self, event) -> None:          # noqa: N802
        super().focusInEvent(event)
        if self._term:
            self._term.write(self._term.vt.focus(True))
        self._schedule_paint()

    def focusOutEvent(self, event) -> None:         # noqa: N802
        super().focusOutEvent(event)
        if self._term:
            self._term.write(self._term.vt.focus(False))
        self._schedule_paint()

    # ------------------------------------------------------------------ mouse --

    def _cell_at(self, point: QPointF) -> tuple[int, int]:
        vt = self._term.vt
        pad = max(0, int(self._cfg.padding))
        col = int((point.x() - pad) // self._cw)
        row = int((point.y() - pad) // self._ch)
        col = max(0, min(col, vt.cols - 1))
        row = max(0, min(row, vt.rows - 1))
        return self._top_line() + row, col

    def _reports_mouse(self, motion: bool = False) -> bool:
        mode = self._term.vt.mouse_mode if self._term else MOUSE["NONE"]
        return mode == MOUSE["DRAG"] if motion else mode != MOUSE["NONE"]

    def mousePressEvent(self, event) -> None:       # noqa: N802
        if not self._term:
            return
        self.forceActiveFocus()
        mods = modifier_for(bool(event.modifiers() & Qt.ShiftModifier),
                            bool(event.modifiers() & Qt.AltModifier),
                            bool(event.modifiers() & Qt.ControlModifier))
        if self._reports_mouse() and not (event.modifiers() & Qt.ShiftModifier):
            button = {Qt.LeftButton: 1, Qt.MiddleButton: 2, Qt.RightButton: 3}.get(event.button(), 0)
            line, col = self._cell_at(event.position())
            row = line - self._term.vt.scrollback_len
            self._term.write(self._term.vt.mouse_move(row, col, mods))
            self._term.write(self._term.vt.mouse_button(button, True, mods))
            event.accept()
            return
        if event.button() == Qt.RightButton:
            self.contextMenuRequested.emit(event.position().x(), event.position().y())
            event.accept()
            return
        if event.button() == Qt.MiddleButton:
            self.paste()
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            line, col = self._cell_at(event.position())
            if event.modifiers() & Qt.ShiftModifier and self._sel:
                self._sel = (self._sel[0], self._sel[1], line, col)
                self._normalize_selection()
            else:
                self._sel_anchor = (line, col)
                self._sel = None
                self._selecting = True
            self.selectionChanged.emit()
            self._schedule_paint()
            event.accept()

    def mouseMoveEvent(self, event) -> None:        # noqa: N802
        if not self._term:
            return
        if self._selecting and (event.buttons() & Qt.LeftButton):
            line, col = self._cell_at(event.position())
            if self._sel_anchor:
                self._sel = (self._sel_anchor[0], self._sel_anchor[1], line, col)
                self._normalize_selection()
                self.selectionChanged.emit()
                self._schedule_paint()
            event.accept()
            return
        if self._reports_mouse(motion=True):
            mods = modifier_for(bool(event.modifiers() & Qt.ShiftModifier),
                                bool(event.modifiers() & Qt.AltModifier),
                                bool(event.modifiers() & Qt.ControlModifier))
            line, col = self._cell_at(event.position())
            row = line - self._term.vt.scrollback_len
            self._term.write(self._term.vt.mouse_move(row, col, mods))
            event.accept()

    def mouseReleaseEvent(self, event) -> None:     # noqa: N802
        if not self._term:
            return
        if self._reports_mouse() and not (event.modifiers() & Qt.ShiftModifier):
            mods = modifier_for(bool(event.modifiers() & Qt.ShiftModifier),
                                bool(event.modifiers() & Qt.AltModifier),
                                bool(event.modifiers() & Qt.ControlModifier))
            button = {Qt.LeftButton: 1, Qt.MiddleButton: 2, Qt.RightButton: 3}.get(event.button(), 0)
            line, col = self._cell_at(event.position())
            row = line - self._term.vt.scrollback_len
            self._term.write(self._term.vt.mouse_move(row, col, mods))
            self._term.write(self._term.vt.mouse_button(button, False, mods))
            event.accept()
            return
        self._selecting = False
        if event.button() == Qt.LeftButton and self._sel and self._cfg.copy_on_select:
            self.copy()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if not self._term or self._reports_mouse():
            return
        line, col = self._cell_at(event.position())
        self._sel = self._word_at(line, col)
        self._normalize_selection()
        self.selectionChanged.emit()
        self._schedule_paint()
        event.accept()

    def wheelEvent(self, event) -> None:            # noqa: N802
        if not self._term:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        if self._reports_mouse():
            mods = modifier_for(bool(event.modifiers() & Qt.ShiftModifier),
                                bool(event.modifiers() & Qt.AltModifier),
                                bool(event.modifiers() & Qt.ControlModifier))
            button = 4 if delta > 0 else 5
            self._term.write(self._term.vt.mouse_button(button, True, mods))
            self._term.write(self._term.vt.mouse_button(button, False, mods))
            event.accept()
            return
        step = 3 if event.modifiers() & Qt.ShiftModifier else 1
        self.scrollLines(step if delta > 0 else -step)
        event.accept()

    def hoverMoveEvent(self, event) -> None:        # noqa: N802
        cursor = Qt.IBeamCursor if not self._reports_mouse() else Qt.ArrowCursor
        if self.cursor().shape() != cursor:
            self.setCursor(cursor)
        super().hoverMoveEvent(event)

    # ----------------------------------------------------------------- search --

    @Slot(str, bool, bool, result=int)
    def runSearch(self, query: str, case_sensitive: bool, regex: bool) -> int:  # noqa: N802
        self._search_query = query or ""
        self._search_case = bool(case_sensitive)
        self._search_regex = bool(regex)
        if not self._term or not self._search_query:
            self._matches = []
            self._match_index = -1
            self.searchChanged.emit()
            self._schedule_paint()
            return 0
        self._matches = search_mod.find_matches(
            self._term.vt, self._search_query, self._search_case, self._search_regex)
        self._match_index = 0 if self._matches else -1
        if self._matches:
            self._jump_to_match(0)
        self.searchChanged.emit()
        self._schedule_paint()
        return len(self._matches)

    @Slot(result=bool)
    def searchNext(self) -> bool:                   # noqa: N802
        return self._step_match(1)

    @Slot(result=bool)
    def searchPrevious(self) -> bool:               # noqa: N802
        return self._step_match(-1)

    def _step_match(self, direction: int) -> bool:
        if not self._matches:
            return False
        self._match_index = search_mod.line_of_next(self._matches, self._match_index, direction)
        self._jump_to_match(self._match_index)
        self.searchChanged.emit()
        self._schedule_paint()
        return True

    def _jump_to_match(self, index: int) -> None:
        if not (0 <= index < len(self._matches)) or not self._term:
            return
        vt = self._term.vt
        match = self._matches[index]
        self._scroll = search_mod.scroll_for_line(match.line, vt.scrollback_len, vt.rows)
        self.stateChanged.emit()

    @Slot()
    def clearSearch(self) -> None:                  # noqa: N802
        self._matches = []
        self._match_index = -1
        self._search_query = ""
        self.searchChanged.emit()
        self._schedule_paint()

    @Slot(result=str)
    def searchText(self) -> str:                    # noqa: N802
        return self._search_query

    # -------------------------------------------------------------- selection --

    def _normalize_selection(self) -> None:
        if self._sel:
            self._sel = select_mod.normalize(self._sel)

    def _word_at(self, line: int, col: int) -> tuple[int, int, int, int]:
        cells = self._term.vt.line_cells(line)
        start, end = select_mod.word_bounds(cells, col)
        return (line, start, line, end)

    def selection_text(self) -> str:
        if not self._term:
            return ""
        return select_mod.selection_text(self._term.vt, self._sel)

    # ------------------------------------------------------------------ slots --

    def copy(self) -> None:
        text = self.selection_text()
        if text:
            self._clipboard_put(text, False)

    def paste(self) -> None:
        if not self._term:
            return
        text = self._clipboard_get()
        if text:
            self._term.send(text)
            self._scroll = 0
            self._schedule_paint()

    def selectAll(self) -> None:                    # noqa: N802
        if not self._term:
            return
        vt = self._term.vt
        last = vt.scrollback_len + vt.rows - 1
        self._sel = (0, 0, last, vt.cols)
        self.selectionChanged.emit()
        self._schedule_paint()

    def clearSelection(self) -> None:               # noqa: N802
        self._sel = None
        self._sel_anchor = None
        self.selectionChanged.emit()
        self._schedule_paint()

    def clearScrollback(self) -> None:              # noqa: N802
        if self._term:
            self._term.vt.clear_scrollback()
            self._scroll = 0
            self._schedule_paint()

    @Slot(int)
    def scrollLines(self, delta: int) -> None:      # noqa: N802
        if not self._term:
            return
        limit = self._term.vt.scrollback_len
        self._scroll = max(0, min(limit, self._scroll + int(delta)))
        self.stateChanged.emit()
        self._schedule_paint()

    @Slot(result=str)
    def selectionText(self) -> str:                 # noqa: N802
        return self.selection_text()

    def scrollToBottom(self) -> None:               # noqa: N802
        self._scroll = 0
        self.stateChanged.emit()
        self._schedule_paint()

    def zoom(self, delta: float) -> None:           # noqa: N802
        self._font_size = settings_mod.clamp_font_size(self._font_size + float(delta))
        self._metrics()
        self._resize_grid()
        self._schedule_paint()

    def resetZoom(self) -> None:                    # noqa: N802
        self._font_size = settings_mod.clamp_font_size(self._cfg.font_size)
        self._metrics()
        self._resize_grid()
        self._schedule_paint()

    def sendText(self, text: str) -> None:          # noqa: N802
        if self._term and text:
            self._term.send(text)

    def focusTerminal(self) -> None:                # noqa: N802
        self.forceActiveFocus()

    def kill(self) -> None:
        if self._term:
            self._term.close()
            self._term = None

    # -------------------------------------------------------------- clipboard --

    def _clipboard_get(self) -> str:
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text()
        if not text:
            mode = clipboard.Selection if hasattr(clipboard, "Selection") else None
            if mode is not None:
                text = clipboard.text(mode)
        return text or ""

    def _clipboard_put(self, text: str, primary: bool) -> None:
        clipboard = QGuiApplication.clipboard()
        if hasattr(clipboard, "Selection"):
            clipboard.setText(text, clipboard.Selection if primary else clipboard.Clipboard)
        else:  # pragma: no cover - Qt < 6.5
            clipboard.setText(text)

    # --------------------------------------------------------------- signals --

    def _on_title(self, title: str) -> None:
        self._title = title
        self.titleChanged.emit()

    def _on_bell(self) -> None:
        self.bell.emit()

    def _on_exit(self, status: int) -> None:
        self._exited = True
        self._exit_status = status
        self.stateChanged.emit()
        self.exited.emit(status)

    # exposed for tests
    @property
    def terminal(self) -> Terminal | None:
        return self._term

    @property
    def cell_size(self) -> tuple[float, float]:
        return self._cw, self._ch

    @property
    def scroll_offset(self) -> int:
        return self._scroll
