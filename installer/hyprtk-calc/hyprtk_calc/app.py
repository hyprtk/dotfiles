"""Application bootstrap: one QGuiApplication, one QML engine, one Bridge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from . import APP_ID, __version__
from .bridge import Bridge


def qml_dir() -> Path:
    return Path(__file__).resolve().parent / "qml"


def create(argv: list[str] | None = None):
    """Build the app, engine and bridge; returns them for tests and screenshots."""
    argv = list(argv if argv is not None else sys.argv)
    app = QGuiApplication(argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName("Calculator")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("hyprtk")
    # Sets the Wayland app id, so window rules and the bar's task list see the
    # desktop entry rather than org.quickshell / python3.
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(True)

    assets = qml_dir().parent / "assets"
    icon = QIcon(str(assets / "hyprtk-calc.svg"))
    if icon.isNull():
        icon = QIcon.fromTheme("accessories-calculator")
    if not icon.isNull():
        app.setWindowIcon(icon)

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)
    engine.load(str(qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load")
    return app, engine, bridge


def run(argv: list[str] | None = None) -> int:
    app, _engine, _bridge = create(argv)
    return app.exec()
