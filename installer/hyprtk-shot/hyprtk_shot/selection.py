"""Selection geometry: the square constraint, clamping and keyboard nudging.

The canvas owns the mouse and the bridge owns the state, so the maths that both
of them need lives here as plain functions on numbers. That is what makes the
behaviour testable without a display: a drag with Shift held, an arrow press at
the edge of the image, a selection that must not leave the frame.
"""

from __future__ import annotations

MIN_SIZE = 4.0

#: Eight resize grips, named by the compass edge they move.
HANDLES = ("nw", "n", "ne", "e", "se", "s", "sw", "w")


def square(ox: float, oy: float, x: float, y: float) -> tuple[float, float]:
    """Constrain a drag corner so the box is square (Shift while selecting).

    The larger of the two deltas wins, so the box follows the pointer instead of
    collapsing when one axis is still short.
    """
    dx, dy = x - ox, y - oy
    size = max(abs(dx), abs(dy))
    return (ox + (size if dx >= 0 else -size), oy + (size if dy >= 0 else -size))


def clamp(x: float, y: float, w: float, h: float,
          image_w: int, image_h: int) -> tuple[float, float, float, float]:
    """Normalise a selection and keep it inside the image."""
    w = max(MIN_SIZE, min(abs(w), float(image_w)))
    h = max(MIN_SIZE, min(abs(h), float(image_h)))
    x = min(max(0.0, x), max(0.0, image_w - w))
    y = min(max(0.0, y), max(0.0, image_h - h))
    return (x, y, w, h)


def nudge(x: float, y: float, w: float, h: float, dx: float, dy: float,
          image_w: int, image_h: int) -> tuple[float, float, float, float]:
    """Move a selection by ``dx``/``dy`` pixels, stopping at the image edge.

    A nudge never resizes: the size is the user's decision and an arrow key is
    about placement. At the edge it clamps, it does not shrink.
    """
    nx = min(max(0.0, x + dx), max(0.0, image_w - w))
    ny = min(max(0.0, y + dy), max(0.0, image_h - h))
    return (nx, ny, w, h)


def is_full_frame(x: float, y: float, w: float, h: float,
                  image_w: int, image_h: int, *, tolerance: float = 0.5) -> bool:
    """True when the selection is still "everything".

    A region capture starts with the whole frame selected, and moving that
    selection is a no-op (it is already at every edge). Treating it as "nothing
    chosen yet" is what lets the first drag draw a box instead of grab the
    frame and save all of it.
    """
    return (abs(x) <= tolerance and abs(y) <= tolerance
            and abs(w - image_w) <= tolerance and abs(h - image_h) <= tolerance)


def resize(handle: str, x: float, y: float, w: float, h: float,
           px: float, py: float, image_w: int, image_h: int) -> tuple[float, float, float, float]:
    """Move one edge or corner of a selection to ``px``/``py``.

    The opposite edge stays put, which is what makes a grip feel anchored. The
    result keeps at least :data:`MIN_SIZE` and the image as its bounds.
    """
    if handle not in HANDLES:
        return (x, y, w, h)
    left, top, right, bottom = x, y, x + w, y + h
    if "w" in handle:
        left = min(max(0.0, px), right - MIN_SIZE)
    if "e" in handle:
        right = max(min(float(image_w), px), left + MIN_SIZE)
    if "n" in handle:
        top = min(max(0.0, py), bottom - MIN_SIZE)
    if "s" in handle:
        bottom = max(min(float(image_h), py), top + MIN_SIZE)
    return (left, top, right - left, bottom - top)
