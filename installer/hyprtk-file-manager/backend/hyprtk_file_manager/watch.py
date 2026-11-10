"""Directory change watching via inotify."""

from __future__ import annotations

import ctypes
import os
import select
import threading
import time

IN_MASK = (
    0x00000002  # IN_MODIFY
    | 0x00000004  # IN_ATTRIB
    | 0x00000008  # IN_CLOSE_WRITE
    | 0x00000040  # IN_MOVED_FROM
    | 0x00000080  # IN_MOVED_TO
    | 0x00000100  # IN_CREATE
    | 0x00000200  # IN_DELETE
    | 0x00000400  # IN_DELETE_SELF
    | 0x00000800  # IN_MOVE_SELF
)

_libc = ctypes.CDLL(None, use_errno=True)
_libc.inotify_init1.argtypes = [ctypes.c_int]
_libc.inotify_init1.restype = ctypes.c_int
_libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
_libc.inotify_add_watch.restype = ctypes.c_int


class _Watcher:
    def __init__(self, token: str, path: str, emit, interval: float = 0.15):
        self.token = token
        self.path = path
        self.emit = emit
        self.interval = interval
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.fd = -1
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        try:
            if self.fd >= 0:
                os.close(self.fd)
        except OSError:
            pass

    def _run(self) -> None:
        fd = _libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            return
        self.fd = fd
        watch = _libc.inotify_add_watch(fd, self.path.encode("utf-8", "replace"), IN_MASK)
        if watch < 0:
            os.close(fd)
            self.fd = -1
            return
        self.ready.set()
        last = 0.0
        try:
            while not self.stop_event.is_set():
                try:
                    ready, _, _ = select.select([fd], [], [], 0.5)
                except (OSError, ValueError):
                    break
                if not ready:
                    continue
                try:
                    data = os.read(fd, 4096)
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError:
                    break
                if not data:
                    continue
                now = time.monotonic()
                if now - last < self.interval:
                    continue
                last = now
                self.emit({"event": "fs", "token": self.token, "dir": self.path})
        finally:
            if self.fd >= 0:
                try:
                    os.close(self.fd)
                except OSError:
                    pass
                self.fd = -1


class WatchManager:
    def __init__(self, emit):
        self.emit = emit
        self.watches: dict[str, _Watcher] = {}
        self.lock = threading.Lock()

    def watch(self, token: str, path: str) -> None:
        if not token or not path:
            return
        with self.lock:
            current = self.watches.get(token)
            if current and current.path == path:
                return
            if current:
                current.stop()
            watcher = _Watcher(token, path, self.emit)
            self.watches[token] = watcher
            watcher.start()
            watcher.ready.wait(0.5)

    def unwatch(self, token: str) -> None:
        with self.lock:
            watcher = self.watches.pop(token, None)
            if watcher:
                watcher.stop()

    def stop_all(self) -> None:
        with self.lock:
            for watcher in self.watches.values():
                watcher.stop()
            self.watches.clear()
