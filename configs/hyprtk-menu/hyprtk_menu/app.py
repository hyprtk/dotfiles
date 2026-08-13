"""Entry point, single-instance, and SIGUSR1 toggle for hyprtk-menu."""

import os
import signal
import sys

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk

from . import config as cfg
from .menu import MenuWindow

PID_FILE = os.path.join(cfg.CACHE_DIR, "hyprtk-menu.pid")


def _read_pid():
    try:
        with open(PID_FILE, encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError, ProcessLookupError, PermissionError):
        return None


def _write_pid():
    os.makedirs(cfg.CACHE_DIR, exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def _cleanup_pid():
    try:
        if _read_pid() == os.getpid():
            os.unlink(PID_FILE)
    except OSError:
        pass


def main():
    running_pid = _read_pid()
    if running_pid:
        os.kill(running_pid, signal.SIGUSR1)
        return 0

    _write_pid()

    window = MenuWindow()

    def _toggle(*_args):
        try:
            window.toggle()
        except Exception:
            import traceback

            traceback.print_exc()
        return True  # keep the signal source alive

    def _reposition(*_args):
        try:
            window.reposition()
        except Exception:
            import traceback

            traceback.print_exc()
        return True

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, _toggle)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, _reposition)

    def _initial_show():
        window.show_menu()
        # Re-present shortly after so the layer-shell surface maps reliably.
        GLib.timeout_add(300, window.present)
        return False

    GLib.idle_add(_initial_show)
    try:
        Gtk.main()
    finally:
        _cleanup_pid()
    return 0
