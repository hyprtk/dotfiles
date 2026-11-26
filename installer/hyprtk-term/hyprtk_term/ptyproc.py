"""The PTY: fork, exec, resize, reap.

One process per terminal, exactly like every other emulator in the field. No
`subprocess` wrapper is used because a child must become a **session leader**
with the slave as its controlling terminal, and that is what ``pty.fork``
gives us.
"""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import signal
import struct
import termios


class PtyError(RuntimeError):
    pass


class Pty:
    """A child process attached to a pseudo-terminal."""

    def __init__(self, argv: list[str], env: dict | None = None,
                 cwd: str | None = None, rows: int = 24, cols: int = 80):
        if not argv:
            raise PtyError("empty command")
        child_env = os.environ.copy()
        child_env.setdefault("TERM", "xterm-256color")
        child_env.setdefault("COLORTERM", "truecolor")
        if env:
            child_env.update(env)

        self.pid, self.fd = pty.fork()
        if self.pid == 0:                                   # child
            try:
                if cwd:
                    os.chdir(cwd)
                os.execvpe(argv[0], argv, child_env)
            except BaseException:
                os._exit(127)

        self._status: int | None = None
        self._pending = bytearray()
        self._set_winsize(rows, cols)
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # ------------------------------------------------------------------ io --

    def read(self, size: int = 65536) -> bytes:
        try:
            return os.read(self.fd, size)
        except BlockingIOError:
            return b""
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                return b""                                  # slave closed
            raise

    def read_all(self) -> bytes:
        """Drain everything the child has written (bounded by the PTY buffer)."""
        chunks = []
        while True:
            data = self.read()
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks)

    def write(self, data: bytes) -> int:
        """Queue bytes for the child and flush what the kernel accepts now.

        Returns the number of bytes accepted *by the queue* (i.e. all of them):
        a PTY master is non-blocking, so a large paste would otherwise be
        silently truncated when the kernel buffer fills (measured: 197 KB
        pasted, 22 KB delivered). Callers must drain with :meth:`flush` once
        the fd reports writable.
        """
        if not data:
            return 0
        self._pending += data
        self.flush()
        return len(data)

    @property
    def pending(self) -> int:
        return len(self._pending)

    def flush(self) -> bool:
        """Write as much of the queue as the kernel takes. True when empty."""
        while self._pending:
            try:
                written = os.write(self.fd, self._pending)
            except BlockingIOError:
                return False
            except OSError as exc:
                if exc.errno == errno.EIO:
                    self._pending.clear()
                    return True
                raise
            if written <= 0:
                return False
            del self._pending[:written]
        return True

    # --------------------------------------------------------------- sizing --

    def _set_winsize(self, rows: int, cols: int) -> None:
        rows, cols = max(1, int(rows)), max(1, int(cols))
        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                        struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass

    def resize(self, rows: int, cols: int) -> None:
        # The kernel sends SIGWINCH to the foreground process group for us.
        self._set_winsize(rows, cols)

    # ------------------------------------------------------------- lifecycle --

    def poll(self) -> int | None:
        """Exit status if the child has exited, else None."""
        if self._status is not None:
            return self._status
        try:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            self._status = 0
            return self._status
        if pid == 0:
            return None
        self._status = _decode_status(status)
        return self._status

    def alive(self) -> bool:
        return self.poll() is None

    def terminate(self, sig: int = signal.SIGHUP) -> None:
        if self.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(self.pid), sig)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(self.pid, sig)
            except ProcessLookupError:
                pass

    def close(self) -> None:
        try:
            os.close(self.fd)
        except OSError:
            pass
        self.fd = -1


def _decode_status(status: int) -> int:
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    return 0


def default_argv(shell: str | None = None, login: bool = True) -> list[str]:
    """The suite's shell, as a login shell when it supports the flag."""
    shell = shell or os.environ.get("SHELL") or "/bin/sh"
    shell = os.path.expanduser(shell)
    argv = [shell]
    if login and os.path.basename(shell) in ("bash", "zsh", "fish", "sh", "ksh", "mksh", "dash"):
        argv.append("-l")
    return argv
