"""``python -m hyprtk_editor`` entry point."""

from __future__ import annotations

import sys

from . import BIN_NAME, __version__
from .app import run


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv)
    if "--version" in argv or "-V" in argv:
        print(f"{BIN_NAME} {__version__}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(
            f"usage: {BIN_NAME} [FILE ...]\n\n"
            "A fast, theme-aware text editor for the hyprtk desktop.\n\n"
            "  -V, --version   print the version and exit\n"
            "  -h, --help      this help\n"
        )
        return 0
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
