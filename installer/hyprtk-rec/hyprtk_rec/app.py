"""Application bootstrap: one QGuiApplication, one engine, one Bridge."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from . import APP_ID, __version__
from .bridge import Bridge


def qml_dir() -> Path:
    return Path(__file__).resolve().parent / "qml"


def create(argv: list[str] | None = None, *, overrides: dict | None = None):
    argv = list(argv if argv is not None else sys.argv)
    app = QGuiApplication(argv)
    app.setApplicationName(APP_ID)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("hyprtk")
    # The Wayland app id: window rules and the bar's task list need the desktop
    # entry id, not python3.
    app.setDesktopFileName(APP_ID)

    assets = qml_dir().parent / "assets"
    icon = QIcon(str(assets / "hyprtk-rec.svg"))
    if icon.isNull():
        icon = QIcon.fromTheme("media-record")
    if not icon.isNull():
        app.setWindowIcon(icon)

    from .settings import Settings

    settings = Settings()
    for key, value in (overrides or {}).items():
        if value is not None:
            settings.set(key, value)
    bridge = Bridge(settings=settings)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)
    engine.load(str(qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load")
    return app, engine, bridge


def run(argv: list[str] | None = None, *, overrides: dict | None = None) -> int:
    app, _engine, _bridge = create(argv, overrides=overrides)
    return app.exec()
