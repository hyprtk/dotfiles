"""Decimal arithmetic, literal parsing and display formatting.

The whole calculator works in :class:`decimal.Decimal`: ``0.1 + 0.2`` is
``0.3``, not ``0.30000000000000004``, and a 12-digit answer really has 12
digits of meaning. Only the transcendental functions (``sin``, ``ln``, ...)
drop to ``math`` floats, because the standard library has no Decimal versions
of them; everything else stays exact decimal.

Two precisions are in play and they are not the same thing:

* **display precision** (``Context.precision``) -- the significant digits the
  user asked to see, 12 by default;
* **working precision** (``precision + 12``, capped) -- the guard digits every
  operation is carried at, so a float-derived result such as ``sin(30 deg) =
  0.49999999999999994`` rounds to a clean ``0.5`` instead of showing the noise.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

MIN_PRECISION = 3
MAX_PRECISION = 60
DEFAULT_PRECISION = 12
GUARD_DIGITS = 12

BASES = (2, 8, 10, 16)
BASE_PREFIX = {2: "0b", 8: "0o", 10: "", 16: "0x"}
BASE_LABEL = {2: "BIN", 8: "OCT", 10: "DEC", 16: "HEX"}

GROUPS = {
    "none": "",
    "thin": "\u2009",
    "space": " ",
    "comma": ",",
    "point": ".",
}

# Scientific notation kicks in outside the range a desktop calculator display
# can show comfortably; inside it a plain decimal is easier to read than
# ``1.234e+08``.
SCI_BELOW = Decimal("1e-9")
SCI_ABOVE = Decimal("1e12")


class CalcError(Exception):
    """A user-facing calculation error; the message goes to the display."""


def clamp_precision(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PRECISION
    return max(MIN_PRECISION, min(MAX_PRECISION, number))


def work_precision(display_precision: int) -> int:
    return min(MAX_PRECISION + GUARD_DIGITS, clamp_precision(display_precision) + GUARD_DIGITS)


def round_to(value: Decimal, precision: int) -> Decimal:
    """Round to ``precision`` significant digits, banker's rounding.

    Unlike :func:`clamp_precision` this accepts any positive precision: it is
    also used internally, where a display precision of 3 means 15 guard digits.
    """
    try:
        digits = int(precision)
    except (TypeError, ValueError):
        digits = DEFAULT_PRECISION
    with localcontext() as ctx:
        ctx.prec = max(1, min(MAX_PRECISION + GUARD_DIGITS, digits))
        ctx.rounding = ROUND_HALF_EVEN
        return +value


def parse_literal(text: str) -> Decimal:
    """A numeric literal: ``12``, ``1.5``, ``1e-3``, ``0x1f``, ``0b1010``."""
    body = text.replace("_", "")
    lowered = body.lower()
    try:
        if lowered.startswith(("0x", "0b", "0o")):
            return Decimal(int(body, 0))
        return Decimal(body)
    except (ValueError, ArithmeticError) as exc:  # pragma: no cover - lexer guards
        raise CalcError("'{0}' is not a number".format(text)) from exc


# ----------------------------------------------------------------- formatting

def _plain(value: Decimal) -> str:
    """Plain notation with trailing zeros trimmed."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-", "-0", "0"):
        return "0"
    return text


def _group(int_part: str, separator: str) -> str:
    if not separator or len(int_part) <= 3:
        return int_part
    chunks = []
    while len(int_part) > 3:
        chunks.append(int_part[-3:])
        int_part = int_part[:-3]
    chunks.append(int_part)
    return separator.join(reversed(chunks))


def _grouped(text: str, separator: str) -> str:
    sign = ""
    if text.startswith("-"):
        sign, text = "-", text[1:]
    if "." in text:
        whole, frac = text.split(".", 1)
        return sign + _group(whole, separator) + "." + frac
    return sign + _group(text, separator)


def _scientific(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    exponent = magnitude.adjusted()
    with localcontext() as ctx:
        ctx.prec = MAX_PRECISION + GUARD_DIGITS
        mantissa = magnitude.scaleb(-exponent)
    return "{0}{1}e{2:+d}".format(sign, _plain(mantissa), exponent)


def format_number(
    value: Decimal,
    precision: int = DEFAULT_PRECISION,
    base: int = 10,
    grouping: str = "none",
) -> str:
    """Render a result for the display."""
    if value.is_nan():
        return "not a number"
    if value.is_infinite():
        return "-∞" if value < 0 else "∞"
    if base != 10:
        return format_base(value, base, grouping)
    rounded = round_to(value, precision)
    if rounded == 0:
        return "0"
    magnitude = abs(rounded)
    if magnitude < SCI_BELOW or magnitude >= SCI_ABOVE:
        return _scientific(rounded)
    return _grouped(_plain(rounded), GROUPS.get(grouping, ""))


def integral(value: Decimal) -> int:
    """Bitwise operators and base conversion need an exact integer."""
    if value.is_infinite() or value.is_nan():
        raise CalcError("not an integer")
    if value != value.to_integral_value():
        raise CalcError("{0} is not an integer".format(_plain(round_to(value, 9))))
    return int(value)


def format_base(value: Decimal, base: int, grouping: str = "none") -> str:
    """Integer in ``base``, prefixed like a source literal (``0x1f``)."""
    if base not in BASES or base == 10:
        return format_number(value, grouping=grouping)
    number = integral(value)
    sign = "-" if number < 0 else ""
    digits = format(abs(number), {2: "b", 8: "o", 16: "X"}[base])
    if base == 2 and grouping != "none":
        digits = _nibbles(digits)  # binary is read in nibbles, never in thousands
    return sign + BASE_PREFIX[base] + digits


def _nibbles(digits: str) -> str:
    chunks = []
    while len(digits) > 4:
        chunks.append(digits[-4:])
        digits = digits[:-4]
    chunks.append(digits)
    return " ".join(reversed(chunks))


def all_bases(value: Decimal) -> dict:
    """The programmer readout: the same integer in all four bases."""
    out = {}
    for base in (16, 10, 8, 2):
        try:
            out[base] = format_base(value, base)
        except CalcError:
            out[base] = "—"
    return out
