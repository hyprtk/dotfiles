"""The QML-facing facade: one capture session, one set of actions.

The CLI and the overlay share this object. It owns the frozen image, the
selection, the annotation list and the undo stack, so every action (save, copy,
undo, clear) is a plain method that a test can call without a display.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRectF, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QImage

from . import __version__, palette
from .annotate import Shape, render
from .capture import CaptureError, MODES, capture, resolve_target, select_region, windows
from .selection import nudge
from .settings import Settings
from .store import History, copy_to_clipboard, default_dir, human_size, make_name, save_image, unique_path


HISTORY = 100


@dataclass
class Session:
    image: QImage
    mode: str
    label: str
    target: dict = field(default_factory=dict)
    ratio: float = 1.0
    selection: QRectF = field(default_factory=QRectF)
    shapes: list[Shape] = field(default_factory=list)

    @property
    def width(self) -> int:
        return self.image.width()

    @property
    def height(self) -> int:
        return self.image.height()


def _send_notification(title: str, body: str, *, icon: str = "") -> None:
    argv = ["notify-send", "-a", "Screenshot", "-h", "string:x-canonical-private-synchronous:hyprtk-shot"]
    if icon:
        argv += ["-i", icon]
    argv += [title, body]
    try:
        subprocess.run(argv, timeout=10, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        pass


class Bridge(QObject):
    paletteChanged = Signal()
    settingsChanged = Signal()
    sessionChanged = Signal()
    selectionChanged = Signal()
    overlayChanged = Signal()
    shapesChanged = Signal()
    recentChanged = Signal()
    windowsChanged = Signal()
    pinChanged = Signal()
    toast = Signal(str, str)
    finished = Signal()

    def __init__(self, settings: Settings | None = None, history: History | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.settings = settings or Settings()
        self.history = History(limit=200)
        self._palette = palette.resolve()
        self._session: Session | None = None
        # Undo entries are whole-state snapshots (shapes + selection). Selection
        # changes are part of the history, not just annotations, and a snapshot
        # keeps undo/redo correct without a separate op type per action.
        self._undo: list[tuple] = []
        self._redo: list[tuple] = []
        self._overlay = False
        self._standalone = False
        self._busy = False
        self._last_error = ""
        self._toast_text = ""
        self._recent = self._load_recent()
        self.pending_region = ""
        self.pending_window = ""
        self._pin_path = ""
        self._pin_size = (0, 0)
        self._windows: list[dict] = []
        self._rev = 0

    # -- properties ------------------------------------------------------
    @Property("QVariantMap", notify=paletteChanged)
    def palette(self):
        data = dict(self._palette)
        # QML prefers camelCase for multi-word roles; keep the snake_case keys
        # too, because the canvas reads them by name.
        for snake, camel in (("panel_alt", "panelAlt"), ("panel_hover", "panelHover"),
                             ("text_on_accent", "textOnAccent")):
            if snake in data:
                data[camel] = data[snake]
        for key, value in list(data.items()):
            if isinstance(value, str) and value.startswith("#"):
                data[key] = QColor(value)
        data["opacity"] = float(data.get("opacity") or 0.98)
        return data

    @Property("QVariantMap", notify=settingsChanged)
    def config(self):
        return self.settings.as_dict()

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property(bool, constant=True)
    def hasGrim(self):
        from .capture import have

        return have("grim")

    @Property(bool, notify=overlayChanged)
    def overlayVisible(self):
        return self._overlay

    @Property(bool, notify=sessionChanged)
    def hasImage(self):
        return self._session is not None

    @Property(bool, notify=sessionChanged)
    def standalone(self):
        return self._standalone

    @Property(bool, notify=sessionChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=sessionChanged)
    def lastError(self):
        return self._last_error

    @Property(str, notify=shapesChanged)
    def tool(self):
        return str(self.settings.get("tool"))

    @Property(str, notify=shapesChanged)
    def color(self):
        return str(self.settings.get("color"))

    @Property(float, notify=shapesChanged)
    def stroke(self):
        return float(self.settings.get("stroke"))

    @Property(int, notify=shapesChanged)
    def shapesRev(self):
        return self._rev

    @Property(bool, notify=shapesChanged)
    def canUndo(self):
        return bool(self._undo)

    @Property(bool, notify=shapesChanged)
    def canRedo(self):
        return bool(self._redo)

    @Property("QVariantMap", notify=sessionChanged)
    def imageInfo(self):
        if not self._session:
            return {}
        session = self._session
        return {
            "width": session.width,
            "height": session.height,
            "mode": session.mode,
            "label": session.label,
            "ratio": session.ratio,
        }

    @Property("QVariantMap", notify=selectionChanged)
    def selectionInfo(self):
        if not self._session:
            return {}
        rect = self._session.selection
        return {
            "x": int(round(rect.x())),
            "y": int(round(rect.y())),
            "width": int(round(rect.width())),
            "height": int(round(rect.height())),
        }

    @Property("QVariantList", notify=recentChanged)
    def recentCaptures(self):
        return self._recent

    @Property("QVariantList", notify=windowsChanged)
    def windows(self):
        return self._windows

    @Property(bool, notify=pinChanged)
    def pinned(self):
        return bool(self._pin_path)

    @Property(str, notify=pinChanged)
    def pinPath(self):
        return self._pin_path

    @Property(int, notify=pinChanged)
    def pinWidth(self):
        return self._pin_size[0]

    @Property(int, notify=pinChanged)
    def pinHeight(self):
        return self._pin_size[1]

    @Property(str, notify=sessionChanged)
    def toastText(self):
        return self._toast_text

    # -- helpers ---------------------------------------------------------
    def session(self) -> Session | None:
        return self._session

    def _load_recent(self) -> list[dict]:
        rows = []
        for row in self.history.recent_paths(int(self.settings.get("recent")) or 12):
            path = Path(str(row.get("path")))
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            rows.append({
                "path": str(path),
                "name": path.name,
                "mode": str(row.get("mode") or "capture"),
                "ts": str(row.get("ts") or ""),
                "size": human_size(size),
                "width": row.get("width"),
                "height": row.get("height"),
            })
        return rows

    @Slot()
    def refreshWindows(self) -> None:
        """The open windows, for the picker; hyprctl is cheap but not free."""
        try:
            self._windows = [row.as_row() for row in windows()]
        except CaptureError:
            self._windows = []
        self.windowsChanged.emit()

    def _bump(self) -> None:
        self._rev += 1

    # -- history ---------------------------------------------------------
    def _snapshot(self) -> tuple:
        if not self._session:
            return ([], (0.0, 0.0, 0.0, 0.0))
        rect = self._session.selection
        return ([Shape.from_dict(shape.to_dict()) for shape in self._session.shapes],
                (rect.x(), rect.y(), rect.width(), rect.height()))

    def _remember(self, before: tuple) -> None:
        """Record one reversible action, given the state it started from."""
        after = self._snapshot()
        if before == after:
            return
        self._undo.append((before, after))
        del self._undo[:-HISTORY]
        self._redo.clear()
        self._bump()

    def _restore(self, snapshot: tuple) -> None:
        if not self._session:
            return
        shapes, rect = snapshot
        self._session.shapes = [Shape.from_dict(shape.to_dict()) for shape in shapes]
        self._session.selection = QRectF(*rect)
        self._bump()
        self.selectionChanged.emit()
        self.shapesChanged.emit()

    def _reset_history(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._bump()
        self.shapesChanged.emit()

    def _set_error(self, message: str) -> None:
        self._last_error = message
        self.sessionChanged.emit()
        self.toast.emit("Capture failed", message)

    # -- capture ---------------------------------------------------------
    @Slot(str)
    def capture(self, mode: str = "region") -> None:
        """Freeze the screen and open the overlay for ``mode``."""
        if self._busy or self._session:
            return
        mode = mode if mode in MODES else str(self.settings.get("mode"))
        self._busy = True
        self._last_error = ""
        self.sessionChanged.emit()
        delay = int(self.settings.get("delay") or 0)
        # Let QML hide the launcher window before grabbing; a capture that
        # includes our own window is the classic screenshot bug.
        QTimer.singleShot(delay * 1000 + 120, lambda: self._grab(mode))

    def _grab(self, mode: str) -> None:
        pending = self.pending_region or None
        picker = str(self.settings.get("picker") or "overlay")
        if mode == "region" and not pending and picker == "slurp":
            # slurp draws across every output, which the frozen overlay cannot:
            # the overlay is one monitor. Choosing it is explicit, because it
            # is a second selection UI the fast path normally avoids.
            try:
                pending = select_region()
            except CaptureError as exc:
                self._busy = False
                self._last_error = str(exc)
                self.sessionChanged.emit()
                self.toast.emit("Capture failed", str(exc))
                if self._standalone:
                    self.finished.emit()
                return
            if not pending:
                self._cancel_capture()
                return
        try:
            target = resolve_target(mode, region=pending,
                                    window=self.pending_window or None)
            data = capture(
                mode,
                geometry=target.get("geometry"),
                output=target.get("output"),
                cursor=bool(self.settings.get("cursor")),
            )
        except CaptureError as exc:
            self._busy = False
            message = str(exc)
            if message == "cancelled":
                self._cancel_capture()
                return
            self._set_error(message)
            self._busy = False
            if self._standalone:
                self.finished.emit()
            return

        image = QImage.fromData(data, "PNG")
        if image.isNull():
            self._busy = False
            self._set_error("grim returned an unreadable image")
            return

        ratio = 1.0
        logical_w = target.get("logical_width")
        if not logical_w:
            geometry = target.get("geometry") or ""
            if geometry and " " in geometry:
                try:
                    logical_w = int(geometry.split(" ", 1)[1].split("x", 1)[0])
                except (ValueError, IndexError):
                    logical_w = None
        if logical_w:
            ratio = image.width() / float(logical_w)

        self._session = Session(
            image=image,
            mode=mode,
            label=str(target.get("label") or mode.title()),
            target=target,
            ratio=max(0.25, min(4.0, ratio)),
            selection=QRectF(0, 0, image.width(), image.height()),
        )
        self.pending_window = ""
        self._reset_history()
        self._busy = False
        self._overlay = True
        self.sessionChanged.emit()
        self.overlayChanged.emit()

    def _cancel_capture(self) -> None:
        """A cancelled pick (slurp, or grim) is not an error."""
        self._last_error = ""
        self._busy = False
        self.sessionChanged.emit()
        if self._standalone:
            self.finished.emit()

    @Slot(str)
    def captureWindow(self, address: str) -> None:
        """Capture a window chosen in the picker, not just the focused one."""
        self.pending_window = str(address or "")
        self.capture("window")

    @Slot(str)
    def startStandalone(self, mode: str) -> None:
        """Entry path for a keybinding: capture, then quit when the overlay closes."""
        self._standalone = True
        self.capture(mode)

    @Slot(str)
    def openFile(self, path: str) -> None:
        """Open an existing image in the annotation overlay (``hyprtk-shot last``)."""
        image = QImage(path)
        if image.isNull():
            self._set_error(f"could not open {path}")
            self.finished.emit()
            return
        self._standalone = True
        self._session = Session(
            image=image,
            mode="edit",
            label=Path(path).name,
            target={"source": path},
            ratio=1.0,
            selection=QRectF(0, 0, image.width(), image.height()),
        )
        self._reset_history()
        self._overlay = True
        self.sessionChanged.emit()
        self.overlayChanged.emit()

    # -- selection / shapes ----------------------------------------------
    @Slot(float, float, float, float)
    def setSelection(self, x: float, y: float, w: float, h: float) -> None:
        if not self._session:
            return
        image = self._session.image
        rect = QRectF(x, y, w, h).normalized()
        rect = rect.intersected(QRectF(0, 0, image.width(), image.height()))
        if rect.width() < 1 or rect.height() < 1:
            return
        self._session.selection = rect
        self.selectionChanged.emit()

    @Slot()
    def selectAll(self) -> None:
        if not self._session:
            return
        image = self._session.image
        before = self._snapshot()
        self._session.selection = QRectF(0, 0, image.width(), image.height())
        self._remember(before)
        self.selectionChanged.emit()

    @Slot(float, float, float, float)
    def recordSelection(self, x: float, y: float, w: float, h: float) -> None:
        """Record a finished drag: ``x, y, w, h`` are the rect it started from.

        The canvas mutates the selection continuously while the pointer moves,
        so only the pointer release can say "that was one action".
        """
        if not self._session:
            return
        shapes, _current = self._snapshot()
        self._remember((shapes, (x, y, w, h)))

    @Slot(int, int)
    def nudgeSelection(self, dx: int, dy: int) -> None:
        """Move the selection with the arrow keys, inside the image."""
        if not self._session:
            return
        session = self._session
        rect = session.selection
        before = self._snapshot()
        session.selection = QRectF(*nudge(rect.x(), rect.y(), rect.width(),
                                          rect.height(), dx, dy,
                                          session.width, session.height))
        self._remember(before)
        self.selectionChanged.emit()

    @Slot(str)
    def setTool(self, tool: str) -> None:
        if self.settings.set("tool", tool):
            self.settings.save()
            self._bump()
            self.shapesChanged.emit()
            self.settingsChanged.emit()

    @Slot(str)
    def setColor(self, color: str) -> None:
        if self.settings.set("color", color):
            self.settings.save()
            self._bump()
            self.shapesChanged.emit()
            self.settingsChanged.emit()

    @Slot(float)
    def setStroke(self, width: float) -> None:
        if self.settings.set("stroke", width):
            self.settings.save()
            self._bump()
            self.shapesChanged.emit()

    @Slot("QVariantMap")
    def addShape(self, data) -> None:
        if not self._session:
            return
        try:
            shape = Shape.from_dict(dict(data))
        except (TypeError, ValueError):
            return
        self.addShapeObject(shape)

    def addShapeObject(self, shape: Shape) -> None:
        if not self._session:
            return
        before = self._snapshot()
        # Annotations live inside the selection: the selection is what gets
        # saved, so anything drawn outside it would silently disappear.
        rect = self._session.selection
        clamped = []
        for x, y in shape.points:
            clamped.append((min(max(x, rect.left()), rect.right()),
                            min(max(y, rect.top()), rect.bottom())))
        shape.points = clamped
        if shape.kind in ("blur", "pixelate") and len(shape.points) >= 2:
            x1, y1 = shape.points[0]
            x2, y2 = shape.points[-1]
            if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
                return
        self._session.shapes.append(shape)
        self._remember(before)
        self.shapesChanged.emit()

    @Slot()
    def undo(self) -> None:
        if not self._undo:
            return
        before, after = self._undo.pop()
        self._restore(before)
        self._redo.append((before, after))

    @Slot()
    def redo(self) -> None:
        if not self._redo:
            return
        before, after = self._redo.pop()
        self._restore(after)
        self._undo.append((before, after))

    @Slot()
    def pin(self) -> None:
        """Keep the finished capture on screen as a floating window.

        The overlay must close (it is fullscreen and would cover the pin), so
        the image is written once to the runtime dir and the pinned window is a
        plain `Image` over that file — no second paint path to keep in sync.
        """
        if not self._session:
            return
        image = self._final_image()
        # The runtime dir, not /tmp: it is per-user and gone at logout, so a
        # killed process cannot leave a pin behind for long.
        base = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / "hyprtk-shot"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._set_error(str(exc))
            return
        # Sweep pins left by processes that no longer exist (a killed app).
        for stale in base.glob("pin-*.png"):
            try:
                pid = int(stale.stem.split("-", 1)[1])
            except (IndexError, ValueError):
                continue
            if pid == os.getpid():
                continue
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, ValueError):
                try:
                    stale.unlink()
                except OSError:
                    pass
            except PermissionError:
                pass
        target = base / f"pin-{os.getpid()}.png"
        try:
            if not image.save(str(target), "PNG"):
                self._set_error("could not write the pinned image")
                return
        except OSError as exc:
            self._set_error(str(exc))
            return
        self._clear_pin()
        self._pin_path = str(target)
        self._pin_size = (image.width(), image.height())
        self.pinChanged.emit()
        self.close()

    @Slot()
    def unpin(self) -> None:
        self._clear_pin()

    def _clear_pin(self) -> None:
        if not self._pin_path:
            return
        try:
            Path(self._pin_path).unlink()
        except OSError:
            pass
        self._pin_path = ""
        self._pin_size = (0, 0)
        self.pinChanged.emit()

    @Slot()
    def clearShapes(self) -> None:
        if not self._session:
            return
        before = self._snapshot()
        self._session.shapes.clear()
        self._remember(before)
        self.shapesChanged.emit()

    # -- output ----------------------------------------------------------
    def _final_image(self):
        assert self._session is not None
        session = self._session
        rendered = render(session.image, session.shapes, scale=session.ratio)
        rect = session.selection.toRect().intersected(rendered.rect())
        if rect.width() < 1 or rect.height() < 1:
            rect = rendered.rect()
        return rendered.copy(rect)

    def _target_path(self, directory: str | None = None, fmt: str | None = None) -> Path:
        base = Path(directory).expanduser() if directory else Path(str(self.settings.get("dir") or default_dir())).expanduser()
        ext = fmt or str(self.settings.get("format") or "png")
        name = make_name(self._session.mode if self._session else "capture", ext=ext)
        return unique_path(base / name)

    def _record(self, path: Path, image) -> None:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        self.history.add({
            "path": str(path),
            "mode": self._session.mode if self._session else "capture",
            "width": image.width(),
            "height": image.height(),
            "bytes": size,
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        self._recent = self._load_recent()
        self.recentChanged.emit()

    @Slot()
    def save(self) -> str:
        if not self._session:
            return ""
        try:
            image = self._final_image()
            path = self._target_path()
            fmt = path.suffix.lstrip(".") or "png"
            path = save_image(image, path, fmt=fmt, quality=int(self.settings.get("quality")))
            self._record(path, image)
        except OSError as exc:
            self._set_error(str(exc))
            return ""
        self._toast_text = f"Saved {path.name}"
        self.toast.emit("Screenshot saved", str(path))
        return str(path)

    @Slot()
    def copy(self) -> bool:
        if not self._session:
            return False
        image = self._final_image()
        try:
            from .store import png_bytes

            data = png_bytes(image)
        except OSError as exc:
            self._set_error(str(exc))
            return False
        ok = copy_to_clipboard(data)
        if ok:
            self.toast.emit("Copied to clipboard", f"{image.width()} x {image.height()}")
        else:
            self.toast.emit("Clipboard unavailable", "Install wl-clipboard to copy captures")
        return ok

    @Slot()
    def saveAndCopy(self) -> None:
        path = self.save()
        copied = self.copy()
        if self._session and self._session.mode:
            label = Path(path).name if path else "capture"
            if path and copied:
                self._notify("Screenshot", f"{label} — saved and copied")
            elif path:
                self._notify("Screenshot", f"{label} — saved")
        self.close()

    def _notify(self, title: str, body: str) -> None:
        if not bool(self.settings.get("notify")):
            return
        icon = str(Path(__file__).resolve().parent / "assets" / "hyprtk-shot.svg")
        _send_notification(title, body, icon=icon)

    @Slot()
    def close(self) -> None:
        self._session = None
        self._overlay = False
        self._reset_history()
        self.sessionChanged.emit()
        self.overlayChanged.emit()
        self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self.close()

    # -- settings / shell -------------------------------------------------
    @Slot(str, "QVariant")
    def setConfig(self, key: str, value) -> None:
        if self.settings.set(key, value):
            self.settings.save()
            self.settingsChanged.emit()

    @Slot()
    def refreshPalette(self) -> None:
        self._palette = palette.resolve()
        self.paletteChanged.emit()

    @Slot(str)
    def openPath(self, path: str) -> None:
        if not path:
            return
        argv = ["xdg-open", str(Path(path).expanduser())]
        try:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

    @Slot(str)
    def copyPath(self, path: str) -> None:
        from .store import copy_text

        if path and copy_text(str(Path(path).expanduser())):
            self.toast.emit("Path copied", str(path))

    @Slot(str)
    def deleteCapture(self, path: str) -> None:
        try:
            Path(path).expanduser().unlink()
        except OSError:
            return
        self._recent = self._load_recent()
        self.recentChanged.emit()

    @Slot()
    def quit(self) -> None:
        app = QGuiApplication.instance()
        if app is not None:
            app.quit()

    # -- aliases used by QML (Slot names are camelCase already) -----------
    @Slot(str)
    def chooseMode(self, mode: str) -> None:
        self.capture(mode)
