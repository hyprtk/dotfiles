"""``hyprtk-calc`` in the shell: one expression, one line, no window.

    hyprtk-calc "2 + 2 * 3"
    hyprtk-calc -p 20 "1/3"
    echo "sqrt(2)" | hyprtk-calc -
    hyprtk-calc --history

Exit status is 0 on success and 1 on a calculation error, so it is usable in a
pipe. ``--json`` gives ``{"ok": …, "expression": …, "result": …}`` for scripts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal

from . import __version__
from .evaluator import Context, evaluate
from .history import History
from .number import CalcError, all_bases, format_number
from .settings import ANGLES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hyprtk-calc",
        description="Evaluate expressions from the shell (hyprtk-calc's CLI).",
    )
    parser.add_argument("expression", nargs="*",
                        help="expression to evaluate; '-' reads stdin, one per line")
    parser.add_argument("-p", "--precision", type=int, help="significant digits")
    parser.add_argument("-a", "--angle", choices=ANGLES, help="angle unit (deg, rad, grad)")
    parser.add_argument("-b", "--base", type=int, choices=(2, 8, 10, 16), help="output base")
    parser.add_argument("-g", "--grouping", choices=("none", "thin", "space", "comma"),
                        help="digit grouping")
    parser.add_argument("--all-bases", action="store_true", help="print the four-base readout")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--history", action="store_true", help="print recent history and exit")
    parser.add_argument("--clear-history", action="store_true", help="empty the history and exit")
    parser.add_argument("-n", "--count", type=int, default=20, help="history rows to print")
    parser.add_argument("-V", "--version", action="version", version="hyprtk-calc " + __version__)
    return parser


def _context(args, answer: Decimal = Decimal(0)) -> Context:
    context = Context(precision=args.precision or Context().precision, angle=args.angle or "deg")
    context.ans = answer
    return context


def _print_history(args) -> int:
    rows = History().newest_first(max(1, args.count))
    if args.json:
        print(json.dumps([row.as_row() for row in rows], indent=2))
        return 0
    if not rows:
        return 0
    width = max(len(row.expression) for row in rows)
    for row in rows:
        print("{0}  =  {1}".format(row.expression.ljust(width), row.result))
    return 0


def run_one(text: str, args, answer: Decimal = Decimal(0)) -> tuple:
    """Returns (display, decimal or None, error or "")."""
    context = _context(args, answer)
    base = args.base or 10
    grouping = args.grouping or "none"
    try:
        value = evaluate(text, context)
    except CalcError as exc:
        return "", None, str(exc)
    return format_number(value, context.precision, base=base, grouping=grouping), value, ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.clear_history:
        removed = len(History())
        History().clear()
        if not args.json:
            print("cleared {0} history entr{1}".format(removed, "y" if removed == 1 else "ies"))
        return 0
    if args.history:
        return _print_history(args)

    answer = Decimal(0)
    sources: list[str] = []
    if args.expression and args.expression != ["-"]:
        sources = [" ".join(args.expression)]
        single = True
    else:
        if sys.stdin.isatty():
            print("hyprtk-calc: give an expression, or pipe one in with '-'", file=sys.stderr)
            return 2
        single = False
        sources = [line for line in sys.stdin.read().splitlines()]

    status = 0
    for text in sources:
        if not text.strip():
            continue
        display, value, error = run_one(text, args, answer)
        if args.json:
            record = {
                "ok": value is not None,
                "expression": text.strip(),
                "result": display,
                "precision": (args.precision or Context().precision),
            }
            if value is not None and args.all_bases:
                record["bases"] = {
                    str(base): number for base, number in all_bases(value).items()
                }
            if error:
                record["error"] = error
            print(json.dumps(record))
        elif single and args.all_bases and value is not None:
            for base, number in all_bases(value).items():
                print("{0}  {1}".format(str(base).rjust(3), number))
        elif display:
            print(display)
        if error:
            print("hyprtk-calc: " + error, file=sys.stderr)
            status = 1
        if value is not None:
            answer = value
    return status


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
