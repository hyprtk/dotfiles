"""Entry point: a window with no arguments, the command line with any.

A bare ``hyprtk-shot`` is the launcher window (desktop entry, bar, menu). Any
argument goes through :mod:`hyprtk_shot.cli`, which either acts immediately or
opens the capture overlay.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        from .app import run

        return run(sys.argv)
    from .cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
