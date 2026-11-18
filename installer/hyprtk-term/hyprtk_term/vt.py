"""The VT core: libvterm plus the pieces a renderer needs.

:class:`VTerminal` owns one libvterm instance and exposes it in the shape the
rest of the app wants:

* ``feed(bytes)`` -- write PTY output into the parser;
* ``row_runs(row)`` -- the row as styled runs, cached per row and invalidated by
  libvterm's damage callback;
* a scrollback ring that stores raw ``VTermScreenCell`` bytes, so the reverse
  scroll can hand libvterm its own cells back losslessly;
* the key / mouse encoders, so no escape-sequence table lives in this project.

No Qt lives here. That is what makes the whole module testable headlessly.
"""

from __future__ import annotations

import ctypes as C
from collections import deque
from dataclasses import dataclass

from . import boxdraw
from . import vtcapi as V
from .vtcapi import ATTR, COLOR_DEFAULT_MASK, COLOR_TYPE_MASK, KEY, MOD

# Code points painted as geometry (boxdraw.py) instead of by the font.
BOX_FIRST, BOX_LAST = boxdraw.FIRST, boxdraw.LAST

# Our own attribute bits (libvterm's bitfield order is awkward to test against).
A_BOLD = 1 << 0
A_UNDERLINE = 1 << 1
A_ITALIC = 1 << 2
A_BLINK = 1 << 3
A_REVERSE = 1 << 4
A_CONCEAL = 1 << 5
A_STRIKE = 1 << 6
A_SMALL = 1 << 7
UNDERLINE_STYLE_SHIFT = 8          # 0 off, 1 single, 2 double, 3 curly
BASELINE_SHIFT = 10                # 0 normal, 1 raise, 2 lower

DEFAULT_ANSI = (
    0x45475A, 0xF38BA8, 0xA6E3A1, 0xF9E2AF,
    0x89B4FA, 0xC084FC, 0x22D3EE, 0xBAC2DE,
    0x585B70, 0xF38BA8, 0xA6E3A1, 0xF9E2AF,
    0x89B4FA, 0xC084FC, 0x22D3EE, 0xA6ADCA,
)


@dataclass(frozen=True, slots=True)
class Run:
    """A horizontal span of cells that share one style."""
    text: str
    cols: int
    fg: int          # 0xRRGGBB
    bg: int          # 0xRRGGBB
    flags: int       # A_* bits above


@dataclass(frozen=True, slots=True)
class Cursor:
    row: int
    col: int
    visible: bool = True
    shape: int = V.CURSOR_BLOCK
    blink: bool = True


class VTerminal:
    """One libvterm screen with a scrollback ring."""

    def __init__(self, rows: int = 24, cols: int = 80, scrollback: int = 10_000):
        self.rows = max(1, int(rows))
        self.cols = max(1, int(cols))
        self.scrollback_limit = max(0, int(scrollback))

        self._vt = V.lib.vterm_new(self.rows, self.cols)
        if not self._vt:
            raise MemoryError("vterm_new failed")
        # Mandatory: libvterm parses bytes, not UTF-8, until this is set.
        V.lib.vterm_set_utf8(self._vt, 1)
        self._screen = V.lib.vterm_obtain_screen(self._vt)
        self._state = V.lib.vterm_obtain_state(self._vt)
        V.lib.vterm_screen_reset(self._screen, 1)
        V.lib.vterm_screen_enable_altscreen(self._screen, 1)
        V.lib.vterm_screen_enable_reflow(self._screen, True)
        V.lib.vterm_screen_set_damage_merge(self._screen, V.DAMAGE["ROW"])

        # theme
        self.foreground = 0xE5E7EB
        self.background = 0x1E1E2E
        self.ansi: tuple[int, ...] = tuple(DEFAULT_ANSI) + tuple(_xterm_palette()[16:])

        # state reported through callbacks / queries
        self.dirty_rows: set[int] = set(range(self.rows))
        self.bell_count = 0
        self.title = ""
        self.icon_name = ""
        self.cursor = Cursor(0, 0)
        self.alt_screen = False
        self.reverse_video = False
        self.mouse_mode = 0
        self.focus_report = False
        self._title_parts: list[str] = []

        # scrollback: (ncols, raw VTermScreenCell bytes) plus the plain text of
        # each line, which is what search walks. Both deques stay aligned.
        self._sb: deque[tuple[int, bytes]] = deque(maxlen=max(1, self.scrollback_limit))
        self._sb_text: deque[str] = deque(maxlen=max(1, self.scrollback_limit))
        self._sb_total = 0

        # rendering cache
        self._runs: dict[int, list[Run]] = {}
        self._sb_runs: dict[int, list[Run]] = {}
        self._color_cache: dict[tuple[int, int, int, int], int] = {}

        # callbacks must outlive the screen
        self.on_clipboard = None          # callable(text: str, primary: bool)
        self.on_clipboard_query = None    # callable() -> None, answers OSC 52 reads
        self._callbacks = self._build_callbacks()
        V.lib.vterm_screen_set_callbacks(
            self._screen, C.byref(self._callbacks), None)
        self._selection = self._build_selection_callbacks()
        self._selection_buffer = C.create_string_buffer(8192)
        V.lib.vterm_state_set_selection_callbacks(
            self._state, C.byref(self._selection), None,
            self._selection_buffer, len(self._selection_buffer))

    # ------------------------------------------------------------- lifecycle --

    def close(self) -> None:
        if getattr(self, "_vt", None):
            V.lib.vterm_free(self._vt)
            self._vt = None

    def __del__(self):  # pragma: no cover - best effort
        try:
            self.close()
        except Exception:
            pass

    # ----------------------------------------------------------------- theme --

    def set_theme(self, foreground: int, background: int, ansi=None) -> None:
        """Colours are 0xRRGGBB ints; changing them invalidates every cached run."""
        self.foreground = int(foreground)
        self.background = int(background)
        if ansi is not None and len(ansi) >= 16:
            self.ansi = tuple(int(c) for c in ansi[:16]) + tuple(_xterm_palette()[16:])
        self._color_cache.clear()
        self._runs.clear()
        self._sb_runs.clear()
        self.dirty_rows.update(range(self.rows))

    # ------------------------------------------------------------------ feed --

    def feed(self, data: bytes) -> None:
        if not data or not self._vt:
            return
        V.lib.vterm_input_write(self._vt, data, len(data))
        V.lib.vterm_screen_flush_damage(self._screen)

    def resize(self, rows: int, cols: int) -> bool:
        rows, cols = max(1, int(rows)), max(1, int(cols))
        if (rows, cols) == (self.rows, self.cols):
            return False
        self.rows, self.cols = rows, cols
        V.lib.vterm_set_size(self._vt, rows, cols)
        self._runs.clear()
        self._sb_runs.clear()
        self.dirty_rows = set(range(rows))
        return True

    # ------------------------------------------------------------- rendering --

    def take_dirty(self) -> bool:
        """True when anything changed since the last call (and clears the set)."""
        dirty = bool(self.dirty_rows)
        self.dirty_rows.clear()
        return dirty

    def row_runs(self, row: int) -> list[Run]:
        if not (0 <= row < self.rows):
            return []
        runs = self._runs.get(row)
        if runs is None:
            get = V.lib.vterm_screen_get_cell
            cells = []
            for col in range(self.cols):
                # A fresh struct per cell: get_cell leaves the tail of chars[]
                # untouched for blank cells, which would repeat combining marks.
                cell = V.Cell()
                get(self._screen, V.Pos(row, col), C.byref(cell))
                cells.append(cell_bits(cell))
            runs = _build_runs(cells, self, self.cols)
            self._runs[row] = runs
        return runs

    # ------------------------------------------------------------ scrollback --

    @property
    def scrollback_len(self) -> int:
        return len(self._sb)

    def scrollback_runs(self, index: int) -> list[Run]:
        """Runs for history line ``index`` (0 = oldest kept line)."""
        runs = self._sb_runs.get(index)
        if runs is None:
            entry = self._sb[index]
            runs = _runs_from_raw(entry[0], entry[1], self)
            self._sb_runs[index] = runs
        return runs

    def set_scrollback(self, limit: int) -> None:
        limit = max(0, int(limit))
        if limit == self.scrollback_limit:
            return
        self.scrollback_limit = limit
        keep = list(self._sb)[-limit:] if limit else []
        keep_text = list(self._sb_text)[-limit:] if limit else []
        self._sb = deque(keep, maxlen=max(1, limit))
        self._sb_text = deque(keep_text, maxlen=max(1, limit))
        self._sb_runs.clear()

    def clear_scrollback(self) -> None:
        self._sb.clear()
        self._sb_text.clear()
        self._sb_total = 0
        self._sb_runs.clear()

    def line_cells(self, index: int) -> list[str]:
        """One line as per-column strings (``""`` marks a wide-glyph continuation).

        ``index`` is absolute over scrollback + screen, so selection and copy
        work the same whether the line is history or live.
        """
        if index < 0:
            return []
        if index < len(self._sb):
            _cols, raw = self._sb[index]
            out: list[str] = []
            count = len(raw) // V.CELL_SIZE
            for i in range(self.cols):
                if i >= count:
                    out.append("")
                    continue
                cell = V.Cell.from_buffer_copy(raw, i * V.CELL_SIZE)
                out.append(_cell_char(cell))
            return out
        row = index - len(self._sb)
        if not (0 <= row < self.rows):
            return []
        get = V.lib.vterm_screen_get_cell
        out = []
        for col in range(self.cols):
            cell = V.Cell()
            get(self._screen, V.Pos(row, col), C.byref(cell))
            out.append(_cell_char(cell))
        return out

    def line_text(self, index: int) -> str:
        """Plain text of an absolute line, cheap enough for a keystroke search.

        Scrollback lines are cached as text when they are pushed; screen rows
        are built on demand (a screen is at most a few thousand cells).
        """
        if index < 0:
            return ""
        if index < len(self._sb_text):
            return self._sb_text[index]
        row = index - len(self._sb_text)
        if not (0 <= row < self.rows):
            return ""
        return "".join(self.line_cells(index)).rstrip()

    def history_text(self, limit: int = 4000) -> str:
        out: list[str] = []
        start = max(0, len(self._sb) - limit)
        for i in range(start, len(self._sb)):
            out.append("".join(r.text for r in self.scrollback_runs(i)).rstrip())
        return "\n".join(out)

    # ------------------------------------------------------------------ keys --

    def key(self, code: int, mods: int = 0) -> bytes:
        V.lib.vterm_keyboard_key(self._vt, int(code), int(mods))
        return self._drain()

    def unichar(self, codepoint: int, mods: int = 0) -> bytes:
        V.lib.vterm_keyboard_unichar(self._vt, int(codepoint), int(mods))
        return self._drain()

    def paste(self, text: str) -> bytes:
        """Bracketed-paste aware: libvterm wraps it when the app asked for it."""
        if not text:
            return b""
        V.lib.vterm_keyboard_start_paste(self._vt)
        for ch in text.replace("\r\n", "\n").replace("\n", "\r"):
            if ch == "\r":
                V.lib.vterm_keyboard_key(self._vt, KEY["ENTER"], 0)
            else:
                V.lib.vterm_keyboard_unichar(self._vt, ord(ch), 0)
        V.lib.vterm_keyboard_end_paste(self._vt)
        return self._drain()

    def mouse_move(self, row: int, col: int, mods: int = 0) -> bytes:
        V.lib.vterm_mouse_move(self._vt, int(row), int(col), int(mods))
        return self._drain()

    def mouse_button(self, button: int, pressed: bool, mods: int = 0) -> bytes:
        V.lib.vterm_mouse_button(self._vt, int(button), bool(pressed), int(mods))
        return self._drain()

    def focus(self, focused: bool) -> bytes:
        if self.focus_report:
            if focused:
                V.lib.vterm_state_focus_in(self._vt)
            else:
                V.lib.vterm_state_focus_out(self._vt)
            return self._drain()
        return b""

    def _drain(self) -> bytes:
        out = bytearray()
        while True:
            buf = C.create_string_buffer(4096)
            n = V.lib.vterm_output_read(self._vt, buf, len(buf))
            if not n:
                break
            out += buf.raw[:n]
            if n < len(buf):
                break
        return bytes(out)

    # ------------------------------------------------------------- callbacks --

    def _build_callbacks(self) -> V.ScreenCallbacks:
        @V._DAMAGE
        def damage(rect, _user):
            for row in range(rect.start_row, min(rect.end_row, self.rows)):
                self.dirty_rows.add(row)
                self._runs.pop(row, None)
            return 1

        @V._MOVERECT
        def moverect(_dest, _src, _user):
            # A scroll shifts every row; re-reading them individually costs more
            # than one full repaint at this grid size.
            self.dirty_rows.update(range(self.rows))
            self._runs.clear()
            return 1

        @V._MOVECURSOR
        def movecursor(pos, oldpos, visible, _user):
            self.cursor = Cursor(pos.row, pos.col, bool(visible),
                                 self.cursor.shape, self.cursor.blink)
            self.dirty_rows.add(pos.row)
            self.dirty_rows.add(oldpos.row)
            return 1

        @V._SETTERMPROP
        def settermprop(prop, value, _user):
            raw = value.contents
            if prop == V.PROP["TITLE"]:
                frag = raw.string
                text = frag.str[:frag.len].decode("utf-8", "replace") if frag.str else ""
                if frag.initial:
                    self._title_parts = []
                self._title_parts.append(text)
                self.title = "".join(self._title_parts)
            elif prop == V.PROP["ICON_NAME"]:
                frag = raw.string
                self.icon_name = (
                    frag.str[:frag.len].decode("utf-8", "replace") if frag.str else "")
            elif prop == V.PROP["CURSOR_VISIBLE"]:
                self.cursor = Cursor(self.cursor.row, self.cursor.col,
                                     bool(raw.boolean), self.cursor.shape, self.cursor.blink)
            elif prop == V.PROP["CURSOR_BLINK"]:
                self.cursor = Cursor(self.cursor.row, self.cursor.col,
                                     self.cursor.visible, self.cursor.shape, bool(raw.boolean))
            elif prop == V.PROP["CURSOR_SHAPE"]:
                self.cursor = Cursor(self.cursor.row, self.cursor.col,
                                     self.cursor.visible, int(raw.number), self.cursor.blink)
            elif prop == V.PROP["ALT_SCREEN"]:
                self.alt_screen = bool(raw.boolean)
            elif prop == V.PROP["REVERSE"]:
                self.reverse_video = bool(raw.boolean)
                self._runs.clear()
                self.dirty_rows.update(range(self.rows))
            elif prop == V.PROP["MOUSE"]:
                self.mouse_mode = int(raw.number)
            elif prop == V.PROP["FOCUS_REPORT"]:
                self.focus_report = bool(raw.boolean)
            return 1

        @V._BELL
        def bell(_user):
            self.bell_count += 1
            return 1

        @V._RESIZE
        def resize(rows, cols, _user):
            self.dirty_rows.update(range(max(rows, self.rows)))
            self._runs.clear()
            return 1

        @V._PUSHLINE
        def pushline(cols, cells, _user):
            self._push_line(cols, cells)
            return 1

        @V._POPLINE
        def popline(cols, cells, _user):
            return self._pop_line(cols, cells)

        @V._SBCLEAR
        def sb_clear(_user):
            self._sb.clear()
            self._sb_text.clear()
            self._sb_total = 0
            self._sb_runs.clear()
            return 1

        return V.ScreenCallbacks(
            damage, moverect, movecursor, settermprop, bell, resize,
            pushline, popline, sb_clear)

    def _build_selection_callbacks(self) -> V.SelectionCallbacks:
        @V._SELSET
        def set_selection(mask, frag, _user):
            text = frag.str[:frag.len].decode("utf-8", "replace") if frag.str else ""
            if frag.final and self.on_clipboard:
                self.on_clipboard(text, bool(mask & V.SELECT["PRIMARY"]))
            return 1

        @V._SELQUERY
        def query_selection(_mask, _user):
            # OSC 52 reads are answered by the app through send_clipboard().
            if self.on_clipboard_query:
                self.on_clipboard_query()
            return 1

        self.on_clipboard_query = None
        return V.SelectionCallbacks(set_selection, query_selection)

    # ---------------------------------------------------- scrollback storage --

    def _push_line(self, cols: int, cells) -> None:
        if self.scrollback_limit == 0:
            return
        n = _trimmed_cells(cells, cols)
        raw = C.string_at(cells, max(1, n) * V.CELL_SIZE) if n else b""
        self._sb.append((cols, raw))
        self._sb_text.append(_raw_text(raw))
        self._sb_total += 1
        # indices shift when the deque evicts, so drop the whole cache
        self._sb_runs.clear()

    def _pop_line(self, cols: int, cells) -> int:
        if not self._sb:
            return 0
        _stored_cols, raw = self._sb.pop()
        if self._sb_text:
            self._sb_text.pop()
        C.memset(cells, 0, cols * V.CELL_SIZE)
        for i in range(cols):
            cell = cells[i]
            cell.width = 1
            cell.fg.type = V.COLOR_DEFAULT_FG
            cell.bg.type = V.COLOR_DEFAULT_BG
        if raw:
            n = min(cols, len(raw) // V.CELL_SIZE)
            C.memmove(cells, raw, n * V.CELL_SIZE)
        self._sb_runs.clear()
        return 1


# ----------------------------------------------------------------- helpers ---

def _cell_char(cell: V.Cell) -> str:
    if cell.width < 0 or cell.chars[0] > 0x10FFFF:
        return ""
    return "".join(chr(c) for c in cell.chars if c) or " "


def cell_bits(cell: V.Cell) -> tuple:
    """Freeze a live cell into plain values (the VTermCell is reused per column).

    Up to six codepoints live in one cell: a base character plus combining
    marks, which must travel together or `e` + U+0301 loses its accent.
    """
    return (
        tuple(c for c in cell.chars if c), cell.width, cell.attrs.bits,
        (cell.fg.type, cell.fg.red, cell.fg.green, cell.fg.blue),
        (cell.bg.type, cell.bg.red, cell.bg.green, cell.bg.blue),
    )


def _attr_flags(bits: int) -> int:
    flags = 0
    if bits & V.ATTR_MASK["BOLD"]:
        flags |= A_BOLD
    under = (bits >> ATTR["UNDERLINE"]) & 0b11
    if under:
        flags |= A_UNDERLINE | (under << UNDERLINE_STYLE_SHIFT)
    if bits & V.ATTR_MASK["ITALIC"]:
        flags |= A_ITALIC
    if bits & V.ATTR_MASK["BLINK"]:
        flags |= A_BLINK
    if bits & V.ATTR_MASK["REVERSE"]:
        flags |= A_REVERSE
    if bits & V.ATTR_MASK["CONCEAL"]:
        flags |= A_CONCEAL
    if bits & V.ATTR_MASK["STRIKE"]:
        flags |= A_STRIKE
    if bits & V.ATTR_MASK["SMALL"]:
        flags |= A_SMALL
    baseline = (bits >> ATTR["BASELINE"]) & 0b11
    if baseline:
        flags |= baseline << BASELINE_SHIFT
    return flags


def _resolve_color(term: "VTerminal", color: tuple, default: int) -> int:
    """Resolve a libvterm colour tuple to 0xRRGGBB, honouring the default flags."""
    ctype, red, green, blue = color
    if ctype & COLOR_DEFAULT_MASK:
        return default
    if ctype & COLOR_TYPE_MASK:
        palette = term.ansi
        return palette[red] if red < len(palette) else default
    return (red << 16) | (green << 8) | blue


def _build_runs(cells: list[tuple], term: "VTerminal", cols: int) -> list[Run]:
    runs: list[Run] = []
    text: list[str] = []
    width = 0
    key: tuple[int, int, int] | None = None

    def flush() -> None:
        nonlocal text, width, key
        if key is not None and width:
            runs.append(Run("".join(text), width, key[0], key[1], key[2]))
        text, width = [], 0

    for cps, cell_width, bits, fg, bg in cells:
        if cell_width < 0 or (cps and cps[0] > 0x10FFFF):
            # libvterm marks the right half of a wide glyph with 0xFFFFFFFF.
            continue
        fgc = _resolve_color(term, fg, term.foreground)
        bgc = _resolve_color(term, bg, term.background)
        flags = _attr_flags(bits)
        if flags & A_REVERSE or term.reverse_video:
            fgc, bgc = bgc, fgc
            flags &= ~A_REVERSE
        if flags & A_CONCEAL:
            fgc = bgc
        span = cell_width or 1
        # A blank cell only matters when it carries a background or attribute.
        if not cps and bgc == term.background and not flags:
            flush()
            key = None
            continue
        if len(cps) == 1 and BOX_FIRST <= cps[0] <= BOX_LAST:
            # Box drawing and block elements are painted as geometry rather
            # than by the font (see boxdraw.py), so each one gets a run of its
            # own and the painter can address its cell exactly.
            flush()
            key = None
            runs.append(Run(chr(cps[0]), span, fgc, bgc, flags))
            continue
        new_key = (fgc, bgc, flags)
        if new_key != key:
            flush()
            key = new_key
        text.append("".join(chr(c) for c in cps) if cps else " ")
        width += span
    flush()
    return runs


def _runs_from_raw(cols: int, raw: bytes, term: "VTerminal") -> list[Run]:
    cells: list[tuple] = []
    count = len(raw) // V.CELL_SIZE
    for i in range(count):
        cell = V.Cell.from_buffer_copy(raw, i * V.CELL_SIZE)
        cells.append(cell_bits(cell))
    blank_fg = (V.COLOR_DEFAULT_FG, 0, 0, 0)
    blank_bg = (V.COLOR_DEFAULT_BG, 0, 0, 0)
    while len(cells) < cols:
        cells.append(((), 1, 0, blank_fg, blank_bg))
    return _build_runs(cells, term, cols)


def _raw_text(raw: bytes) -> str:
    out: list[str] = []
    for i in range(len(raw) // V.CELL_SIZE):
        cell = V.Cell.from_buffer_copy(raw, i * V.CELL_SIZE)
        out.append(_cell_char(cell))
    return "".join(out).rstrip()


def _trimmed_cells(cells, cols: int) -> int:
    """Number of cells up to and including the last non-blank one."""
    last = 0
    for i in range(cols - 1, -1, -1):
        cell = cells[i]
        if cell.chars[0] or (cell.bg.type & COLOR_DEFAULT_MASK) == 0:
            last = i + 1
            break
    return last


def _xterm_palette() -> list[int]:
    """The 256-colour table, indexes 16..255 (0..15 come from the theme)."""
    out = [0] * 16
    steps = (0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF)
    for r in range(6):
        for g in range(6):
            for b in range(6):
                out.append((steps[r] << 16) | (steps[g] << 8) | steps[b])
    grey = 8
    while len(out) < 256:
        out.append((grey << 16) | (grey << 8) | grey)
        grey += 10
    return out[:256]


PALETTE256 = _xterm_palette()


def modifier_for(shift: bool, alt: bool, ctrl: bool) -> int:
    return (MOD["SHIFT"] if shift else 0) | (MOD["ALT"] if alt else 0) | (MOD["CTRL"] if ctrl else 0)
