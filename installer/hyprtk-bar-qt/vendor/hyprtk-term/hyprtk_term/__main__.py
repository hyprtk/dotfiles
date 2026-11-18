"""``python -m hyprtk_term`` entry point."""

from __future__ import annotations

import os
import sys

from . import BIN_NAME, __version__
from .app import run

HELP = f"""usage: {BIN_NAME} [OPTION]... [-- COMMAND [ARG]...]

A fast, theme-aware terminal emulator for the hyprtk desktop.

  -e, --exec CMD...    run CMD instead of the login shell
  -d, --directory DIR  start in DIR
  -V, --version        print the version and exit
  -h, --help           this help

Keys: Ctrl+Shift+T new tab, Ctrl+Shift+W close tab, Ctrl+Shift+C/V copy/paste,
Ctrl+Shift+N/P previous/next tab, Ctrl+plus/minus zoom, Ctrl+comma settings.
"""


def _parse(argv: list[str]) -> tuple[list[str], str | None]:
    """Split argv into (command, directory); everything else is Qt's."""
    command: list[str] = []
    cwd: str | None = None
    args = list(argv[1:])
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-e", "--exec"):
            command = args[i + 1:]
            break
        if arg == "--":
            command = args[i + 1:]
            break
        if arg in ("-d", "--directory", "--working-directory"):
            if i + 1 < len(args):
                cwd = os.path.expanduser(args[i + 1])
            i += 2
            continue
        if arg.startswith("--working-directory="):
            cwd = os.path.expanduser(arg.split("=", 1)[1])
        i += 1
    return command, cwd


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv)
    if "--version" in argv or "-V" in argv:
        from . import vtcapi
        print(f"{BIN_NAME} {__version__} (libvterm via {vtcapi.library_path()})")
        return 0
    if "--help" in argv or "-h" in argv:
        print(HELP)
        return 0

    command, cwd = _parse(argv)
    return run([argv[0], "-name", "hyprtk-term"],
               startup_argv=command or None, cwd=cwd)


if __name__ == "__main__":
    raise SystemExit(main())
