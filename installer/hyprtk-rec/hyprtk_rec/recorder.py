"""The recording process: start it, watch it, stop it, and survive a restart.

The app does not encode anything. ``wf-recorder`` (or ``wl-screenrec``) does,
and this module builds its command line, keeps the running state in a file so
that ``hyprtk-rec stop`` works from a keybinding in a different process, and
turns a stray SIGINT into a finished, named file.

The state file is the contract: one recorder at a time, JSON, in
``$XDG_RUNTIME_DIR/hyprtk-rec/``. A state file whose pid is gone is stale and is
cleaned up on the next read — the alternative is a "recording" indicator that
survives a reboot.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field

CODECS = ("h264", "hevc", "vp9", "av1")
QUALITIES = ("low", "medium", "high")
CONTAINERS = ("mp4", "mkv", "webm")
BACKENDS = ("auto", "wf-recorder", "wl-screenrec")

#: Subjective quality -> x264-style CRF. wl-screenrec wants a bitrate instead;
#: the mapping there is rough on purpose (bits/s for a 1080p60-ish picture).
CRF = {
    "h264": {"low": 30, "medium": 23, "high": 18},
    "hevc": {"low": 32, "medium": 26, "high": 20},
    "vp9": {"low": 40, "medium": 32, "high": 24},
    "av1": {"low": 40, "medium": 32, "high": 24},
}
BITRATE = {"low": "3 MB", "medium": "6 MB", "high": "12 MB"}

WF_CODEC = {"h264": "libx264", "hevc": "libx265", "vp9": "libvpx-vp9", "av1": "libsvtav1"}
WS_CODEC = {"h264": "avc", "hevc": "hevc", "vp9": "vp9", "av1": "av1"}


class RecorderError(RuntimeError):
    """The recorder could not start or stop; the message is user-facing."""


def state_path() -> str:
    override = os.environ.get("HYPRTK_REC_STATE")
    if override:
        return override
    base = os.environ.get("XDG_RUNTIME_DIR")
    if base:
        return os.path.join(base, "hyprtk-rec", "state.json")
    return os.path.join("/tmp", f"hyprtk-rec-{os.getuid()}", "state.json")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def available(which=shutil.which) -> list[str]:
    found = []
    if which("wl-screenrec"):
        found.append("wl-screenrec")
    if which("wf-recorder"):
        found.append("wf-recorder")
    return found


def pick_backend(preference: str = "auto", which=shutil.which) -> str:
    """Resolve the backend, preferring hardware encoding when available."""
    if preference == "auto":
        found = available(which)
        if not found:
            raise RecorderError("no recorder installed (wf-recorder or wl-screenrec)")
        return found[0]
    if preference not in ("wf-recorder", "wl-screenrec"):
        raise RecorderError(f"unknown backend: {preference}")
    if not which(preference):
        # An explicit choice that is missing is an error, not a silent switch.
        raise RecorderError(f"{preference} is not installed")
    return preference


@dataclass
class Recording:
    pid: int
    backend: str
    source: str
    path: str
    geometry: str | None = None
    output: str | None = None
    audio: str = "none"
    audio_device: str | None = None
    codec: str = "h264"
    quality: str = "medium"
    fps: int = 60
    cursor: bool = True
    started: float = field(default_factory=time.time)
    paused_at: float | None = None
    paused_total: float = 0.0

    def elapsed(self, now: float | None = None) -> float:
        now = time.time() if now is None else now
        end = self.paused_at if self.paused_at is not None else now
        return max(0.0, end - self.started - self.paused_total)

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Recording":
        allowed = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**allowed)


# ------------------------------------------------------------------ argv ---

def build_argv(rec: Recording) -> list[str]:
    """The exact command line for a recording; pure enough to assert on."""
    if rec.backend == "wl-screenrec":
        argv = ["wl-screenrec", "-f", rec.path, "-m", str(int(rec.fps))]
        argv += ["--codec", WS_CODEC.get(rec.codec, "avc")]
        argv += ["-b", BITRATE.get(rec.quality, "6 MB")]
        if rec.geometry:
            argv += ["-g", rec.geometry]
        elif rec.output:
            argv += ["-o", rec.output]
        if not rec.cursor:
            argv.append("--no-cursor")
        return argv

    argv = ["wf-recorder", "-f", rec.path, "-c", WF_CODEC.get(rec.codec, "libx264")]
    argv += ["-p", f"crf={CRF.get(rec.codec, CRF['h264']).get(rec.quality, 23)}"]
    if rec.codec in ("h264", "hevc"):
        argv += ["-p", "preset=veryfast"]
    # A constant frame rate keeps seeking sane in every player; the damage
    # optimization still keeps the file small when nothing moves.
    argv += ["-r", str(int(rec.fps))]
    if rec.geometry:
        argv += ["-g", rec.geometry]
    elif rec.output:
        argv += ["-o", rec.output]
    if not rec.cursor:
        argv += ["--no-cursor"]
    return argv


def with_audio(argv: list[str], rec: Recording) -> list[str]:
    """Append the audio flags after the backend-specific ones are built."""
    from .audio import apply

    return apply(argv, rec.audio, rec.backend, rec.audio_device)


# ----------------------------------------------------------------- class ---

class Recorder:
    """Start/stop/pause the encoder, and keep the state file honest."""

    def __init__(self, path: str | None = None, *, spawn=None, which=shutil.which,
                 clock=time.time, signal_fn=os.kill, alive_fn=pid_alive) -> None:
        self.path = path or state_path()
        self._spawn = spawn or self._default_spawn
        self._which = which
        self._clock = clock
        self._signal = signal_fn
        self._alive = alive_fn
        self._process = None

    @staticmethod
    def _default_spawn(argv: list[str]):
        try:
            return subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        except FileNotFoundError as exc:
            raise RecorderError(f"{argv[0]} is not installed") from exc

    # -- state io
    def read_state(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_state(self, rec: Recording) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(rec.as_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.path)

    def _clear_state(self) -> None:
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def active(self) -> Recording | None:
        data = self.read_state()
        if not data:
            return None
        try:
            rec = Recording.from_dict(data)
        except TypeError:
            self._clear_state()
            return None
        if not self._alive(rec.pid):
            self._clear_state()
            return None
        return rec

    # -- lifecycle
    def start(self, *, path: str, source: str = "output", geometry: str | None = None,
              output: str | None = None, codec: str = "h264", quality: str = "medium",
              fps: int = 60, audio: str = "none", audio_device: str | None = None,
              cursor: bool = True, backend: str = "auto") -> Recording:
        current = self.active()
        if current is not None:
            raise RecorderError(f"already recording to {current.path}")

        backend = pick_backend(backend, self._which)
        rec = Recording(
            pid=0,
            backend=backend,
            source=source,
            path=str(path),
            geometry=geometry,
            output=output,
            audio=audio,
            audio_device=audio_device,
            codec=codec if codec in CODECS else "h264",
            quality=quality if quality in QUALITIES else "medium",
            fps=max(1, min(240, int(fps))),
            cursor=bool(cursor),
            started=self._clock(),
        )
        argv = with_audio(build_argv(rec), rec)
        os.makedirs(os.path.dirname(rec.path) or ".", exist_ok=True)
        process = self._spawn(argv)
        rec.pid = int(getattr(process, "pid", 0) or 0)
        self._process = process
        self._write_state(rec)
        return rec

    def stop(self, *, timeout: float = 10.0) -> str | None:
        """Ask the encoder to finish, then report the file it wrote.

        SIGINT is what wf-recorder and wl-screenrec both treat as "stop and
        finalize the container". SIGTERM only follows if that is ignored for
        longer than ``timeout``.
        """
        rec = self.active()
        if rec is None:
            return None
        process = self._process
        try:
            if process is not None and getattr(process, "pid", None) == rec.pid:
                process.send_signal(signal.SIGINT)
            else:
                self._signal(rec.pid, signal.SIGINT)
        except (ProcessLookupError, OSError):
            pass

        deadline = self._clock() + timeout
        while self._clock() < deadline:
            if not self._alive(rec.pid):
                break
            if process is not None:
                if process.poll() is not None:
                    break
            time.sleep(0.1)
        else:
            try:
                if process is not None:
                    process.kill()
                else:
                    self._signal(rec.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass

        if process is not None:
            try:
                process.wait(timeout=3)
            except Exception:
                pass

        self._clear_state()
        target = rec.path
        try:
            size = os.path.getsize(target)
        except OSError:
            return None
        if size <= 0:
            try:
                os.unlink(target)
            except OSError:
                pass
            return None
        return target

    def pause(self) -> bool:
        rec = self.active()
        if rec is None or rec.paused_at is not None:
            return False
        try:
            self._signal(rec.pid, signal.SIGSTOP)
        except (ProcessLookupError, OSError):
            return False
        rec.paused_at = self._clock()
        self._write_state(rec)
        return True

    def resume(self) -> bool:
        rec = self.active()
        if rec is None or rec.paused_at is None:
            return False
        try:
            self._signal(rec.pid, signal.SIGCONT)
        except (ProcessLookupError, OSError):
            return False
        rec.paused_total += max(0.0, self._clock() - rec.paused_at)
        rec.paused_at = None
        self._write_state(rec)
        return True

    def status(self) -> dict:
        rec = self.active()
        if rec is None:
            return {"recording": False}
        size = 0
        try:
            size = os.path.getsize(rec.path)
        except OSError:
            pass
        return {
            "recording": True,
            "paused": rec.paused_at is not None,
            "elapsed": round(rec.elapsed(self._clock()), 1),
            "path": rec.path,
            "backend": rec.backend,
            "source": rec.source,
            "audio": rec.audio,
            "codec": rec.codec,
            "fps": rec.fps,
            "bytes": size,
            "pid": rec.pid,
        }
