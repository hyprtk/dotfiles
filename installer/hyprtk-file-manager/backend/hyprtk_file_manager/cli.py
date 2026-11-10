"""Command line interface for hyprtk-file-manager."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from . import __version__
from . import places as places_mod
from . import rpc

APP_DIR = Path(__file__).resolve().parents[2]


def cmd_serve(_args) -> int:
    return rpc.serve()


def cmd_open(_args) -> int:
    subprocess.Popen(["qs", "-p", str(APP_DIR)])
    return 0


def cmd_version(_args) -> int:
    print(f"hyprtk-file-manager {__version__}")
    return 0


def cmd_places(_args) -> int:
    home = places_mod.home_dir()
    print(
        json.dumps(
            {
                "places": places_mod.places(home),
                "bookmarks": places_mod.bookmarks(home),
                "drives": places_mod.drives(),
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyprtk-fm", description="hyprtk file manager")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("open", help="open the GUI").set_defaults(func=cmd_open)
    sub.add_parser("serve", help="JSON-lines RPC over stdio").set_defaults(func=cmd_serve)
    sub.add_parser("places", help="dump places, bookmarks and drives").set_defaults(func=cmd_places)
    sub.add_parser("version", help="print the version").set_defaults(func=cmd_version)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "func", None):
        return cmd_open(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
