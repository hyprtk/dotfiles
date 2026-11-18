"""Application bootstrap: one QGuiApplication, one QML engine, one Bridge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from . import __version__, APP_ID, BIN_NAME
from .bridge import Bridge
from .view import TerminalView


def qml_dir() -> Path:
    return Path(__file__).resolve().parent / "qml"


def assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets"


def create(argv: list[str] | None = None, startup_argv: list[str] | None = None,
           cwd: str | None = None):
    """Build the app, engine and bridge; returned for tests and screenshots."""
    argv = list(argv if argv is not None else sys.argv)
    app = QGuiApplication(argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName("Terminal")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("hyprtk")
    # Sets the Wayland app id, which is what Hyprland window rules match on.
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(True)

    icon_path = assets_dir() / "hyprtk-term.svg"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)

    qmlRegisterType(TerminalView, "HyprtkTerm", 1, 0, "TermView")
    TerminalView.set_default_startup(startup_argv, cwd)

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)
    engine.load(str(qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load")
    return app, engine, bridge


def run(argv: list[str] | None = None, startup_argv: list[str] | None = None,
        cwd: str | None = None) -> int:
    app, _engine, _bridge = create(argv, startup_argv, cwd)
    return app.exec()
