"""The QML-facing facade for the recorder window.

One `Recorder` object, one settings file, one history. The bridge adds the
things the UI needs that the core does not: a countdown before starting, a
500 ms tick for the elapsed timer, notifications, and a recent list.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication

from . import __version__, audio, palette
from .recorder import Recorder, RecorderError, available as backends_available
from .settings import Settings
from .sources import SOURCES, SourceError, outputs, resolve_source, windows
from .store import History, default_dir, human_duration, human_size, make_name, unique_path


def _send_notification(title: str, body: str, *, icon: str = "") -> None:
    argv = ["notify-send", "-a", "Screen Recorder",
            "-h", "string:x-canonical-private-synchronous:hyprtk-rec"]
    if icon:
        argv += ["-i", icon]
    argv += [title, body]
    try:
        subprocess.run(argv, timeout=6, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        pass


class Bridge(QObject):
    paletteChanged = Signal()
    settingsChanged = Signal()
    stateChanged = Signal()
    recentChanged = Signal()
    sourcesChanged = Signal()
    toast = Signal(str, str)
    countdownTick = Signal(int)

    def __init__(self, settings: Settings | None = None, recorder: Recorder | None = None,
                 history: History | None = None, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings or Settings()
        self.recorder = recorder or Recorder()
        self.history = History()
        self._palette = palette.resolve()
        # Before status(): asking for the status clears a stale state file, and
        # a crash's partial file is exactly what must not be forgotten.
        recovered = self.recorder.recover()
        self._status = self.recorder.status()
        self._countdown = 0
        self._pending_source = ""
        self._recent = self._load_recent()
        if recovered is not None:
            self._salvage(recovered)
        self._monitors = []
        self._windows = []
        self.refreshSources()

        self._ticker = QTimer(self)
        self._ticker.setInterval(500)
        self._ticker.timeout.connect(self._tick)
        if self._status.get("recording"):
            self._ticker.start()

    # -- properties ------------------------------------------------------
    @Property("QVariantMap", notify=paletteChanged)
    def palette(self):
        data = dict(self._palette)
        for snake, camel in (("panel_alt", "panelAlt"), ("panel_hover", "panelHover"),
                             ("text_on_accent", "textOnAccent"), ("muted_text", "mutedText")):
            if snake in data:
                data[camel] = data[snake]
        for key, value in list(data.items()):
            if isinstance(value, str) and value.startswith("#"):
                data[key] = QColor(value)
        return data

    @Property("QVariantMap", notify=settingsChanged)
    def config(self):
        return self.settings.as_dict()

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property(bool, notify=stateChanged)
    def recording(self):
        return bool(self._status.get("recording"))

    @Property(bool, notify=stateChanged)
    def paused(self):
        return bool(self._status.get("paused"))

    @Property(str, notify=stateChanged)
    def elapsed(self):
        return human_duration(self._status.get("elapsed", 0))

    @Property("QVariantMap", notify=stateChanged)
    def status(self):
        data = dict(self._status)
        if data.get("bytes"):
            data["size"] = human_size(data["bytes"])
        else:
            data["size"] = ""
        data["elapsedText"] = human_duration(data.get("elapsed", 0))
        return data

    @Property(int, notify=stateChanged)
    def countdown(self):
        return self._countdown

    @Property("QVariantList", notify=recentChanged)
    def recentRecordings(self):
        return self._recent

    @Property("QVariantList", notify=sourcesChanged)
    def monitors(self):
        return self._monitors

    @Property("QVariantList", notify=sourcesChanged)
    def windows(self):
        return self._windows

    @Property(str, notify=settingsChanged)
    def windowLabel(self):
        """What the Window source will record: a picked title, or "Focused"."""
        address = str(self.settings.get("window") or "")
        if not address:
            return "Focused window"
        for row in self._windows:
            if row.get("address") == address:
                return str(row.get("title") or row.get("class") or "Window")
        return "Focused window"

    @Property("QVariantList", constant=True)
    def audioSources(self):
        return [{"name": row["name"], "label": row["label"], "monitor": row["monitor"]}
                for row in audio.sources()]

    @Property("QVariantList", constant=True)
    def backends(self):
        return backends_available()

    @Property(str, notify=stateChanged)
    def backendLabel(self):
        found = backends_available()
        return found[0] if found else "none installed"

    @Property(bool, constant=True)
    def canRecord(self):
        return bool(backends_available())

    # -- helpers ---------------------------------------------------------
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
                "source": str(row.get("source") or "output"),
                "duration": row.get("duration") or 0,
                "durationText": human_duration(row.get("duration") or 0),
                "size": human_size(size),
                "ts": str(row.get("ts") or ""),
            })
        return rows

    def _salvage(self, rec) -> None:
        """Keep a crashed recording: log it, and say what happened."""
        try:
            size = os.path.getsize(rec.path)
        except OSError:
            size = 0
        self.history.add({
            "path": str(rec.path),
            "source": rec.source,
            "duration": rec.elapsed(),
            "bytes": size,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "recovered": True,
        })
        self._recent = self._load_recent()
        self.recentChanged.emit()
        self._notify("Recording recovered", f"{Path(rec.path).name} ({human_size(size)})")

    def _set_status(self) -> None:
        self._status = self.recorder.status()
        if self._status.get("recording"):
            if not self._ticker.isActive():
                self._ticker.start()
        elif self._ticker.isActive():
            self._ticker.stop()
        self.stateChanged.emit()

    def _tick(self) -> None:
        self._set_status()

    def _notify(self, title: str, body: str) -> None:
        if not bool(self.settings.get("notify")) or os.environ.get("HYPRTK_REC_NOTIFY") == "0":
            return
        icon = str(Path(__file__).resolve().parent / "assets" / "hyprtk-rec.svg")
        _send_notification(title, body, icon=icon)

    @Slot()
    def refreshSources(self) -> None:
        try:
            self._monitors = [row.as_row() for row in outputs()]
        except SourceError:
            self._monitors = []
        try:
            self._windows = [row.as_row() for row in windows()]
        except SourceError:
            self._windows = []
        # A picked window that has closed must not pin the recording to a
        # geometry nobody is drawing any more.
        picked = str(self.settings.get("window") or "")
        if picked and not any(row.get("address") == picked for row in self._windows):
            self.settings.set("window", "")
            self.settings.save()
            self.settingsChanged.emit()
        self.sourcesChanged.emit()

    @Slot(str)
    def pickWindow(self, address: str) -> None:
        """Choose a window by address; an empty address means "focused"."""
        address = str(address or "")
        if not any(row.get("address") == address for row in self._windows):
            address = ""
        if self.settings.set("window", address):
            self.settings.save()
            self.settingsChanged.emit()

    # -- recording -------------------------------------------------------
    @Slot()
    def start(self) -> None:
        self.startSource(str(self.settings.get("source") or "output"))

    @Slot(str)
    def startSource(self, source: str) -> None:
        if self._status.get("recording") or self._countdown:
            return
        self._pending_source = source if source in SOURCES else "output"
        countdown = int(self.settings.get("countdown") or 0)
        if countdown > 0:
            self._countdown = countdown
            self.countdownTick.emit(self._countdown)
            self.stateChanged.emit()
            QTimer.singleShot(1000, self._countdown_step)
            return
        self._begin()

    def _countdown_step(self) -> None:
        if self._countdown <= 0:
            return
        self._countdown -= 1
        self.countdownTick.emit(self._countdown)
        self.stateChanged.emit()
        if self._countdown > 0:
            QTimer.singleShot(1000, self._countdown_step)
        else:
            self._begin()

    @Slot()
    def _begin(self) -> None:
        self._countdown = 0
        source = self._pending_source or str(self.settings.get("source") or "output")
        try:
            target = resolve_source(source, window=str(self.settings.get("window") or "") or None)
        except SourceError as exc:
            message = str(exc)
            if message != "cancelled":
                self.toast.emit("Cannot start", message)
            self.stateChanged.emit()
            return

        container = str(self.settings.get("container") or "mp4")
        base = Path(str(self.settings.get("dir") or default_dir())).expanduser()
        path = unique_path(base / make_name(source, ext=container))
        try:
            recording = self.recorder.start(
                path=str(path),
                source=source,
                geometry=target.get("geometry"),
                output=target.get("output"),
                codec=str(self.settings.get("codec") or "h264"),
                quality=str(self.settings.get("quality") or "medium"),
                fps=int(self.settings.get("fps") or 60),
                audio=str(self.settings.get("audio") or "none"),
                cursor=bool(self.settings.get("cursor")),
                backend=str(self.settings.get("backend") or "auto"),
                container=container,
            )
        except RecorderError as exc:
            self.toast.emit("Cannot start", str(exc))
            self.stateChanged.emit()
            return
        self._set_status()
        self._notify("Recording", f"{target.get('label')} → {Path(recording.path).name}")

    @Slot()
    def stop(self) -> None:
        was = self._status.get("recording")
        self._countdown = 0
        # Read the clock before the state file is cleared, or the history
        # records every recording as zero seconds long.
        try:
            duration = float(self._status.get("elapsed") or 0)
        except (TypeError, ValueError):
            duration = 0
        path = self.recorder.stop()
        self._set_status()
        if not was or not path:
            if was:
                self.toast.emit("Recording failed", "the encoder wrote no data")
            return
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        row = self.history.add({
            "path": str(path),
            "source": self.settings.get("source"),
            "duration": duration,
            "bytes": size,
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        self._recent = self._load_recent()
        self.recentChanged.emit()
        self._notify_saved(str(path))
        self.toast.emit("Saved", str(path))

    def _notify_saved(self, path: str) -> None:
        """A notification with "Open folder" / "Copy path" buttons.

        notify-send only reports the pressed button while the notification is
        alive, so the waiter is a detached helper process, not this one.
        """
        if not bool(self.settings.get("notify")) or os.environ.get("HYPRTK_REC_NOTIFY") == "0":
            return
        argv = [sys.executable, "-m", "hyprtk_rec", "notify-saved", path]
        env = dict(os.environ)
        root = str(Path(__file__).resolve().parents[1])
        env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        try:
            subprocess.Popen(argv, env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            self._notify("Recording saved", str(path))

    @Slot()
    def toggle(self) -> None:
        if self._status.get("recording") or self._countdown:
            self.stop()
        else:
            self.start()

    @Slot()
    def pause(self) -> None:
        if self.recorder.pause():
            self._set_status()

    @Slot()
    def resume(self) -> None:
        if self.recorder.resume():
            self._set_status()

    @Slot()
    def togglePause(self) -> None:
        if self._status.get("paused"):
            self.resume()
        else:
            self.pause()

    @Slot()
    def refreshStatus(self) -> None:
        self._set_status()

    # -- settings / shell -------------------------------------------------
    @Slot(str, "QVariant")
    def setConfig(self, key: str, value) -> None:
        if self.settings.set(key, value):
            self.settings.save()
            self.settingsChanged.emit()
            self.stateChanged.emit()

    @Slot()
    def resetConfig(self) -> None:
        self.settings = Settings()
        self.settingsChanged.emit()

    @Slot()
    def refreshPalette(self) -> None:
        self._palette = palette.resolve()
        self.paletteChanged.emit()

    @Slot(str)
    def openPath(self, path: str) -> None:
        if not path:
            return
        target = Path(path).expanduser()
        if target.is_dir():
            argv = ["xdg-open", str(target)]
        else:
            argv = ["xdg-open", str(target)]
        try:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

    @Slot(str)
    def deleteRecording(self, path: str) -> None:
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
