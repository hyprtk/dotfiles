"""Application bootstrap: one QApplication, one QML engine, one Bridge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from . import APP_ID, APP_NAME, __version__
from .bridge import Bridge


def qml_dir() -> Path:
    return Path(__file__).resolve().parent / "qml"


def create(argv: list[str] | None = None):
    """Build the app, engine and bridge; returns them for tests/screenshots."""
    argv = list(argv if argv is not None else sys.argv)
    app = QApplication(argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName("Text Editor")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("hyprtk")
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(True)

    icon = QIcon(str(qml_dir().parent / "assets" / "hyprtk-editor.svg"))
    if icon.isNull():
        icon = QIcon.fromTheme("accessories-text-editor")
    if not icon.isNull():
        app.setWindowIcon(icon)

    # Everything after the program name that is not a flag is a file to open.
    files = []
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        candidate = os.path.abspath(os.path.expanduser(arg))
        if os.path.exists(candidate):
            files.append(candidate)

    bridge = Bridge(initial=files)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)
    engine.load(str(qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load")
    return app, engine, bridge


def run(argv: list[str] | None = None) -> int:
    app, _engine, _bridge = create(argv)
    return app.exec()
