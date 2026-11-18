"""ctypes declarations for libvterm 0.3.x.

Nothing in this module keeps state: it is the ABI description (structs,
signatures, enum values) that :mod:`hyprtk_term.vt` builds on.

Every function lives in :data:`SIGNATURES`. That is deliberate: a ctypes
function whose ``restype`` is unset returns a truncated 32-bit pointer, and the
crash that follows points nowhere near the real line. Adding a call anywhere
else is how that bug gets reintroduced.

Values were checked against ``/usr/include/vterm.h`` (0.3.3) and by probing the
library, not copied from memory -- the key enum in particular is a trap:
``VTERM_KEY_ENTER`` is 1, so ``TAB`` is 2 and ``UP`` is 5.
"""

from __future__ import annotations

import ctypes as C
import ctypes.util
import os

__all__ = [
    "lib", "Pos", "Rect", "Cell", "RGB", "Attrs", "Value", "Fragment",
    "ScreenCallbacks", "SelectionCallbacks",
    "KEY", "MOD", "ATTR", "PROP", "DAMAGE", "MOUSE", "SELECT",
    "CELL_SIZE", "COLOR_RGB", "COLOR_INDEXED", "COLOR_DEFAULT_FG",
    "COLOR_DEFAULT_BG", "COLOR_DEFAULT_MASK", "CURSOR_BLOCK",
    "CURSOR_UNDERLINE", "CURSOR_BAR", "library_path",
]

_SONAMES = (
    "libvterm.so.0", "libvterm.so", "libvterm.0.dylib", "libvterm.dylib",
    "libvterm.so.0.3.3",
)


_loaded_from = ""


def _load() -> C.CDLL:
    global _loaded_from
    override = os.environ.get("HYPRTK_TERM_LIBVTERM")
    candidates = ([override] if override else []) + list(_SONAMES)
    found = ctypes.util.find_library("vterm")
    if found:
        candidates.append(found)
    errors = []
    for name in candidates:
        if not name:
            continue
        try:
            handle = C.CDLL(name)
        except OSError as exc:  # pragma: no cover - depends on the host
            errors.append(f"{name}: {exc}")
            continue
        _loaded_from = name
        return handle
    detail = "\n  ".join(errors) if errors else "no candidates"
    raise OSError(
        "libvterm could not be loaded; install the distro package "
        "(libvterm on Arch/Fedora/Void/Alpine, libvterm0 on Debian/openSUSE)\n  "
        + detail
    )


def library_path() -> str:
    """The soname libvterm was loaded from, for diagnostics and the About box."""
    return _loaded_from


lib = _load()

# ------------------------------------------------------------------ structs --

class Pos(C.Structure):
    _fields_ = [("row", C.c_int), ("col", C.c_int)]


class Rect(C.Structure):
    _fields_ = [
        ("start_row", C.c_int), ("end_row", C.c_int),
        ("start_col", C.c_int), ("end_col", C.c_int),
    ]


class RGB(C.Structure):
    """``VTermColor``: a tagged union that is always four bytes.

    ``type`` is the tag, then either ``red/green/blue`` or (when the indexed
    bit is set) the palette index in ``red``. Modelled as a struct because the
    union's largest member has exactly this layout.
    """
    _fields_ = [
        ("type", C.c_uint8),
        ("red", C.c_uint8),
        ("green", C.c_uint8),
        ("blue", C.c_uint8),
    ]


class Attrs(C.Structure):
    """``VTermScreenCellAttrs``: one ``unsigned int`` of bitfields."""
    _fields_ = [("bits", C.c_uint32)]


class Cell(C.Structure):
    """``VTermScreenCell`` -- 40 bytes (chars[6] + int8 + pad + attrs + 2 colours)."""
    _fields_ = [
        ("chars", C.c_uint32 * 6),
        ("width", C.c_int8),
        ("_pad", C.c_ubyte * 3),
        ("attrs", Attrs),
        ("fg", RGB),
        ("bg", RGB),
    ]


CELL_SIZE = C.sizeof(Cell)


class Fragment(C.Structure):
    """``VTermStringFragment``: len/initial/final are ``size_t`` bitfields."""
    _fields_ = [
        ("str", C.c_char_p),
        ("len", C.c_size_t, 30),
        ("initial", C.c_size_t, 1),
        ("final", C.c_size_t, 1),
    ]


class Value(C.Union):
    _fields_ = [
        ("boolean", C.c_int),
        ("number", C.c_int),
        ("string", Fragment),
        ("color", RGB),
    ]


# --------------------------------------------------------------- signatures --

_DAMAGE = C.CFUNCTYPE(C.c_int, Rect, C.c_void_p)
_MOVERECT = C.CFUNCTYPE(C.c_int, Rect, Rect, C.c_void_p)
_MOVECURSOR = C.CFUNCTYPE(C.c_int, Pos, Pos, C.c_int, C.c_void_p)
_SETTERMPROP = C.CFUNCTYPE(C.c_int, C.c_int, C.POINTER(Value), C.c_void_p)
_BELL = C.CFUNCTYPE(C.c_int, C.c_void_p)
_RESIZE = C.CFUNCTYPE(C.c_int, C.c_int, C.c_int, C.c_void_p)
_PUSHLINE = C.CFUNCTYPE(C.c_int, C.c_int, C.POINTER(Cell), C.c_void_p)
_POPLINE = C.CFUNCTYPE(C.c_int, C.c_int, C.POINTER(Cell), C.c_void_p)
_SBCLEAR = C.CFUNCTYPE(C.c_int, C.c_void_p)


class ScreenCallbacks(C.Structure):
    _fields_ = [
        ("damage", _DAMAGE),
        ("moverect", _MOVERECT),
        ("movecursor", _MOVECURSOR),
        ("settermprop", _SETTERMPROP),
        ("bell", _BELL),
        ("resize", _RESIZE),
        ("sb_pushline", _PUSHLINE),
        ("sb_popline", _POPLINE),
        ("sb_clear", _SBCLEAR),
    ]


_SELSET = C.CFUNCTYPE(C.c_int, C.c_int, Fragment, C.c_void_p)
_SELQUERY = C.CFUNCTYPE(C.c_int, C.c_int, C.c_void_p)


class SelectionCallbacks(C.Structure):
    _fields_ = [("set", _SELSET), ("query", _SELQUERY)]


W = C.c_void_p
I = C.c_int

SIGNATURES = {
    # lifecycle
    "vterm_new": (W, [I, I]),
    "vterm_free": (None, [W]),
    "vterm_set_utf8": (None, [W, I]),
    "vterm_get_utf8": (I, [W]),
    "vterm_set_size": (None, [W, I, I]),
    "vterm_get_size": (None, [W, C.POINTER(I), C.POINTER(I)]),
    # layers
    "vterm_obtain_state": (W, [W]),
    "vterm_obtain_screen": (W, [W]),
    # input / output
    "vterm_input_write": (C.c_size_t, [W, C.c_char_p, C.c_size_t]),
    "vterm_output_read": (C.c_size_t, [W, C.c_char_p, C.c_size_t]),
    "vterm_output_get_buffer_current": (C.c_size_t, [W]),
    "vterm_keyboard_key": (None, [W, I, I]),
    "vterm_keyboard_unichar": (None, [W, C.c_uint32, I]),
    "vterm_keyboard_start_paste": (None, [W]),
    "vterm_keyboard_end_paste": (None, [W]),
    "vterm_mouse_move": (None, [W, I, I, I]),
    "vterm_mouse_button": (None, [W, I, C.c_bool, I]),
    "vterm_state_focus_in": (None, [W]),
    "vterm_state_focus_out": (None, [W]),
    # state
    "vterm_state_reset": (None, [W, I]),
    "vterm_state_get_cursorpos": (None, [W, C.POINTER(Pos)]),
    "vterm_state_set_default_colors": (None, [W, C.POINTER(RGB), C.POINTER(RGB)]),
    "vterm_state_set_palette_color": (None, [W, I, C.POINTER(RGB)]),
    "vterm_state_set_bold_highbright": (None, [W, I]),
    "vterm_state_convert_color_to_rgb": (None, [W, C.POINTER(RGB)]),
    "vterm_state_set_callbacks": (None, [W, C.c_void_p, C.c_void_p]),
    "vterm_state_set_selection_callbacks": (
        None, [W, C.POINTER(SelectionCallbacks), C.c_void_p, C.c_char_p, C.c_size_t]),
    "vterm_state_send_selection": (None, [W, I, Fragment]),
    # screen
    "vterm_screen_reset": (None, [W, I]),
    "vterm_screen_enable_altscreen": (None, [W, I]),
    "vterm_screen_enable_reflow": (None, [W, C.c_bool]),
    "vterm_screen_set_callbacks": (None, [W, C.POINTER(ScreenCallbacks), C.c_void_p]),
    "vterm_screen_flush_damage": (None, [W]),
    "vterm_screen_set_damage_merge": (None, [W, I]),
    "vterm_screen_get_cell": (I, [W, Pos, C.POINTER(Cell)]),
    "vterm_screen_get_text": (C.c_size_t, [W, C.c_char_p, C.c_size_t, Rect]),
    "vterm_screen_is_eol": (I, [W, Pos]),
    "vterm_screen_convert_color_to_rgb": (None, [W, C.POINTER(RGB)]),
    "vterm_screen_get_attrs_extent": (I, [W, C.POINTER(Rect), Pos, C.c_int]),
}

# Present in some builds only; the code paths that use them degrade gracefully.
_OPTIONAL = frozenset({"vterm_screen_enable_reflow", "vterm_state_send_selection"})

for _name, (_restype, _argtypes) in SIGNATURES.items():
    try:
        _fn = getattr(lib, _name)
    except AttributeError as exc:  # pragma: no cover - old libvterm
        if _name in _OPTIONAL:
            continue
        raise ImportError(f"libvterm is missing {_name}") from exc
    _fn.restype = _restype
    _fn.argtypes = _argtypes

# ------------------------------------------------------------------ enums ---

KEY = {
    "NONE": 0, "ENTER": 1, "TAB": 2, "BACKSPACE": 3, "ESCAPE": 4,
    "UP": 5, "DOWN": 6, "LEFT": 7, "RIGHT": 8,
    "INS": 9, "DEL": 10, "HOME": 11, "END": 12, "PAGEUP": 13, "PAGEDOWN": 14,
    "FUNCTION_0": 256,
}

MOD = {"NONE": 0, "SHIFT": 1, "ALT": 2, "CTRL": 4}

# VTermScreenCellAttrs bitfield offsets
ATTR = {
    "BOLD": 0, "UNDERLINE": 1, "ITALIC": 3, "BLINK": 4, "REVERSE": 5,
    "CONCEAL": 6, "STRIKE": 7, "FONT": 8, "DWL": 12, "DHL": 13,
    "SMALL": 15, "BASELINE": 16,
}
ATTR_MASK = {
    "BOLD": 0b1,
    "UNDERLINE": 0b110,
    "ITALIC": 0b1000,
    "BLINK": 0b1_0000,
    "REVERSE": 0b10_0000,
    "CONCEAL": 0b100_0000,
    "STRIKE": 0b1000_0000,
    "FONT": 0b1111_0000_0000,
    "DWL": 0b1_0000_0000_0000,
    "DHL": 0b11_0000_0000_0000,
    "SMALL": 0b1000_0000_0000_0000,
    "BASELINE": 0b11_0000_0000_0000_0000,
}

PROP = {
    "CURSOR_VISIBLE": 1, "CURSOR_BLINK": 2, "ALT_SCREEN": 3, "TITLE": 4,
    "ICON_NAME": 5, "REVERSE": 6, "CURSOR_SHAPE": 7, "MOUSE": 8,
    "FOCUS_REPORT": 9,
}

DAMAGE = {"CELL": 0, "ROW": 1, "SCREEN": 2, "SCROLL": 3}
MOUSE = {"NONE": 0, "CLICK": 1, "DRAG": 2, "MOVE": 3}
SELECT = {"CLIPBOARD": 1, "PRIMARY": 2, "SECONDARY": 4}

CURSOR_BLOCK = 1
CURSOR_UNDERLINE = 2
CURSOR_BAR = 3

COLOR_RGB = 0x00
COLOR_INDEXED = 0x01
COLOR_TYPE_MASK = 0x01
COLOR_DEFAULT_FG = 0x02
COLOR_DEFAULT_BG = 0x04
COLOR_DEFAULT_MASK = 0x06
