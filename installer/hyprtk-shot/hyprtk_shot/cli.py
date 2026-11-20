"""The command line: capture-and-act without the editor, or open the editor.

``hyprtk-shot`` (no arguments) is the launcher window. ``hyprtk-shot region``
is what a keybinding calls: freeze, select, annotate, save/copy. The flags
exist so the same binary can be scripted: ``--stdout`` for a pipe, ``--json``
for status, ``--no-edit`` for a straight save, and ``--list-outputs`` to see
what grim will be pointed at.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import BIN_NAME, __version__
from .capture import CaptureError, MODES, capture, outputs, resolve_target
from .settings import Settings
from .store import copy_to_clipboard, default_dir, human_size, make_name, save_image, unique_path

USAGE = """\
usage: {bin} [mode] [options]

modes:
  region          drag a region (default)            window   the focused window
  output          the focused monitor                full     all outputs
  last            reopen the most recent capture in the editor
  open PATH       open any image in the editor

options:
  -d, --delay N   seconds before capturing (0-30)
  -c, --copy      copy the result to the clipboard (default from settings)
      --no-copy   do not copy
      --region G  capture "x,y WxH" instead of selecting on the overlay
  -s, --save P    save to P (a directory, or a file name)
      --no-save   do not write a file
      --stdout    write PNG bytes to stdout, no file, no editor
      --no-edit   capture straight to disk/clipboard, no overlay
      --cursor    include the cursor
      --json      print a JSON result
      --list-outputs   list monitors Hyprland reports
  -h, --help      this text
  -V, --version   version
"""


@dataclass
class Options:
    mode: str = ""
    file: str = ""
    delay: int | None = None
    copy: bool | None = None
    region: str = ""
    save: str = ""
    no_save: bool = False
    stdout: bool = False
    edit: bool | None = None
    cursor: bool | None = None
    json: bool = False
    list_outputs: bool = False
    help: bool = False
    version: bool = False


def parse(argv: list[str]) -> Options:
    opts = Options()
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("-h", "--help"):
            opts.help = True
        elif arg in ("-V", "--version"):
            opts.version = True
        elif arg in ("-c", "--copy"):
            opts.copy = True
        elif arg == "--no-copy":
            opts.copy = False
        elif arg in ("-d", "--delay"):
            index += 1
            if index >= len(argv):
                raise ValueError("--delay needs a number")
            opts.delay = int(argv[index])
        elif arg.startswith("--delay="):
            opts.delay = int(arg.split("=", 1)[1])
        elif arg in ("-s", "--save"):
            index += 1
            if index >= len(argv):
                raise ValueError("--save needs a path")
            opts.save = argv[index]
        elif arg.startswith("--save="):
            opts.save = arg.split("=", 1)[1]
        elif arg == "--region":
            index += 1
            if index >= len(argv):
                raise ValueError("--region needs a geometry")
            opts.region = argv[index]
        elif arg.startswith("--region="):
            opts.region = arg.split("=", 1)[1]
        elif arg == "--no-save":
            opts.no_save = True
        elif arg == "--stdout":
            opts.stdout = True
        elif arg in ("--no-edit", "--no-ui"):
            opts.edit = False
        elif arg == "--edit":
            opts.edit = True
        elif arg == "--cursor":
            opts.cursor = True
        elif arg == "--json":
            opts.json = True
        elif arg == "--list-outputs":
            opts.list_outputs = True
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        elif not opts.mode:
            if arg not in MODES and arg not in ("last", "open"):
                raise ValueError(f"unknown mode: {arg}")
            opts.mode = arg
        elif opts.mode in ("last", "open") and not opts.file:
            opts.file = arg
        else:
            raise ValueError(f"unexpected argument: {arg}")
        index += 1
    return opts


def _save_path(opts: Options, settings: Settings, mode: str) -> Path:
    fmt = str(settings.get("format") or "png")
    if opts.save:
        target = Path(opts.save).expanduser()
        if target.is_dir() or opts.save.endswith("/"):
            target = target / make_name(mode, ext=fmt)
        elif not target.suffix:
            target = target.with_suffix("." + fmt)
        return unique_path(target)
    base = Path(str(settings.get("dir") or default_dir())).expanduser()
    return unique_path(base / make_name(mode, ext=fmt))


def _quick_capture(opts: Options, settings: Settings) -> int:
    """The no-editor path: capture, save and/or copy, optionally print JSON."""
    mode = opts.mode or str(settings.get("mode") or "region")
    if opts.cursor is not None:
        settings.set("cursor", opts.cursor)
    if mode == "region" and not opts.region:
        print(f'{BIN_NAME}: region capture without the editor needs --region "x,y WxH"',
              file=sys.stderr)
        return 2
    try:
        target = resolve_target(mode, region=opts.region or None)
        data = capture(
            mode,
            geometry=target.get("geometry"),
            output=target.get("output"),
            cursor=bool(settings.get("cursor")),
        )
    except CaptureError as exc:
        message = str(exc)
        if message == "cancelled":
            return 3
        print(f"{BIN_NAME}: {message}", file=sys.stderr)
        return 1

    if opts.stdout:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return 0

    want_save = not opts.no_save and bool(settings.get("save"))
    want_copy = bool(opts.copy if opts.copy is not None else settings.get("copy"))
    path = None
    width = height = 0

    if want_save:
        path = _save_path(opts, settings, mode)
        if path.suffix.lower() in (".png", ".PNG"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        else:
            from PySide6.QtGui import QImage

            image = QImage.fromData(data, "PNG")
            if image.isNull():
                print(f"{BIN_NAME}: could not decode the capture", file=sys.stderr)
                return 1
            width, height = image.width(), image.height()
            path = save_image(image, path, quality=int(settings.get("quality")))
    if want_copy and not copy_to_clipboard(data):
        print(f"{BIN_NAME}: clipboard unavailable (install wl-clipboard)", file=sys.stderr)

    if path is not None and not width:
        try:
            from PySide6.QtGui import QImage

            image = QImage.fromData(data, "PNG")
            width, height = image.width(), image.height()
        except Exception:
            pass

    if opts.json:
        payload = {
            "mode": mode,
            "path": str(path) if path else "",
            "copied": bool(want_copy),
            "bytes": len(data),
            "width": width,
            "height": height,
        }
        print(json.dumps(payload, sort_keys=True))
    elif path:
        print(f"saved {path} ({human_size(len(data))})")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    try:
        opts = parse(argv)
    except ValueError as exc:
        print(f"{BIN_NAME}: {exc}", file=sys.stderr)
        print(USAGE.format(bin=BIN_NAME), file=sys.stderr, end="")
        return 2

    if opts.help:
        print(USAGE.format(bin=BIN_NAME), end="")
        return 0
    if opts.version:
        print(f"{BIN_NAME} {__version__}")
        return 0

    settings = Settings()

    if opts.list_outputs:
        rows = outputs()
        for row in rows:
            print(("%-12s %5dx%-5d +%d+%d scale %.2f%s"
                   % (row.name, row.logical_width, row.logical_height, row.x, row.y,
                      row.scale, "  (focused)" if row.focused else "")))
        return 0

    mode = opts.mode or str(settings.get("mode") or "region")

    if opts.delay is not None:
        settings.set("delay", max(0, min(30, opts.delay)))
    if opts.cursor is not None:
        settings.set("cursor", opts.cursor)

    if mode == "open" or mode == "last":
        from .app import run
        from .store import History

        if mode == "open" and not opts.file:
            print(f"{BIN_NAME}: open needs an image path", file=sys.stderr)
            return 2
        if opts.file:
            target = Path(opts.file).expanduser()
            if not target.is_file():
                print(f"{BIN_NAME}: no such file: {target}", file=sys.stderr)
                return 1
            return run([sys.argv[0]], open_path=str(target))

        rows = History().recent_paths(1)
        if not rows:
            print(f"{BIN_NAME}: no captures in the history", file=sys.stderr)
            return 1
        return run([sys.argv[0]], open_path=str(rows[0]["path"]))

    want_edit = opts.edit if opts.edit is not None else bool(settings.get("annotate"))
    if opts.no_save:
        settings.set("save", False)
    if opts.copy is not None:
        settings.set("copy", opts.copy)

    if opts.stdout or not want_edit:
        if opts.delay:
            time.sleep(int(opts.delay))
        return _quick_capture(opts, settings)

    # The editor: capture inside the app, so the overlay can show the freeze
    # and the session keeps the full-resolution image.
    from .app import run

    overrides = {"copy": bool(opts.copy) if opts.copy is not None else None,
                 "save": False if opts.no_save else None}
    return run([sys.argv[0]], mode=mode, region=opts.region, overrides=overrides)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
