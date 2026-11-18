"""Entry point: a shell calculator when given work, a window when not.

``hyprtk-calc "2+2"`` prints, ``echo 2+2 | hyprtk-calc -`` prints, and a bare
``hyprtk-calc`` (from the bar, a keybinding or the desktop entry) opens the GUI.
The GUI is imported lazily so the CLI keeps working on a machine without Qt,
and a bare launch never guesses: no arguments means the window.
"""

from __future__ import annotations

import sys

CLI_FLAGS = {
    "-p", "--precision", "-a", "--angle", "-b", "--base", "-g", "--grouping",
    "--all-bases", "--json", "--history", "--clear-history", "-n", "--count",
    "-h", "--help", "-V", "--version",
}


def wants_cli(argv: list[str]) -> bool:
    # A bare launch is the window, always: the desktop entry, a keybinding and
    # the bar all start the process without a tty, and none of them want a
    # calculator that exits instantly having read nothing from stdin.
    if not argv:
        return False
    for arg in argv:
        if arg in CLI_FLAGS or any(arg.startswith(flag + "=") for flag in CLI_FLAGS if flag.startswith("--")):
            return True
    # A bare argument is an expression, not a file to open.
    return True


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if wants_cli(argv):
        from .cli import main as cli_main

        return cli_main(argv)
    from .app import run

    return run([sys.argv[0]] + argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
