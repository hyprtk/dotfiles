"""Tokenizer, precedence-climbing parser and evaluator.

A hand-written parser rather than ``ast`` for two reasons: numbers must stay
:class:`decimal.Decimal` (an ``ast`` round-trip turns ``1.5`` into a float and
loses the exactness the whole design rests on), and no user input should ever
reach ``eval``.

Grammar, loosest binding first::

    expr   := bitor
    bitor  := bitxor ( '|' bitxor )*
    bitxor := bitand ( 'xor' bitand )*
    bitand := shift ( '&' shift )*
    shift  := sum ( ('<<'|'>>') sum )*
    sum    := term ( ('+'|'-') term )*
    term   := unary ( ('*'|'/'|implicit) unary )*
    unary  := ('+'|'-'|'~') unary | power
    power  := postfix ( '^' unary )?          # right associative
    postfix:= primary ( '!' | '%' )*
    primary:= number | name '(' args ')' | name <unary> | '(' expr ')'
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, localcontext
from typing import Callable, NamedTuple

from .number import (
    DEFAULT_PRECISION,
    CalcError,
    clamp_precision,
    integral,
    parse_literal,
    round_to,
    work_precision,
)

# 120 digits is far beyond any precision the app offers; the values are then
# rounded to the working precision on use.
PI = Decimal(
    "3.14159265358979323846264338327950288419716939937510582097494459230781640628"
    "6208998628034825342117067982148086513282306647093844609550582231725359408"
)
EULER = Decimal(
    "2.71828182845904523536028747135266249775724709369995957496696762772407663035"
    "3547594571382178525166427427466391932003059921817413596629043572900334295"
)
PHI = Decimal(
    "1.61803398874989484820458683436563811772030917980576286213544862270526046281"
    "8902449707207204189391137484754088075386891752126633862223536931793180060"
)
with localcontext() as _ctx:  # exact at the precision above, not the default 28
    _ctx.prec = 120
    TAU = PI * 2

CONSTANTS = {
    "pi": PI,
    "e": EULER,
    "tau": TAU,
    "phi": PHI,
    "inf": Decimal("Infinity"),
    "infinity": Decimal("Infinity"),
}

# Typographic input is normalised, not rejected: people paste formulas from
# documents all the time.
NORMALISE = {
    "×": "*",
    "⋅": "*",
    "·": "*",
    "÷": "/",
    "−": "-",
    "–": "-",
    "—": "-",
    # Word replacements carry a trailing space: the NAME lexer matches \w,
    # so "sqrt9" would otherwise be read as one unknown name.
    "π": "pi ",
    "τ": "tau ",
    "φ": "phi ",
    "√": "sqrt ",
    "\u00a0": " ",
    "\u2009": " ",
    "\u202f": " ",
}

_OPERATORS = ("<<", ">>", "**", "+", "-", "*", "/", "^", "%", "&", "|", "~", "!", "(", ")", ",")
_NUMBER = re.compile(
    r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+"
    r"|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d+)?"
)
_NAME = re.compile(r"[^\W\d]\w*", re.UNICODE)

# A runaway expression should fail cleanly, not take the UI thread with it.
MAX_TOKENS = 2000
MAX_FACTORIAL = 3000


class Token(NamedTuple):
    kind: str  # num | name | op | lparen | rparen | comma | eof
    text: str
    pos: int


@dataclass
class Context:
    """Everything an evaluation needs that is not in the expression text."""

    precision: int = DEFAULT_PRECISION
    angle: str = "rad"  # deg | rad | grad
    variables: dict = field(default_factory=dict)
    ans: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        self.precision = clamp_precision(self.precision)
        self.angle = (self.angle or "rad").lower()
        if self.angle not in ("deg", "rad", "grad"):
            self.angle = "rad"


# ------------------------------------------------------------------- lexing

def normalise(source: str) -> str:
    out = source
    for old, new in NORMALISE.items():
        if old in out:
            out = out.replace(old, new)
    return out


def tokenize(source: str) -> list[Token]:
    text = normalise(source)
    tokens: list[Token] = []
    i = 0
    size = len(text)
    while i < size:
        char = text[i]
        if char.isspace():
            i += 1
            continue

        # 0x / 0b / 0o need digits of their own before the decimal rule wins.
        if char == "0" and i + 1 < size and text[i + 1] in "xXbBoO":
            match = _NUMBER.match(text, i)
            # The decimal rule can still match the leading "0" alone, so the
            # test is on what was actually consumed.
            if not match or match.group(0) == "0":
                raise CalcError("'{0}' needs digits after the base prefix".format(text[i:i + 2]))
            tokens.append(Token("num", match.group(0), i))
            i = match.end()
            continue

        if char.isdigit() or (char == "." and i + 1 < size and text[i + 1].isdigit()):
            match = _NUMBER.match(text, i)
            if not match:  # pragma: no cover - guarded by the branch above
                raise CalcError("'{0}' is not a number".format(text[i:i + 1]))
            literal = match.group(0)
            if literal.endswith(".") and text[i + len(literal):i + len(literal) + 1] == ".":
                raise CalcError("unexpected '.'")
            tokens.append(Token("num", literal, i))
            i = match.end()
            continue

        if char.isalpha() or char == "_":
            match = _NAME.match(text, i)
            if not match:  # pragma: no cover
                raise CalcError("unexpected '{0}'".format(char))
            tokens.append(Token("name", match.group(0).lower(), i))
            i = match.end()
            continue

        for operator in _OPERATORS:
            if text.startswith(operator, i):
                kind = {"(": "lparen", ")": "rparen", ",": "comma"}.get(operator, "op")
                width = len(operator)
                tokens.append(Token(kind, "^" if operator == "**" else operator, i))
                i += width
                break
        else:
            raise CalcError("unexpected character '{0}'".format(char))

        if len(tokens) > MAX_TOKENS:
            raise CalcError("expression is too long")
    return tokens


# ---------------------------------------------------------------- functions

def _from_float(value: float) -> Decimal:
    if math.isnan(value):
        raise CalcError("the result is not a real number")
    if math.isinf(value):
        raise CalcError("the result is out of range")
    return Decimal(value)


def _int_arg(args: list[Decimal], index: int, name: str) -> int:
    try:
        return integral(args[index])
    except CalcError as exc:
        raise CalcError("{0}() needs a whole number".format(name)) from exc


def _to_radians(ctx: Context, value: Decimal) -> Decimal:
    if ctx.angle == "deg":
        return value * PI / 180
    if ctx.angle == "grad":
        return value * PI / 200
    return value


def _from_radians(ctx: Context, value: Decimal) -> Decimal:
    if ctx.angle == "deg":
        return value * 180 / PI
    if ctx.angle == "grad":
        return value * 200 / PI
    return value


def _trig(fn: Callable[[float], float]) -> Callable[[Context, list], Decimal]:
    def call(ctx: Context, args: list[Decimal]) -> Decimal:
        return _from_float(fn(float(_to_radians(ctx, args[0]))))

    return call


def _arc(fn: Callable[[float], float]) -> Callable[[Context, list], Decimal]:
    def call(ctx: Context, args: list[Decimal]) -> Decimal:
        return _from_radians(ctx, _from_float(fn(float(args[0]))))

    return call


def _factorial(ctx: Context, args: list[Decimal]) -> Decimal:
    number = _int_arg(args, 0, "fact")
    if number < 0:
        raise CalcError("fact() is only defined for whole numbers >= 0")
    if number > MAX_FACTORIAL:
        raise CalcError("fact() is limited to {0}".format(MAX_FACTORIAL))
    return Decimal(math.factorial(number))


def _root(ctx: Context, args: list[Decimal]) -> Decimal:
    degree = args[1]
    if degree == 0:
        raise CalcError("root() of degree 0 is undefined")
    if args[0] < 0:
        if degree != degree.to_integral_value() or int(degree) % 2 == 0:
            raise CalcError("an even root of a negative number is not real")
        return -((-args[0]) ** (Decimal(1) / degree))
    return args[0] ** (Decimal(1) / degree)


def _sqrt(ctx: Context, args: list[Decimal]) -> Decimal:
    if args[0] < 0:
        raise CalcError("sqrt() of a negative number is not real")
    return args[0] ** Decimal("0.5")


def _ln(ctx: Context, args: list[Decimal]) -> Decimal:
    if args[0] <= 0:
        raise CalcError("ln() is only defined for positive numbers")
    return _from_float(math.log(float(args[0])))


def _log(ctx: Context, args: list[Decimal]) -> Decimal:
    if args[0] <= 0:
        raise CalcError("log() is only defined for positive numbers")
    if len(args) == 1:
        return _from_float(math.log10(float(args[0])))
    base = args[1]
    if base <= 0 or base == 1:
        raise CalcError("log() needs a positive base other than 1")
    return _from_float(math.log(float(args[0]), float(base)))


def _round(ctx: Context, args: list[Decimal]) -> Decimal:
    places = _int_arg(args, 1, "round") if len(args) > 1 else 0
    if abs(places) > 60:
        raise CalcError("round() is limited to 60 places")
    return args[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)


def _mod(ctx: Context, args: list[Decimal]) -> Decimal:
    if args[1] == 0:
        raise CalcError("mod() by zero")
    return args[0] - args[1] * (args[0] / args[1]).to_integral_value(rounding=ROUND_HALF_EVEN)


FUNCTIONS: dict[str, tuple[int, int, Callable[[Context, list], Decimal]]] = {
    "sqrt": (1, 1, _sqrt),
    "cbrt": (1, 1, lambda c, a: _root(c, [a[0], Decimal(3)])),
    "root": (2, 2, _root),
    "abs": (1, 1, lambda c, a: abs(a[0])),
    "sign": (1, 1, lambda c, a: Decimal((a[0] > 0) - (a[0] < 0))),
    "exp": (1, 1, lambda c, a: _from_float(math.exp(float(a[0])))),
    "ln": (1, 1, _ln),
    "log": (1, 2, _log),
    "log2": (1, 1, lambda c, a: _from_float(math.log2(float(a[0])))),
    "log10": (1, 1, lambda c, a: _from_float(math.log10(float(a[0])))),
    "floor": (1, 1, lambda c, a: Decimal(math.floor(a[0]))),
    "ceil": (1, 1, lambda c, a: Decimal(math.ceil(a[0]))),
    "round": (1, 2, _round),
    "trunc": (1, 1, lambda c, a: Decimal(int(a[0]))),
    "mod": (2, 2, _mod),
    "min": (1, 64, lambda c, a: min(a)),
    "max": (1, 64, lambda c, a: max(a)),
    "gcd": (1, 64, lambda c, a: Decimal(math.gcd(*(integral(x) for x in a)))),
    "lcm": (1, 64, lambda c, a: Decimal(math.lcm(*(integral(x) for x in a)))),
    "hypot": (1, 64, lambda c, a: _from_float(math.hypot(*(float(x) for x in a)))),
    "fact": (1, 1, _factorial),
    "ncr": (2, 2, lambda c, a: Decimal(math.comb(_int_arg(a, 0, "ncr"), _int_arg(a, 1, "ncr")))),
    "npr": (2, 2, lambda c, a: Decimal(math.perm(_int_arg(a, 0, "npr"), _int_arg(a, 1, "npr")))),
    "deg": (1, 1, lambda c, a: a[0] * 180 / PI),
    "rad": (1, 1, lambda c, a: a[0] * PI / 180),
    "sin": (1, 1, _trig(math.sin)),
    "cos": (1, 1, _trig(math.cos)),
    "tan": (1, 1, _trig(math.tan)),
    "asin": (1, 1, _arc(math.asin)),
    "acos": (1, 1, _arc(math.acos)),
    "atan": (1, 1, _arc(math.atan)),
    "atan2": (2, 2, lambda c, a: _from_radians(c, _from_float(math.atan2(float(a[0]), float(a[1]))))),
    "sinh": (1, 1, lambda c, a: _from_float(math.sinh(float(a[0])))),
    "cosh": (1, 1, lambda c, a: _from_float(math.cosh(float(a[0])))),
    "tanh": (1, 1, lambda c, a: _from_float(math.tanh(float(a[0])))),
    "asinh": (1, 1, lambda c, a: _from_float(math.asinh(float(a[0])))),
    "acosh": (1, 1, lambda c, a: _from_float(math.acosh(float(a[0])))),
    "atanh": (1, 1, lambda c, a: _from_float(math.atanh(float(a[0])))),
}


# ------------------------------------------------------------------ parsing

class _Parser:
    def __init__(self, tokens: list[Token], ctx: Context) -> None:
        self.tokens = tokens
        self.index = 0
        self.ctx = ctx

    # -- token helpers
    def peek(self, offset: int = 0) -> Token:
        position = self.index + offset
        if position >= len(self.tokens):
            return Token("eof", "", -1)
        return self.tokens[position]

    def advance(self) -> Token:
        token = self.peek()
        self.index += 1
        return token

    def at_op(self, *operators: str) -> bool:
        token = self.peek()
        return token.kind == "op" and token.text in operators

    def at_word(self, *words: str) -> bool:
        token = self.peek()
        return token.kind == "name" and token.text in words

    def expect(self, kind: str, what: str) -> Token:
        token = self.peek()
        if token.kind != kind:
            raise CalcError("expected {0}".format(what))
        return self.advance()

    # -- grammar
    def parse(self) -> Decimal:
        value = self.bitor()
        if self.peek().kind != "eof":
            token = self.peek()
            raise CalcError("unexpected '{0}'".format(token.text or "end"))
        return value

    def bitor(self) -> Decimal:
        value = self.bitxor()
        while self.at_op("|"):
            self.advance()
            value = Decimal(integral(value) | integral(self.bitxor()))
        return value

    def bitxor(self) -> Decimal:
        value = self.bitand()
        while self.at_word("xor"):
            self.advance()
            value = Decimal(integral(value) ^ integral(self.bitand()))
        return value

    def bitand(self) -> Decimal:
        value = self.shift()
        while self.at_op("&"):
            self.advance()
            value = Decimal(integral(value) & integral(self.shift()))
        return value

    def shift(self) -> Decimal:
        value = self.sum()
        while self.at_op("<<", ">>"):
            operator = self.advance().text
            amount = integral(self.sum())
            if amount < 0 or amount > 256:
                raise CalcError("shifts are limited to 0-256 bits")
            value = Decimal(integral(value) << amount) if operator == "<<" else Decimal(integral(value) >> amount)
        return value

    def sum(self) -> Decimal:
        value = self.term()
        while self.at_op("+", "-"):
            operator = self.advance().text
            right = self.term()
            value = value + right if operator == "+" else value - right
        return value

    def term(self) -> Decimal:
        value = self.unary()
        while True:
            if self.at_op("*", "/"):
                operator = self.advance().text
                right = self.unary()
                if operator == "*":
                    value = value * right
                else:
                    if right == 0:
                        raise CalcError("division by zero")
                    value = value / right
                continue
            # Implicit multiplication: 2pi, 3(4+5), (2)(3), 2sin(30).
            # `xor` is an operator word, not an operand.
            nxt = self.peek()
            if nxt.kind in ("num", "lparen") or (nxt.kind == "name" and nxt.text != "xor"):
                value = value * self.unary()
                continue
            return value

    def unary(self) -> Decimal:
        if self.at_op("+"):
            self.advance()
            return self.unary()
        if self.at_op("-"):
            self.advance()
            return -self.unary()
        if self.at_op("~"):
            self.advance()
            return Decimal(~integral(self.unary()))
        return self.power()

    def power(self) -> Decimal:
        base = self.postfix()
        if self.at_op("^"):
            self.advance()
            return self._power(base, self.unary())
        return base

    def postfix(self) -> Decimal:
        value = self.primary()
        while self.at_op("!", "%"):
            operator = self.advance().text
            if operator == "!":
                value = _factorial(self.ctx, [value])
            else:
                value = value / 100
        return value

    def primary(self) -> Decimal:
        token = self.peek()
        if token.kind == "num":
            self.advance()
            return parse_literal(token.text)
        if token.kind == "lparen":
            self.advance()
            value = self.bitor()
            self.expect("rparen", "')'")
            return value
        if token.kind == "name":
            return self.name(token)
        if token.kind == "eof":
            raise CalcError("the expression ends too early")
        raise CalcError("unexpected '{0}'".format(token.text))

    def name(self, token: Token) -> Decimal:
        word = token.text
        self.advance()
        if self.peek().kind == "lparen":
            self.advance()
            return self.call(word)
        if word in FUNCTIONS and self.peek().kind in ("num", "name"):
            # Bare-argument call: sqrt 9, sin 30. The argument binds as a power,
            # so ``sin 2^2`` is sin(4) and ``sin 2 + 3`` is sin(2) + 3.
            return self.apply(word, [self.unary()])
        return self.value_of(word)

    def call(self, word: str) -> Decimal:
        args: list[Decimal] = []
        if self.peek().kind != "rparen":
            args.append(self.bitor())
            while self.peek().kind == "comma":
                self.advance()
                args.append(self.bitor())
        self.expect("rparen", "')'")
        return self.apply(word, args)

    def apply(self, word: str, args: list[Decimal]) -> Decimal:
        if word not in FUNCTIONS:
            raise CalcError("'{0}' is not a function".format(word))
        low, high, impl = FUNCTIONS[word]
        if not low <= len(args) <= high:
            wanted = str(low) if low == high else "{0}-{1}".format(low, high)
            raise CalcError(
                "{0}() takes {1} argument{2}, got {3}".format(
                    word, wanted, "" if wanted == "1" else "s", len(args)
                )
            )
        return impl(self.ctx, args)

    def value_of(self, word: str) -> Decimal:
        if word == "ans":
            return self.ctx.ans
        if word in self.ctx.variables:
            return self.ctx.variables[word]
        if word in CONSTANTS:
            return CONSTANTS[word]
        raise CalcError("'{0}' is not defined".format(word))

    def _power(self, base: Decimal, exponent: Decimal) -> Decimal:
        if exponent == exponent.to_integral_value() and abs(exponent) <= 100000:
            power = int(exponent)
            if base == 0 and power == 0:
                return Decimal(1)  # the limit everywhere it matters; keeps 0^0 quiet
            if base == 0 and power < 0:
                raise CalcError("division by zero")
            try:
                return base ** power
            except DecimalException:
                raise CalcError("the result is out of range") from None
        if base < 0:
            raise CalcError("a negative number to a fractional power is not real")
        if base == 0:
            return Decimal(0)
        # decimal can raise a positive base to a fractional power itself, which
        # keeps sqrt(2) at working precision; float is the fallback for the
        # corners where decimal refuses (e.g. absurdly large exponents).
        try:
            return base ** exponent
        except DecimalException:
            pass
        try:
            return _from_float(math.pow(float(base), float(exponent)))
        except (ValueError, OverflowError):
            raise CalcError("the result is out of range") from None


# -------------------------------------------------------------------- entry

def evaluate(source: str, ctx: Context | None = None) -> Decimal:
    """Evaluate one expression, rounded to the context's display precision."""
    context = ctx if ctx is not None else Context()
    if not source or not source.strip():
        raise CalcError("nothing to calculate")
    tokens = tokenize(source)
    if not tokens:
        raise CalcError("nothing to calculate")
    with localcontext() as active:
        active.prec = work_precision(context.precision)
        active.rounding = ROUND_HALF_EVEN
        try:
            value = _Parser(tokens, context).parse()
        except DecimalException:
            raise CalcError("the calculation is not valid") from None
        except RecursionError:
            raise CalcError("the expression is nested too deeply") from None
        return round_to(value, context.precision)
