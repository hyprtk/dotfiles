"""A terminal = one libvterm screen + one PTY + the Qt plumbing between them.

The PTY master is watched with a ``QSocketNotifier`` on the GUI thread, so
there is no reader thread and no lock around the VT state.
"""

from __future__ import annotations

import os
import signal

from PySide6.QtCore import QObject, QSocketNotifier, QTimer, Signal

from .ptyproc import Pty, default_argv
from .vt import VTerminal


class Terminal(QObject):
    """Owns the child process and the emulator state for one tab."""

    titleChanged = Signal(str)
    bell = Signal()
    exited = Signal(int)
    changed = Signal()

    def __init__(self, rows: int = 24, cols: int = 80, *,
                 shell: str | None = None,
                 command: list[str] | None = None,
                 cwd: str | None = None,
                 env: dict | None = None,
                 scrollback: int = 10_000,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.vt = VTerminal(rows, cols, scrollback)
        self.vt.on_clipboard = self._osc52_set
        self.vt.on_clipboard_query = self._osc52_query

        self._title = ""
        self._bell = 0
        self._exited = False
        self._on_clipboard_get = None
        self._on_clipboard_put = None

        argv = command or default_argv(shell)
        self.pty = Pty(argv, env=env, cwd=cwd or os.path.expanduser("~"),
                       rows=rows, cols=cols)
        self.pid = self.pty.pid

        self._notifier = QSocketNotifier(self.pty.fd, QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._readable)

        # A PTY master is non-blocking: a paste bigger than the kernel buffer
        # must be queued and drained when the fd reports writable, not dropped.
        self._wnotifier = QSocketNotifier(self.pty.fd, QSocketNotifier.Type.Write, self)
        self._wnotifier.setEnabled(False)
        self._wnotifier.activated.connect(self._writable)

        # A child can exit while a grandchild keeps the slave open; the fd then
        # never reports EOF, so the process is also polled.
        self._reaper = QTimer(self)
        self._reaper.setInterval(1000)
        self._reaper.timeout.connect(self._check_exit)
        self._reaper.start()

    # ------------------------------------------------------------- clipboard --

    def bind_clipboard(self, getter, putter) -> None:
        """``getter() -> str`` and ``putter(text, primary)`` for OSC 52."""
        self._on_clipboard_get = getter
        self._on_clipboard_put = putter

    def _osc52_set(self, text: str, primary: bool) -> None:
        if self._on_clipboard_put:
            self._on_clipboard_put(text, primary)

    def _osc52_query(self) -> None:
        if not self._on_clipboard_get:
            return
        text = self._on_clipboard_get() or ""
        if text:
            self.write(_osc52_answer(self.vt, text))

    # ------------------------------------------------------------------- io --

    def _readable(self, *_args) -> None:
        data = self.pty.read_all()
        if not data:
            self._check_exit()
            return
        self.vt.feed(data)
        self._sync()

    def _sync(self) -> None:
        if self.vt.title != self._title:
            self._title = self.vt.title
            self.titleChanged.emit(self._title)
        if self.vt.bell_count != self._bell:
            self._bell = self.vt.bell_count
            self.bell.emit()
        self.changed.emit()

    def _check_exit(self) -> None:
        if self._exited:
            return
        status = self.pty.poll()
        if status is None:
            return
        self._exited = True
        self._notifier.setEnabled(False)
        self._wnotifier.setEnabled(False)
        self._reaper.stop()
        # Nothing will read or write this master again; closing it here stops a
        # grandchild holding the slave from keeping the fd (and the pty) alive
        # for the life of the tab.
        try:
            self.pty.close()
        except OSError:
            pass
        self.changed.emit()
        self.exited.emit(status)

    # ------------------------------------------------------------- commands --

    def write(self, data: bytes) -> None:
        if not data:
            return
        self.pty.write(data)
        if self.pty.pending and not self._exited:
            self._wnotifier.setEnabled(True)

    def _writable(self, *_args) -> None:
        if self.pty.flush():
            self._wnotifier.setEnabled(False)

    def send(self, text: str) -> None:
        """Send text as if typed (used by paste, IME commits, drop targets)."""
        if text:
            self.write(self.vt.paste(text))

    def resize(self, rows: int, cols: int) -> bool:
        """True when the grid actually changed (and the shell was told)."""
        if self.vt.resize(rows, cols):
            self.pty.resize(rows, cols)
            self.changed.emit()
            return True
        return False

    def close(self, sig: int = signal.SIGHUP) -> None:
        if not self._exited:
            try:
                self.pty.terminate(sig)
            except OSError:
                pass
            # A child that ignores SIGHUP would otherwise keep running against
            # a closed master; escalate after a short grace period.
            import time as _time

            deadline = _time.monotonic() + 0.25
            while _time.monotonic() < deadline and self.pty.poll() is None:
                _time.sleep(0.01)
            if self.pty.poll() is None:
                try:
                    self.pty.terminate(signal.SIGKILL)
                except OSError:
                    pass
        try:
            self._notifier.setEnabled(False)
            self._wnotifier.setEnabled(False)
        except RuntimeError:
            pass
        self.pty.close()

    @property
    def has_exited(self) -> bool:
        return self._exited

    @property
    def title(self) -> str:
        return self._title


def _osc52_answer(vt: VTerminal, text: str) -> bytes:
    """Answer an OSC 52 read from what the clipboard currently holds."""
    from . import vtcapi as V
    import ctypes as C
    if not hasattr(V.lib, "vterm_state_send_selection"):
        return b""
    raw = text.encode("utf-8")
    frag = V.Fragment(raw, len(raw), True, True)
    V.lib.vterm_state_send_selection(vt._state, V.SELECT["CLIPBOARD"], frag)
    out = bytearray()
    while True:
        buf = C.create_string_buffer(4096)
        n = V.lib.vterm_output_read(vt._vt, buf, len(buf))
        if not n:
            break
        out += buf.raw[:n]
        if n < len(buf):
            break
    return bytes(out)
