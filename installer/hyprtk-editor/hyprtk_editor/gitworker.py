"""Git gutter work off the GUI thread.

`git diff` is cheap on a small repository and not cheap at all on a large one:
three subprocesses per status call, up to 1.2 s in a pathological checkout. The
gutter is refreshed on every save, load and settings change, so it must never
run on the GUI thread.

This is a plain ``QThread`` with a queue: the bridge asks for a path, the worker
computes with the pure-Python :class:`~hyprtk_editor.gitdiff.GitDiff` and emits
the result. Emitting from ``run()`` gives a queued connection to the GUI thread,
so the receiver can touch QML state safely. A sentinel stops the thread, and
each path is coalesced — a newer request for the same path wins.
"""

from __future__ import annotations

import atexit
import queue
import threading

from PySide6.QtCore import QThread, Signal

from .gitdiff import GitDiff, Status


class GitWorker(QThread):
    """One background thread that answers gutter requests."""

    ready = Signal(str, "QVariant")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._diff = GitDiff()
        self._requests: queue.Queue = queue.Queue()
        self._wanted = threading.Lock()
        self._pending: set[str] = set()
        self._stopping = False
        atexit.register(self.stop)

    # -- api (GUI thread) -------------------------------------------------
    def request(self, path: str) -> None:
        """Ask for a fresh status; the answer arrives as :attr:`ready`."""
        if self._stopping or not path:
            return
        with self._wanted:
            if path in self._pending:
                return                      # already queued; it will be fresh
            self._pending.add(path)
        self._requests.put(path)
        if not self.isRunning():
            # The thread exits when idle, so it never outlives its usefulness
            # (a test process or a closed editor is not left waiting on it).
            self._stopping = False
            self.start()

    def cached(self, path: str) -> dict:
        """Last known status. A well-formed "nothing yet" before the first answer,
        so QML always gets the same keys."""
        status = self._diff.cached(path)
        if status is None:
            status = Status()
        return status.as_dict()

    def stop(self) -> None:
        self._stopping = True
        self._requests.put(None)
        self.wait(1000)

    # -- thread -----------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - QThread entry point
        idle = 0
        while True:
            try:
                path = self._requests.get(timeout=0.1)
            except queue.Empty:
                idle += 1
                if self._stopping or idle >= 10:    # ~1 s with nothing to do
                    return
                continue
            idle = 0
            if path is None:
                return
            try:
                status = self._diff.status(path)
                payload = status.as_dict()
            except Exception:               # a status call must never kill the thread
                payload = {}
            with self._wanted:
                self._pending.discard(path)
            self.ready.emit(path, payload)
