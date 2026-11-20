"""What to record: outputs, windows and a region, from Hyprland itself.

The recorder never guesses at a source. Outputs come from ``hyprctl monitors``,
windows from ``hyprctl clients`` (the same geometry ``grim`` and ``wf-recorder``
accept), and a region from ``slurp`` when the user picks one.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass

HYPRCTL = os.environ.get("HYPRTK_REC_HYPRCTL", "hyprctl")
SLURP = os.environ.get("HYPRTK_REC_SLURP", "slurp")

SOURCES = ("output", "region", "window")


class SourceError(RuntimeError):
    """No usable capture source; the message is safe to show a user."""


@dataclass(frozen=True)
class Output:
    name: str
    x: int
    y: int
    width: int
    height: int
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
        return f"{self.x},{self.y} {self.logical_width}x{self.logical_height}"

    @property
    def fps(self) -> int:
        return max(1, min(240, round(self.refresh or 60)))

    def as_row(self) -> dict:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.logical_width,
            "height": self.logical_height,
            "scale": self.scale,
            "focused": self.focused,
            "fps": self.fps,
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
            "width": self.width,
            "height": self.height,
            "geometry": self.geometry,
        }


def which(program: str) -> str | None:
    return shutil.which(program)


def have(program: str) -> bool:
    return which(program) is not None


def _run(argv: list[str], *, timeout: float = 15.0):
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise SourceError(f"{argv[0]} is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"{argv[0]} timed out") from exc


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
            refresh=float(data.get("refreshRate") or 60.0),
        )
    except (TypeError, ValueError) as exc:
        raise SourceError("hyprctl reported a monitor with invalid geometry") from exc


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


def select_region() -> str | None:
    if not have(SLURP):
        raise SourceError("slurp is not installed (region recording needs it)")
    result = _run([SLURP], timeout=600.0)
    if result.returncode != 0:
        return None
    geometry = result.stdout.decode("utf-8", "replace").strip()
    return geometry or None


def resolve_source(source: str, *, region: str | None = None,
                   output: str | None = None) -> dict:
    """Work out the target before the recorder starts.

    Returns ``{"source", "geometry", "output", "label"}``. A region runs slurp
    here, so cancelling happens before a countdown begins.
    """
    if source not in SOURCES:
        raise SourceError(f"unknown source: {source}")

    if source == "region":
        geometry = region or select_region()
        if not geometry:
            raise SourceError("cancelled")
        return {"source": "region", "geometry": geometry, "output": None, "label": "Region"}

    if source == "window":
        window = active_window()
        if window is None:
            raise SourceError("no window to record")
        return {
            "source": "window",
            "geometry": window.geometry,
            "output": None,
            "label": window.title or window.app_class or "Window",
        }

    monitor = None if output else focused_output()
    target = output or (monitor.name if monitor else None)
    if not target:
        raise SourceError("no monitor reported by Hyprland")
    return {"source": "output", "geometry": None, "output": target, "label": target}
