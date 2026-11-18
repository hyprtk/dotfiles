"""Geometry for block elements and box-drawing characters.

A terminal cannot trust the font for U+2500-U+259F. Those code points have to
tile: the line in one cell must meet the line in the next, and a half block has
to cover exactly half the cell. Fonts get that wrong in both directions -- they
omit the range outright (JetBrainsMono Nerd Font Mono ships U+2588 and nothing
else of it) or they size the glyph to the em box instead of the cell, leaving
seams. Letting Qt fall back to another family is worse still: it picks a
proportional face and the art shears.

So these characters are painted as rectangles, lines and arcs inside the cell,
which is what every serious terminal does. The module is deliberately Qt-free:
it emits primitives through a small canvas protocol, so the geometry is unit
testable and ``vt`` can ask which cells it owns without importing a GUI.
"""

from __future__ import annotations

# Line weights used by ``LINES``.
LIGHT = 1
HEAVY = 2
DOUBLE = 3

#: Block elements as (x0, y0, x1, y1) rectangles in 0..1 cell space.
BLOCKS: dict[str, tuple[tuple[float, float, float, float], ...]] = {
    "\u2580": ((0, 0, 1, 0.5),),                       # upper half
    "\u2581": ((0, 7 / 8, 1, 1),),                     # lower one eighth
    "\u2582": ((0, 6 / 8, 1, 1),),
    "\u2583": ((0, 5 / 8, 1, 1),),
    "\u2584": ((0, 0.5, 1, 1),),                       # lower half
    "\u2585": ((0, 3 / 8, 1, 1),),
    "\u2586": ((0, 2 / 8, 1, 1),),
    "\u2587": ((0, 1 / 8, 1, 1),),
    "\u2588": ((0, 0, 1, 1),),                         # full block
    "\u2589": ((0, 0, 7 / 8, 1),),                     # left seven eighths
    "\u258a": ((0, 0, 6 / 8, 1),),
    "\u258b": ((0, 0, 5 / 8, 1),),
    "\u258c": ((0, 0, 0.5, 1),),                       # left half
    "\u258d": ((0, 0, 3 / 8, 1),),
    "\u258e": ((0, 0, 2 / 8, 1),),
    "\u258f": ((0, 0, 1 / 8, 1),),
    "\u2590": ((0.5, 0, 1, 1),),                       # right half
    "\u2594": ((0, 0, 1, 1 / 8),),                     # upper one eighth
    "\u2595": ((7 / 8, 0, 1, 1),),                     # right one eighth
    "\u2596": ((0, 0.5, 0.5, 1),),                     # quadrants
    "\u2597": ((0.5, 0.5, 1, 1),),
    "\u2598": ((0, 0, 0.5, 0.5),),
    "\u2599": ((0, 0, 0.5, 0.5), (0, 0.5, 0.5, 1), (0.5, 0.5, 1, 1)),
    "\u259a": ((0, 0, 0.5, 0.5), (0.5, 0.5, 1, 1)),
    "\u259b": ((0, 0, 0.5, 0.5), (0.5, 0, 1, 0.5), (0, 0.5, 0.5, 1)),
    "\u259c": ((0, 0, 0.5, 0.5), (0.5, 0, 1, 0.5), (0.5, 0.5, 1, 1)),
    "\u259d": ((0.5, 0, 1, 0.5),),
    "\u259e": ((0.5, 0, 1, 0.5), (0, 0.5, 0.5, 1)),
    "\u259f": ((0.5, 0, 1, 0.5), (0, 0.5, 0.5, 1), (0.5, 0.5, 1, 1)),
}

#: Shade blocks: a flat wash of the foreground at this alpha.
SHADES: dict[str, float] = {
    "\u2591": 0.25,                                    # light shade
    "\u2592": 0.5,                                     # medium shade
    "\u2593": 0.75,                                    # dark shade
}

#: Box drawing as (up, down, left, right) weights.
LINES: dict[str, tuple[int, int, int, int]] = {
    "\u2500": (0, 0, 1, 1),
    "\u2501": (0, 0, 2, 2),
    "\u2502": (1, 1, 0, 0),
    "\u2503": (2, 2, 0, 0),
    "\u250c": (0, 1, 0, 1),
    "\u250d": (0, 1, 0, 2),
    "\u250e": (0, 2, 0, 1),
    "\u250f": (0, 2, 0, 2),
    "\u2510": (0, 1, 1, 0),
    "\u2511": (0, 1, 2, 0),
    "\u2512": (0, 2, 1, 0),
    "\u2513": (0, 2, 2, 0),
    "\u2514": (1, 0, 0, 1),
    "\u2515": (1, 0, 0, 2),
    "\u2516": (2, 0, 0, 1),
    "\u2517": (2, 0, 0, 2),
    "\u2518": (1, 0, 1, 0),
    "\u2519": (1, 0, 2, 0),
    "\u251a": (2, 0, 1, 0),
    "\u251b": (2, 0, 2, 0),
    "\u251c": (1, 1, 0, 1),
    "\u251d": (1, 1, 0, 2),
    "\u251e": (2, 1, 0, 1),
    "\u251f": (1, 2, 0, 1),
    "\u2520": (2, 2, 0, 1),
    "\u2521": (2, 1, 0, 2),
    "\u2522": (1, 2, 0, 2),
    "\u2523": (2, 2, 0, 2),
    "\u2524": (1, 1, 1, 0),
    "\u2525": (1, 1, 2, 0),
    "\u2526": (2, 1, 1, 0),
    "\u2527": (1, 2, 1, 0),
    "\u2528": (2, 2, 1, 0),
    "\u2529": (2, 1, 2, 0),
    "\u252a": (1, 2, 2, 0),
    "\u252b": (2, 2, 2, 0),
    "\u252c": (0, 1, 1, 1),
    "\u252d": (0, 1, 2, 1),
    "\u252e": (0, 1, 1, 2),
    "\u252f": (0, 1, 2, 2),
    "\u2530": (0, 2, 1, 1),
    "\u2531": (0, 2, 2, 1),
    "\u2532": (0, 2, 1, 2),
    "\u2533": (0, 2, 2, 2),
    "\u2534": (1, 0, 1, 1),
    "\u2535": (1, 0, 2, 1),
    "\u2536": (1, 0, 1, 2),
    "\u2537": (1, 0, 2, 2),
    "\u2538": (2, 0, 1, 1),
    "\u2539": (2, 0, 2, 1),
    "\u253a": (2, 0, 1, 2),
    "\u253b": (2, 0, 2, 2),
    "\u253c": (1, 1, 1, 1),
    "\u253d": (1, 1, 2, 1),
    "\u253e": (1, 1, 1, 2),
    "\u253f": (1, 1, 2, 2),
    "\u2540": (2, 1, 1, 1),
    "\u2541": (1, 2, 1, 1),
    "\u2542": (2, 2, 1, 1),
    "\u2543": (2, 1, 2, 1),
    "\u2544": (2, 1, 1, 2),
    "\u2545": (1, 2, 2, 1),
    "\u2546": (1, 2, 1, 2),
    "\u2547": (2, 1, 2, 2),
    "\u2548": (1, 2, 2, 2),
    "\u2549": (2, 2, 2, 1),
    "\u254a": (2, 2, 1, 2),
    "\u254b": (2, 2, 2, 2),
    "\u2550": (0, 0, 3, 3),
    "\u2551": (3, 3, 0, 0),
    "\u2552": (0, 1, 0, 3),
    "\u2553": (0, 3, 0, 1),
    "\u2554": (0, 3, 0, 3),
    "\u2555": (0, 1, 3, 0),
    "\u2556": (0, 3, 1, 0),
    "\u2557": (0, 3, 3, 0),
    "\u2558": (1, 0, 0, 3),
    "\u2559": (3, 0, 0, 1),
    "\u255a": (3, 0, 0, 3),
    "\u255b": (1, 0, 3, 0),
    "\u255c": (3, 0, 1, 0),
    "\u255d": (3, 0, 3, 0),
    "\u255e": (1, 1, 0, 3),
    "\u255f": (3, 3, 0, 1),
    "\u2560": (3, 3, 0, 3),
    "\u2561": (1, 1, 3, 0),
    "\u2562": (3, 3, 1, 0),
    "\u2563": (3, 3, 3, 0),
    "\u2564": (0, 1, 3, 3),
    "\u2565": (0, 3, 1, 1),
    "\u2566": (0, 3, 3, 3),
    "\u2567": (1, 0, 3, 3),
    "\u2568": (3, 0, 1, 1),
    "\u2569": (3, 0, 3, 3),
    "\u256a": (1, 1, 3, 3),
    "\u256b": (3, 3, 1, 1),
    "\u256c": (3, 3, 3, 3),
    "\u2574": (0, 0, 1, 0),
    "\u2575": (1, 0, 0, 0),
    "\u2576": (0, 0, 0, 1),
    "\u2577": (0, 1, 0, 0),
    "\u2578": (0, 0, 2, 0),
    "\u2579": (2, 0, 0, 0),
    "\u257a": (0, 0, 0, 2),
    "\u257b": (0, 2, 0, 0),
    "\u257c": (0, 0, 1, 2),
    "\u257d": (1, 2, 0, 0),
    "\u257e": (0, 0, 2, 1),
    "\u257f": (2, 1, 0, 0),
}

#: Dashed lines as (axis, dash count, weight).
DASHES: dict[str, tuple[str, int, int]] = {
    "\u2504": ("h", 3, 1),
    "\u2505": ("h", 3, 2),
    "\u2506": ("v", 3, 1),
    "\u2507": ("v", 3, 2),
    "\u2508": ("h", 4, 1),
    "\u2509": ("h", 4, 2),
    "\u250a": ("v", 4, 1),
    "\u250b": ("v", 4, 2),
    "\u254c": ("h", 2, 1),
    "\u254d": ("h", 2, 2),
    "\u254e": ("v", 2, 1),
    "\u254f": ("v", 2, 2),
}

#: Rounded corners as (horizontal arm, vertical arm).
ARCS: dict[str, tuple[str, str]] = {
    "\u256d": ("right", "down"),
    "\u256e": ("left", "down"),
    "\u256f": ("left", "up"),
    "\u2570": ("right", "up"),
}

#: Diagonals as ((x0, y0), (x1, y1)) segments in 0..1 cell space.
DIAGONALS: dict[str, tuple[tuple[tuple[float, float], tuple[float, float]], ...]] = {
    "\u2571": (((1, 0), (0, 1)),),                     # upper right to lower left
    "\u2572": (((0, 0), (1, 1)),),                     # upper left to lower right
    "\u2573": (((1, 0), (0, 1)), ((0, 0), (1, 1))),    # crossed
}

DRAWABLE = frozenset(BLOCKS) | frozenset(SHADES) | frozenset(LINES) \
    | frozenset(DASHES) | frozenset(ARCS) | frozenset(DIAGONALS)

#: First and last code point this module owns; ``vt`` splits runs on it.
FIRST = 0x2500
LAST = 0x259F


def is_geometric(ch: str) -> bool:
    """True when ``ch`` is painted by this module rather than by the font."""
    return len(ch) == 1 and ch in DRAWABLE


def _thickness(cell_w: float, weight: int) -> float:
    light = max(1.0, round(cell_w / 8.0))
    return light if weight != HEAVY else max(2.0, light * 2.0)


def _separation(cell_w: float) -> float:
    """Centre-to-centre gap between the two strokes of a double line."""
    return max(2.0, round(cell_w / 4.0))


def _horizontal(canvas, x0, x1, cy, weight, cell_w, has_up, has_down,
                grow_right) -> None:
    """One arm of a horizontal line, from the cell centre towards an edge.

    ``has_up``/``has_down`` say whether a vertical arm meets this one at the
    centre: the two strokes of a double line join the matching stroke of the
    perpendicular pair, so each stops at its own offset instead of crossing.
    """
    if weight != DOUBLE:
        stroke = _thickness(cell_w, weight)
        canvas.fill_rect(x0, cy - stroke / 2, x1 - x0, stroke)
        return
    gap = _separation(cell_w)
    stroke = _thickness(cell_w, LIGHT)
    if grow_right:
        top = x0 - gap if not has_up else x0 + gap
        bottom = x0 - gap if not has_down else x0 + gap
        canvas.fill_rect(top, cy - gap - stroke / 2, x1 - top, stroke)
        canvas.fill_rect(bottom, cy + gap - stroke / 2, x1 - bottom, stroke)
    else:
        top = x1 + gap if not has_up else x1 - gap
        bottom = x1 + gap if not has_down else x1 - gap
        canvas.fill_rect(x0, cy - gap - stroke / 2, top - x0, stroke)
        canvas.fill_rect(x0, cy + gap - stroke / 2, bottom - x0, stroke)


def _vertical(canvas, y0, y1, cx, weight, cell_w, has_left, has_right,
              grow_down) -> None:
    """One arm of a vertical line; the mirror of :func:`_horizontal`."""
    if weight != DOUBLE:
        stroke = _thickness(cell_w, weight)
        canvas.fill_rect(cx - stroke / 2, y0, stroke, y1 - y0)
        return
    gap = _separation(cell_w)
    stroke = _thickness(cell_w, LIGHT)
    if grow_down:
        left = y0 - gap if not has_left else y0 + gap
        right = y0 - gap if not has_right else y0 + gap
        canvas.fill_rect(cx - gap - stroke / 2, left, stroke, y1 - left)
        canvas.fill_rect(cx + gap - stroke / 2, right, stroke, y1 - right)
    else:
        left = y1 + gap if not has_left else y1 - gap
        right = y1 + gap if not has_right else y1 - gap
        canvas.fill_rect(cx - gap - stroke / 2, y0, stroke, left - y0)
        canvas.fill_rect(cx + gap - stroke / 2, y0, stroke, right - y0)


def _dashed(canvas, x, y, w, h, axis: str, dashes: int, weight: int,
            cell_w: float) -> None:
    """Dashes are laid out as ``dash gap dash gap ... dash`` across the cell."""
    stroke = _thickness(cell_w, weight)
    span = w if axis == "h" else h
    step = span / (2 * dashes - 1)
    for index in range(dashes):
        offset = index * 2 * step
        if axis == "h":
            canvas.fill_rect(x + offset, y + h / 2 - stroke / 2, step, stroke)
        else:
            canvas.fill_rect(x + w / 2 - stroke / 2, y + offset, stroke, step)


def _arc(canvas, x, y, w, h, arms: tuple[str, str], cell_w: float) -> None:
    horizontal, vertical = arms
    radius = min(w, h) / 2
    stroke = _thickness(cell_w, LIGHT)
    cx = x + w / 2
    cy = y + h / 2
    # Qt measures arc angles counter-clockwise from three o'clock while the
    # y axis points down, so "up" is 90 degrees and "left" is 180.
    if vertical == "down" and horizontal == "right":      # top-left corner
        centre, start = (cx + radius, cy + radius), 90
    elif vertical == "down" and horizontal == "left":     # top-right corner
        centre, start = (cx - radius, cy + radius), 0
    elif vertical == "up" and horizontal == "left":       # bottom-right corner
        centre, start = (cx - radius, cy - radius), 270
    else:                                                 # bottom-left corner
        centre, start = (cx + radius, cy - radius), 180
    canvas.arc(centre[0], centre[1], radius, start, 90, stroke)

    if horizontal == "right":
        canvas.fill_rect(cx + radius, cy - stroke / 2, max(0.0, x + w - cx - radius),
                         stroke)
    else:
        canvas.fill_rect(x, cy - stroke / 2, max(0.0, cx - radius - x), stroke)
    if vertical == "down":
        canvas.fill_rect(cx - stroke / 2, cy + radius, stroke,
                         max(0.0, y + h - cy - radius))
    else:
        canvas.fill_rect(cx - stroke / 2, y, stroke, max(0.0, cy - radius - y))


def draw(canvas, ch: str, x: float, y: float, w: float, h: float) -> bool:
    """Paint ``ch`` into the cell at ``(x, y)`` sized ``w`` x ``h``.

    ``canvas`` supplies ``fill_rect(x, y, w, h, alpha=1.0)``, ``line(x0, y0,
    x1, y1, thickness)`` and ``arc(cx, cy, radius, start, span, thickness)``.
    Returns False when the character is not ours, so the caller can fall back
    to the font.
    """
    blocks = BLOCKS.get(ch)
    if blocks is not None:
        for x0, y0, x1, y1 in blocks:
            canvas.fill_rect(x + x0 * w, y + y0 * h, (x1 - x0) * w, (y1 - y0) * h)
        return True

    shade = SHADES.get(ch)
    if shade is not None:
        canvas.fill_rect(x, y, w, h, shade)
        return True

    arms = LINES.get(ch)
    if arms is not None:
        up, down, left, right = arms
        cx = x + w / 2
        cy = y + h / 2
        if left:
            _horizontal(canvas, x, cx, cy, left, w, bool(up), bool(down), False)
        if right:
            _horizontal(canvas, cx, x + w, cy, right, w, bool(up), bool(down), True)
        if up:
            _vertical(canvas, y, cy, cx, up, w, bool(left), bool(right), False)
        if down:
            _vertical(canvas, cy, y + h, cx, down, w, bool(left), bool(right), True)
        return True

    dashed = DASHES.get(ch)
    if dashed is not None:
        axis, dashes, weight = dashed
        _dashed(canvas, x, y, w, h, axis, dashes, weight, w)
        return True

    arc_arms = ARCS.get(ch)
    if arc_arms is not None:
        _arc(canvas, x, y, w, h, arc_arms, w)
        return True

    segments = DIAGONALS.get(ch)
    if segments is not None:
        stroke = _thickness(w, LIGHT)
        for (ax, ay), (bx, by) in segments:
            canvas.line(x + ax * w, y + ay * h, x + bx * w, y + by * h, stroke)
        return True

    return False
