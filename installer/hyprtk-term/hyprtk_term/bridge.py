"""The QML-facing facade.

QML never touches settings files, the palette loader or the clipboard directly;
it reads properties from here and calls slots. The terminal views get the same
two objects (``config`` and ``palette``) through ``applySettings()``, so one
wallpaper change repaints every tab.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, Signal, Slot
from PySide6.QtGui import QColor

from . import __version__, palette, settings
from . import vtcapi

PROJECT_URL = "https://github.com/hyprtk/hyprtk-term"


class Bridge(QObject):
    paletteChanged = Signal()
    configChanged = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._cfg = settings.Settings.load()
        self._colors = palette.resolve()
        self._watch_paths: list[str] = []
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_theme_file_changed)
        self._install_watch()

    # ------------------------------------------------------------- properties --

    def _get_palette(self) -> dict:
        # QML colour helpers (Util.alpha) need .r/.g/.b, and a hex string has
        # none -- so every colour crosses the boundary as a QColor. The ANSI
        # list stays as hex strings because the terminal view parses it itself.
        out = {}
        for key, value in self._colors.items():
            if isinstance(value, str) and value.startswith("#"):
                out[key] = QColor(value)
            else:
                out[key] = value
        return out

    palette = Property("QVariantMap", _get_palette, notify=paletteChanged)

    def _get_config(self) -> dict:
        return self._cfg.as_dict()

    config = Property("QVariantMap", _get_config, notify=configChanged)

    def _get_version(self) -> str:
        return __version__

    version = Property(str, _get_version, constant=True)

    def _get_about(self) -> dict:
        return {
            "version": __version__,
            "libvterm": vtcapi.library_path(),
            "project": PROJECT_URL,
            "shell": self._cfg.shell or os.environ.get("SHELL", "/bin/sh"),
        }

    about = Property("QVariantMap", _get_about, constant=True)

    # ---------------------------------------------------------------- palette --

    def _install_watch(self) -> None:
        home = os.environ.get("HYPRTK_WAL_HOME") or os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".cache", "wal", "colors.json"),
            os.path.expanduser("~/.config/hyprtk-bar-qt/config.json"),
        ]
        paths = [p for p in candidates if os.path.exists(p) and p not in self._watch_paths]
        if paths:
            self._watcher.addPaths(paths)
            self._watch_paths.extend(paths)

    def _on_theme_file_changed(self, _path: str) -> None:
        self.reloadPalette()
        self._install_watch()          # editors often replace the file

    @Slot()
    def reloadPalette(self) -> None:    # noqa: N802
        self._colors = palette.resolve()
        self.paletteChanged.emit()

    # --------------------------------------------------------------- settings --

    @Slot(str, "QVariant")
    def setConfig(self, key: str, value) -> None:   # noqa: N802
        if not hasattr(self._cfg, key):
            return
        current = getattr(self._cfg, key)
        try:
            if isinstance(current, bool):
                value = bool(value)
            elif isinstance(current, int):
                value = int(value)
            elif isinstance(current, float):
                value = float(value)
            else:
                value = str(value)
        except (TypeError, ValueError):
            return
        setattr(self._cfg, key, value)
        self.configChanged.emit()

    @Slot()
    def saveConfig(self) -> None:                   # noqa: N802
        self._cfg.opacity = settings.clamp_opacity(self._cfg.opacity)
        self._cfg.font_size = settings.clamp_font_size(self._cfg.font_size)
        self._cfg.scrollback = settings.clamp_scrollback(self._cfg.scrollback)
        try:
            self._cfg.save()
        except OSError:
            pass
        self.configChanged.emit()

    @Slot()
    def resetConfig(self) -> None:                  # noqa: N802
        self._cfg = settings.Settings()
        self.configChanged.emit()

    @Slot(result="QVariantList")
    def monoFonts(self) -> list:                    # noqa: N802
        """Monospace families, suite fonts first."""
        return [name for name in settings.MONO_FALLBACKS if _font_exists(name)] or ["monospace"]

    # ------------------------------------------------------------- utilities --

    @Slot(str, result=str)
    def shellName(self, path: str) -> str:          # noqa: N802
        return os.path.basename(path) if path else "shell"

    @Slot(result=str)
    def defaultShell(self) -> str:                  # noqa: N802
        return os.environ.get("SHELL", "/bin/sh")

    @Slot(str, result=bool)
    def pathExists(self, path: str) -> bool:        # noqa: N802
        return bool(path) and Path(os.path.expanduser(path)).exists()

    @Slot(str, result=str)
    def expandPath(self, path: str) -> str:         # noqa: N802
        return os.path.expanduser(path or "")

    @Slot(str, result=str)
    def openWith(self, target: str) -> str:         # noqa: N802
        """Open a path with the suite's file manager (URLs would need a handler)."""
        expanded = os.path.expanduser(target)
        if not os.path.exists(expanded):
            return ""
        for candidate in ("hyprtk-fm", "xdg-open"):
            exe = shutil.which(candidate)
            if exe:
                import subprocess
                subprocess.Popen([exe, expanded], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return candidate
        return ""


def _font_exists(family: str) -> bool:
    try:
        from PySide6.QtGui import QFontDatabase
        return family in QFontDatabase.families()
    except Exception:               # pragma: no cover - no display
        return family == "monospace"
