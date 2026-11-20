"""Application bootstrap: one QGuiApplication, one engine, one Bridge."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from . import APP_ID, __version__
from .bridge import Bridge
from .canvas import CaptureCanvas
from .settings import Settings


def qml_dir() -> Path:
    return Path(__file__).resolve().parent / "qml"


def create(argv: list[str] | None = None, *, mode: str = "", open_path: str = "",
           region: str = "", overrides: dict | None = None):
    """Build the app, engine and bridge; returns them for tests and screenshots."""
    argv = list(argv if argv is not None else sys.argv)
    app = QGuiApplication(argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName("Screenshot")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("hyprtk")
    # Sets the Wayland app id, so the overlay's fullscreen request and window
    # rules see a real desktop id instead of python3.
    app.setDesktopFileName(APP_ID)

    assets = qml_dir().parent / "assets"
    icon = QIcon(str(assets / "hyprtk-shot.svg"))
    if icon.isNull():
        icon = QIcon.fromTheme("applets-screenshooter")
    if not icon.isNull():
        app.setWindowIcon(icon)

    qmlRegisterType(CaptureCanvas, "HyprtkShot", 1, 0, "CaptureCanvas")

    settings = Settings()
    for key, value in (overrides or {}).items():
        if value is not None:
            settings.set(key, value)
    bridge = Bridge(settings=settings)
    bridge.pending_region = region
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)
    engine.rootContext().setContextProperty("initialMode", mode)
    engine.rootContext().setContextProperty("initialPath", open_path)
    engine.load(str(qml_dir() / "Main.qml"))
    if not engine.rootObjects():
        raise RuntimeError("QML failed to load")

    bridge.finished.connect(lambda: app.quit() if bridge.standalone else None)
    return app, engine, bridge


def run(argv: list[str] | None = None, *, mode: str = "", open_path: str = "",
        region: str = "", overrides: dict | None = None) -> int:
    app, _engine, _bridge = create(argv, mode=mode, open_path=open_path,
                                   region=region, overrides=overrides)
    return app.exec()
