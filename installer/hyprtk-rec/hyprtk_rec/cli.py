"""The recorder's command line: start, stop, toggle, status.

``hyprtk-rec`` with no arguments is the window. Everything else is scriptable,
because the two things a recorder is always asked to do — start on a keypress
and stop on another — should not need a GUI at all.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from . import BIN_NAME, __version__
from .audio import AUDIO, device_for
from .recorder import CODECS, QUALITIES, Recorder, RecorderError
from .settings import Settings
from .sources import SOURCES, SourceError, outputs, resolve_source, windows
from .store import default_dir, human_duration, human_size, make_name, unique_path

USAGE = """\
usage: {bin} [command] [options]

commands:
  start         start recording (default when no command is given)
  stop          stop the running recording and finalize the file
  toggle        start if idle, stop if recording
  pause         freeze the encoder (SIGSTOP)
  resume        continue after pause (SIGCONT)
  status        print the current state
  sources       list monitors and windows Hyprland reports
  trim PATH     cut a finished file without re-encoding

options:
  -o, --source S      output | region | window            (default from settings)
      --output NAME   record a named monitor
      --region GEOM   "x,y WxH" instead of drawing with slurp
      --window ADDR   record a specific window by Hyprland address
      --fps N         5-240
      --codec C       h264 | hevc | vp9 | av1
      --quality Q     low | medium | high
      --audio A       none | system | mic
      --device NAME   a specific PulseAudio/PipeWire source
      --countdown N   seconds before recording starts
      --dir PATH      output directory
      --backend B     auto | wf-recorder | wl-screenrec
      --container C   mp4 | mkv | webm
      --no-cursor     hide the pointer

  trim options:
      --from T        start time (seconds, MM:SS or HH:MM:SS)
      --to T          end time (same formats; must be after --from)
      --last          trim the most recent recording
      --replace       overwrite the original instead of writing -trimmed
      --reencode      frame-accurate cut (slower; default is a keyframe copy)
      --json          machine-readable output
  -h, --help          this text
  -V, --version       version
"""

COMMANDS = ("start", "stop", "toggle", "pause", "resume", "status", "sources", "trim")


@dataclass
class Options:
    command: str = "start"
    source: str = ""
    output: str = ""
    region: str = ""
    window: str = ""
    fps: int | None = None
    codec: str = ""
    quality: str = ""
    audio: str = ""
    device: str = ""
    countdown: int | None = None
    directory: str = ""
    backend: str = ""
    container: str = ""
    cursor: bool | None = None
    path: str = ""
    start: str = ""
    end: str = ""
    replace: bool = False
    reencode: bool = False
    last: bool = False
    json: bool = False
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
        elif arg == "--json":
            opts.json = True
        elif arg in ("-o", "--source"):
            index += 1
            if index >= len(argv):
                raise ValueError("--source needs a value")
            opts.source = argv[index]
        elif arg.startswith("--source="):
            opts.source = arg.split("=", 1)[1]
        elif arg == "--output":
            index += 1
            opts.output = argv[index]
        elif arg == "--region":
            index += 1
            opts.region = argv[index]
        elif arg == "--window":
            index += 1
            opts.window = argv[index]
        elif arg == "--fps":
            index += 1
            opts.fps = int(argv[index])
        elif arg.startswith("--fps="):
            opts.fps = int(arg.split("=", 1)[1])
        elif arg == "--codec":
            index += 1
            opts.codec = argv[index]
        elif arg == "--quality":
            index += 1
            opts.quality = argv[index]
        elif arg == "--audio":
            index += 1
            opts.audio = argv[index]
        elif arg.startswith("--audio="):
            opts.audio = arg.split("=", 1)[1]
        elif arg == "--device":
            index += 1
            opts.device = argv[index]
        elif arg == "--countdown":
            index += 1
            opts.countdown = int(argv[index])
        elif arg == "--dir":
            index += 1
            opts.directory = argv[index]
        elif arg == "--backend":
            index += 1
            opts.backend = argv[index]
        elif arg == "--container":
            index += 1
            opts.container = argv[index]
        elif arg == "--from":
            index += 1
            opts.start = argv[index] if index < len(argv) else ""
        elif arg.startswith("--from="):
            opts.start = arg.split("=", 1)[1]
        elif arg == "--to":
            index += 1
            opts.end = argv[index] if index < len(argv) else ""
        elif arg.startswith("--to="):
            opts.end = arg.split("=", 1)[1]
        elif arg == "--replace":
            opts.replace = True
        elif arg == "--reencode":
            opts.reencode = True
        elif arg == "--last":
            opts.last = True
        elif arg == "--no-cursor":
            opts.cursor = False
        elif arg == "--cursor":
            opts.cursor = True
        elif arg in ("-t", "--toggle"):
            opts.command = "toggle"
        elif arg in ("-s", "--stop"):
            opts.command = "stop"
        elif arg.startswith("-"):
            raise ValueError(f"unknown option: {arg}")
        elif arg in COMMANDS:
            opts.command = arg
        elif opts.command == "trim" and not opts.path:
            opts.path = arg
        else:
            raise ValueError(f"unknown command: {arg}")
        index += 1
    return opts


def _apply(opts: Options, settings: Settings) -> Settings:
    if opts.source:
        settings.set("source", opts.source)
    if opts.fps is not None:
        settings.set("fps", opts.fps)
    if opts.codec:
        settings.set("codec", opts.codec)
    if opts.quality:
        settings.set("quality", opts.quality)
    if opts.audio:
        settings.set("audio", opts.audio)
    if opts.countdown is not None:
        settings.set("countdown", opts.countdown)
    if opts.directory:
        settings.set("dir", opts.directory)
    if opts.backend:
        settings.set("backend", opts.backend)
    if opts.container:
        settings.set("container", opts.container)
    if opts.window:
        settings.set("window", opts.window)
    if opts.cursor is not None:
        settings.set("cursor", opts.cursor)
    return settings


def cmd_trim(opts: Options) -> int:
    from . import trim
    from .store import History

    path = opts.path
    if not path and opts.last:
        rows = History().recent_paths(1)
        if not rows:
            print(f"{BIN_NAME}: no recordings in the history", file=sys.stderr)
            return 1
        path = str(rows[0]["path"])
    if not path:
        print(f"{BIN_NAME}: trim needs a file (or --last)", file=sys.stderr)
        return 2
    try:
        start = trim.parse_time(opts.start)
        end = trim.parse_time(opts.end)
        output = trim.run(path, start=start, end=end, replace=opts.replace,
                          reencode=opts.reencode)
    except trim.TrimError as exc:
        print(f"{BIN_NAME}: {exc}", file=sys.stderr)
        return 1
    size = 0
    try:
        size = Path(output).stat().st_size
    except OSError:
        pass
    if opts.json:
        print(json.dumps({"path": output, "bytes": size, "source": path,
                          "replaced": bool(opts.replace)}, sort_keys=True))
    else:
        print(f"wrote {output} ({human_size(size)})")
    return 0


def cmd_start(opts: Options, settings: Settings) -> int:
    recorder = Recorder()
    if recorder.active() is not None:
        print(f"{BIN_NAME}: already recording", file=sys.stderr)
        return 1
    source = str(settings.get("source") or "output")
    try:
        target = resolve_source(source, region=opts.region or None,
                                output=opts.output or None,
                                window=opts.window or str(settings.get("window") or "") or None)
    except SourceError as exc:
        message = str(exc)
        if message == "cancelled":
            return 3
        print(f"{BIN_NAME}: {message}", file=sys.stderr)
        return 1

    container = str(settings.get("container") or "mp4")
    base = Path(str(settings.get("dir") or default_dir())).expanduser()
    path = unique_path(base / make_name(source, ext=container))
    try:
        recording = recorder.start(
            path=str(path),
            source=source,
            geometry=target.get("geometry"),
            output=target.get("output"),
            codec=str(settings.get("codec") or "h264"),
            quality=str(settings.get("quality") or "medium"),
            fps=int(settings.get("fps") or 60),
            audio=str(settings.get("audio") or "none"),
            audio_device=opts.device or None,
            cursor=bool(settings.get("cursor")),
            backend=str(settings.get("backend") or "auto"),
            container=container,
        )
    except RecorderError as exc:
        print(f"{BIN_NAME}: {exc}", file=sys.stderr)
        return 1

    if opts.json:
        print(json.dumps({"recording": True, "path": recording.path,
                          "backend": recording.backend, "source": recording.source,
                          "pid": recording.pid}, sort_keys=True))
    else:
        print(f"recording {target.get('label')} → {recording.path} ({recording.backend})")
    return 0


def cmd_stop(opts: Options, settings: Settings) -> int:
    recorder = Recorder()
    before = recorder.status()
    path = recorder.stop()
    if path is None:
        if opts.json:
            print(json.dumps({"recording": False, "path": ""}))
        else:
            print(f"{BIN_NAME}: not recording", file=sys.stderr)
        return 3
    size = 0
    try:
        size = Path(path).stat().st_size
    except OSError:
        pass
    if opts.json:
        print(json.dumps({"recording": False, "path": path, "bytes": size,
                          "duration": before.get("elapsed", 0)}, sort_keys=True))
    else:
        print(f"saved {path} ({human_size(size)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    # Internal helper, spawned detached by the window: it must block while the
    # notification is on screen, which is exactly what the app cannot do.
    if argv[:1] == ["notify-saved"]:
        from . import notify

        return notify.run(argv[1] if len(argv) > 1 else "")
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

    settings = _apply(opts, Settings())
    recorder = Recorder()

    if opts.command == "status":
        status = recorder.status()
        if opts.json:
            print(json.dumps(status, sort_keys=True))
        elif status.get("recording"):
            print(f"recording {human_duration(status.get('elapsed', 0))} "
                  f"→ {status.get('path')} ({status.get('backend')})"
                  f"{' [paused]' if status.get('paused') else ''}")
        else:
            print("idle")
        return 0

    if opts.command == "toggle":
        if recorder.active() is not None:
            opts.command = "stop"
        else:
            opts.command = "start"

    if opts.command == "stop":
        return cmd_stop(opts, settings)

    if opts.command in ("pause", "resume"):
        ok = recorder.pause() if opts.command == "pause" else recorder.resume()
        if not ok:
            print(f"{BIN_NAME}: not recording", file=sys.stderr)
            return 3
        print(opts.command + "d")
        return 0

    if opts.command == "trim":
        return cmd_trim(opts)

    if opts.command == "sources":
        for row in outputs():
            print(f"monitor {row.name:<12} {row.geometry:<20} {row.fps} Hz"
                  f"{'  (focused)' if row.focused else ''}")
        for row in windows():
            print(f"window  {row.geometry:<20} {row.app_class}: {row.title[:60]}")
        return 0

    if opts.source and opts.source not in SOURCES:
        print(f"{BIN_NAME}: unknown source: {opts.source}", file=sys.stderr)
        return 2
    if opts.audio and opts.audio not in AUDIO:
        print(f"{BIN_NAME}: unknown audio mode: {opts.audio}", file=sys.stderr)
        return 2
    if opts.codec and opts.codec not in CODECS:
        print(f"{BIN_NAME}: unknown codec: {opts.codec}", file=sys.stderr)
        return 2
    if opts.quality and opts.quality not in QUALITIES:
        print(f"{BIN_NAME}: unknown quality: {opts.quality}", file=sys.stderr)
        return 2

    return cmd_start(opts, settings)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
