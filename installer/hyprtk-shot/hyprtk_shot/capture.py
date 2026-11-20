"""Screen capture and Hyprland geometry.

Everything here is a thin, testable layer over two external programs:

* ``grim`` — captures an output, a region or the whole layout to PNG bytes.
* ``hyprctl`` — reports monitors (to pick an output) and clients (to capture a
  window without asking the user to draw a box around it).

No Qt import: the CLI must work on a box where PySide6 is missing or broken,
and the geometry maths is easier to test as plain numbers.

Coordinates: Hyprland reports window and monitor geometry in *logical* pixels,
which is exactly what ``grim -g`` wants; ``grim -o`` and a bare ``grim`` do the
pixel-size conversion themselves. An output's own pixel size is
``width x height``; its logical size is that divided by ``scale``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass

GRIM = os.environ.get("HYPRTK_SHOT_GRIM", "grim")
SLURP = os.environ.get("HYPRTK_SHOT_SLURP", "slurp")
HYPRCTL = os.environ.get("HYPRTK_SHOT_HYPRCTL", "hyprctl")

MODES = ("region", "window", "output", "full")


class CaptureError(RuntimeError):
    """A capture could not be taken; the message is safe to show a user."""


# --------------------------------------------------------------- external ---

def which(program: str) -> str | None:
    return shutil.which(program)


def have(program: str) -> bool:
    return which(program) is not None


def _run(argv: list[str], *, timeout: float = 20.0, stdin: bytes | None = None):
    try:
        return subprocess.run(
            argv,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CaptureError(f"{argv[0]} is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise CaptureError(f"{argv[0]} timed out") from exc


def _hyprctl_json(args: list[str]):
    if not have(HYPRCTL):
        return None
    result = _run([HYPRCTL, *args, "-j"], timeout=5.0)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout.decode("utf-8", "replace") or "null")
    except ValueError:
        return None


# ---------------------------------------------------------------- geometry ---

@dataclass(frozen=True)
class Output:
    name: str
    x: int
    y: int
    width: int          # physical pixels
    height: int         # physical pixels
    scale: float
    focused: bool
    refresh: float = 0.0

    @property
    def logical_width(self) -> int:
        return max(1, round(self.width / (self.scale or 1.0)))

    @property
    def logical_height(self) -> int:
        return max(1, round(self.height / (self.scale or 1.0)))

    @property
    def geometry(self) -> str:
        """Logical ``x,y WxH``, the format ``grim -g`` and ``wf-recorder -g`` use."""
        return f"{self.x},{self.y} {self.logical_width}x{self.logical_height}"

    def as_row(self) -> dict:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.logical_width,
            "height": self.logical_height,
            "scale": self.scale,
            "focused": self.focused,
        }


@dataclass(frozen=True)
class Window:
    address: str
    title: str
    app_class: str
    x: int
    y: int
    width: int
    height: int
    monitor: int
    floating: bool
    focus_order: int

    @property
    def geometry(self) -> str:
        return f"{self.x},{self.y} {self.width}x{self.height}"

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def as_row(self) -> dict:
        return {
            "address": self.address,
            "title": self.title or self.app_class,
            "class": self.app_class,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "geometry": self.geometry,
        }


def _monitor_row(data: dict) -> Output:
    try:
        return Output(
            name=str(data.get("name") or ""),
            x=int(data.get("x") or 0),
            y=int(data.get("y") or 0),
            width=int(data.get("width") or 0),
            height=int(data.get("height") or 0),
            scale=float(data.get("scale") or 1.0),
            focused=bool(data.get("focused")),
            refresh=float(data.get("refreshRate") or 0.0),
        )
    except (TypeError, ValueError) as exc:
        raise CaptureError("hyprctl reported a monitor with invalid geometry") from exc


def outputs() -> list[Output]:
    data = _hyprctl_json(["monitors"])
    if not isinstance(data, list):
        return []
    rows = [_monitor_row(item) for item in data if isinstance(item, dict)]
    return [row for row in rows if row.name]


def focused_output(rows: list[Output] | None = None) -> Output | None:
    rows = outputs() if rows is None else rows
    for row in rows:
        if row.focused:
            return row
    return rows[0] if rows else None


def windows(*, visible_only: bool = True) -> list[Window]:
    data = _hyprctl_json(["clients"])
    if not isinstance(data, list):
        return []
    result: list[Window] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if visible_only and (item.get("hidden") or item.get("mapped") is False):
            continue
        try:
            at = item.get("at") or (0, 0)
            size = item.get("size") or (0, 0)
            result.append(Window(
                address=str(item.get("address") or ""),
                title=str(item.get("title") or ""),
                app_class=str(item.get("class") or item.get("initialClass") or ""),
                x=int(at[0]),
                y=int(at[1]),
                width=int(size[0]),
                height=int(size[1]),
                monitor=int(item.get("monitor") or 0),
                floating=bool(item.get("floating")),
                focus_order=int(item.get("focusHistoryID") or 0),
            ))
        except (TypeError, ValueError, IndexError):
            continue
    return [row for row in result if row.width > 0 and row.height > 0]


def active_window() -> Window | None:
    rows = windows()
    return min(rows, key=lambda row: row.focus_order, default=None) if rows else None


def window_at(x: float, y: float, rows: list[Window] | None = None) -> Window | None:
    """Topmost window under a point.

    Hyprland does not publish a stacking list through ``hyprctl``; the focus
    history is the closest reliable proxy (0 is the most recently focused), and
    it matches what the user sees for every non-overlapping window.
    """
    rows = windows() if rows is None else rows
    hits = [row for row in rows if row.contains(x, y)]
    return min(hits, key=lambda row: row.focus_order, default=None)


def select_region(*, slurp: str | None = None) -> str | None:
    """Ask slurp for a region; ``None`` means the user cancelled."""
    program = slurp or SLURP
    if not have(program):
        raise CaptureError("slurp is not installed (region selection needs it)")
    result = _run([program], timeout=600.0)
    if result.returncode != 0:
        return None
    geometry = result.stdout.decode("utf-8", "replace").strip()
    return geometry or None


# ---------------------------------------------------------------- capture ---

def grim_argv(
    mode: str = "region",
    *,
    geometry: str | None = None,
    output: str | None = None,
    cursor: bool = False,
    image_format: str = "png",
    quality: int = 90,
    program: str | None = None,
) -> list[str]:
    """Build the grim command for a mode; raises rather than guessing.

    ``mode`` is one of :data:`MODES`. ``region`` and ``window`` need a geometry,
    ``output`` prefers a name (grim then handles scale itself) and ``full``
    captures the whole layout with no arguments.
    """
    if mode not in MODES:
        raise CaptureError(f"unknown capture mode: {mode}")
    argv = [program or GRIM]
    if mode in ("region", "window"):
        if geometry:
            argv += ["-g", geometry]
        elif mode == "region" and output:
            # The overlay selects inside a single frozen monitor; grim names
            # that monitor and does the scale conversion itself.
            argv += ["-o", output]
        else:
            raise CaptureError(f"{mode} capture needs a geometry")
    elif mode == "output":
        # An output can be named or addressed by its logical geometry; the name
        # is preferable, because grim then applies the output's own scale.
        if output:
            argv += ["-o", output]
        elif geometry:
            argv += ["-g", geometry]
        else:
            raise CaptureError("output capture needs an output name or geometry")
    if cursor:
        argv.append("-c")
    if image_format != "png":
        argv += ["-t", image_format]
        if image_format == "jpeg":
            argv += ["-q", str(max(1, min(100, int(quality))))]
    argv.append("-")
    return argv


def capture(
    mode: str = "region",
    *,
    geometry: str | None = None,
    output: str | None = None,
    cursor: bool = False,
    image_format: str = "png",
    quality: int = 90,
) -> bytes:
    """Capture to bytes. Raises :class:`CaptureError` with a usable message."""
    if not have(GRIM):
        raise CaptureError("grim is not installed")
    argv = grim_argv(
        mode,
        geometry=geometry,
        output=output,
        cursor=cursor,
        image_format=image_format,
        quality=quality,
    )
    result = _run(argv, timeout=60.0)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CaptureError(detail or "grim failed to capture the screen")
    if not result.stdout:
        raise CaptureError("grim returned an empty image")
    return result.stdout


def resolve_target(
    mode: str,
    *,
    region: str | None = None,
    output: str | None = None,
    window: str | None = None,
) -> dict:
    """Work out what to capture, before any pixels move.

    Returns a dict with ``mode``, ``geometry``, ``output``, ``label`` and
    ``logical_width`` (the width the user sees, for stroke scaling).

    **Region does not select anything here.** The overlay is the selector: this
    grabs the focused output whole (`grim -o`), the user draws the box on the
    frozen frame, and the selection becomes the crop. That keeps the
    fast keypress path free of a second, separate selection UI. An explicit
    ``region`` geometry is honoured for scripting (`--region "x,y WxH"`);
    drawing across several outputs with slurp is a v0.2 option.
    """
    if mode not in MODES:
        raise CaptureError(f"unknown capture mode: {mode}")

    monitor = focused_output()

    if mode == "region":
        if region:
            return {
                "mode": mode,
                "geometry": region,
                "output": None,
                "label": "Region",
                "logical_width": None,
            }
        if monitor is None:
            raise CaptureError("no monitor reported by Hyprland")
        return {
            "mode": mode,
            "geometry": None,
            "output": monitor.name,
            "label": f"Region · {monitor.name}",
            "logical_width": monitor.logical_width,
        }

    if mode == "window":
        target_window = None
        if window:
            target_window = next((row for row in windows() if row.address == window), None)
        target_window = target_window or active_window()
        if target_window is None:
            raise CaptureError("no window to capture")
        return {
            "mode": mode,
            "geometry": target_window.geometry,
            "output": None,
            "label": target_window.title or target_window.app_class or "Window",
            "logical_width": target_window.width,
        }

    if mode == "output":
        target = output
        if not target:
            if monitor is None:
                raise CaptureError("no monitor reported by Hyprland")
            target = monitor.name
        return {
            "mode": mode,
            "geometry": None,
            "output": target,
            "label": target,
            "logical_width": monitor.logical_width if monitor and monitor.name == target else None,
        }

    rows = outputs()
    logical = sum(row.logical_width for row in rows) or None
    return {
        "mode": "full",
        "geometry": None,
        "output": None,
        "label": f"All outputs ({monitor.name})" if monitor else "All outputs",
        "logical_width": logical,
    }
