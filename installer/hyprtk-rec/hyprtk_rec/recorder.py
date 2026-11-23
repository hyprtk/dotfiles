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

import glob
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field

CODECS = ("h264", "hevc", "vp9", "av1")
QUALITIES = ("low", "medium", "high")
CONTAINERS = ("mp4", "mkv", "webm", "gif")
BACKENDS = ("auto", "wf-recorder", "wl-screenrec")

#: A GIF is a frame stack, not a video stream: above this the file is enormous
#: and the encoder cannot keep up with a live capture.
GIF_MAX_FPS = 30

#: VAAPI picks a quantiser, not a CRF, and only for these codecs here.
VAAPI_CODEC = {"h264": "h264_vaapi", "hevc": "hevc_vaapi"}
VAAPI_QP = {"low": 28, "medium": 24, "high": 20}

#: Seconds of replay history, and the signal that flushes it to the file.
REPLAY_MAX = 600

#: An encoder that rejects its options dies in milliseconds; anything still
#: running after this is treated as a real recording.
START_GRACE = 0.6

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


def render_devices() -> list[str]:
    return sorted(glob.glob("/dev/dri/renderD*"))


def vaapi_probe(device: str, *, runner=None, program: str = "ffmpeg") -> tuple[bool, str]:
    """Actually open the device: a render node is not the same as VAAPI.

    Mesa can expose ``renderD128`` and still fail ``vaInitialize`` (the box this
    was written on does exactly that), so the probe initialises the device and
    reports why it could not.
    """
    runner = runner or subprocess.run
    if not os.path.exists(device):
        return (False, "no render node")
    argv = [program, "-hide_banner", "-loglevel", "error",
            "-init_hw_device", f"vaapi=va:{device}",
            # ffmpeg refuses an output with no stream ("Output file does not
            # contain any stream"), so a bare `-f null -` reported *every*
            # device as broken. One frame of lavfi input is enough to force the
            # device to open without touching the screen.
            "-f", "lavfi", "-i", "nullsrc=s=32x32:d=1",
            "-frames:v", "1", "-f", "null", "-"]
    try:
        result = runner(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (False, str(exc) or "ffmpeg could not probe the device")
    if result.returncode != 0:
        detail = (getattr(result, "stderr", b"") or b"").decode("utf-8", "replace").strip()
        lines = [line.strip() for line in detail.splitlines() if line.strip()]
        # ffmpeg ends with a generic "Error parsing global options", so prefer
        # the line that actually names the VAAPI failure.
        for line in lines:
            if "vaapi" in line.lower() or "device creation failed" in line.lower():
                # Drop ffmpeg's "[VAAPI @ 0x55...] " prefix; the tail is the reason.
                return (False, re.sub(r"^\[[^\]]+\]\s*", "", line))
        return (False, lines[-1] if lines else "VAAPI device could not be opened")
    return (True, "")


def vaapi_status(*, runner=None, program: str = "ffmpeg") -> tuple[bool, str, str]:
    """``(available, device, reason)`` for the first working render node."""
    devices = render_devices()
    if not devices:
        return (False, "", "no /dev/dri/renderD* device")
    if not shutil.which(program):
        return (False, "", "ffmpeg is not installed")
    reason = ""
    for device in devices:
        ok, reason = vaapi_probe(device, runner=runner, program=program)
        if ok:
            return (True, device, "")
    return (False, "", reason)


def available(which=shutil.which) -> list[str]:
    found = []
    if which("wl-screenrec"):
        found.append("wl-screenrec")
    if which("wf-recorder"):
        found.append("wf-recorder")
    return found


def pick_backend(preference: str = "auto", which=shutil.which, *,
                 container: str = "mp4") -> str:
    """Resolve the backend, preferring hardware encoding when available."""
    if container == "gif":
        # wl-screenrec has no GIF encoder; this is a wf-recorder job even when
        # the user asked for wl-screenrec, and saying why beats a broken file.
        if not which("wf-recorder"):
            raise RecorderError("GIF output needs wf-recorder")
        return "wf-recorder"
    if preference == "auto":
        found = available(which)
        if not found:
            raise RecorderError("no recorder installed (wf-recorder or wl-screenrec)")
        if found[0] == "wl-screenrec":
            # wl-screenrec always encodes through VAAPI and exits rather than
            # falling back, so "auto" must only pick it when the device opens.
            # A machine whose session pins the wrong libva driver (or has no
            # driver at all) then records with wf-recorder's software encoder
            # instead of writing a 0-byte file.
            ok, _device, _reason = vaapi_status()
            if not ok and "wf-recorder" in found:
                return "wf-recorder"
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
    container: str = "mp4"
    replay: int = 0
    vaapi: bool = False
    vaapi_device: str | None = None
    geometry: str | None = None
    output: str | None = None
    audio: str = "none"
    audio_device: str | None = None
    audio_modules: list[int] = field(default_factory=list)
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
    if rec.container == "gif":
        # `-c gif` needs a pixel format the gif encoder accepts; rgb8 is the
        # one that opens without an avcodec argument error.
        argv = ["wf-recorder", "-f", rec.path, "-c", "gif", "-x", "rgb8"]
        argv += ["-r", str(int(rec.fps))]
        if rec.geometry:
            argv += ["-g", rec.geometry]
        elif rec.output:
            argv += ["-o", rec.output]
        if not rec.cursor:
            argv += ["--no-cursor"]
        return argv

    if rec.vaapi and rec.backend == "wf-recorder":
        codec = VAAPI_CODEC.get(rec.codec, "h264_vaapi")
        argv = ["wf-recorder", "-f", rec.path, "-c", codec]
        if rec.vaapi_device:
            argv += ["-d", rec.vaapi_device]
        argv += ["-p", f"qp={VAAPI_QP.get(rec.quality, 24)}"]
        argv += ["-r", str(int(rec.fps))]
        if rec.geometry:
            argv += ["-g", rec.geometry]
        elif rec.output:
            argv += ["-o", rec.output]
        if not rec.cursor:
            argv += ["--no-cursor"]
        return argv

    if rec.backend == "wl-screenrec":
        argv = ["wl-screenrec", "-f", rec.path, "-m", str(int(rec.fps))]
        if rec.replay:
            # Nothing is written until SIGUSR1: the encoder keeps the last N
            # seconds in memory and flushes them to the file on demand.
            argv += ["--history", str(int(rec.replay))]
            # The trim can only drop whole GOPs (it keeps the span between the
            # first two keyframes), so the encoder's default GOP makes "2 s"
            # keep ~5 s. One keyframe per second keeps the window within ~1 s.
            argv += ["--gop-size", str(max(1, int(rec.fps)))]
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
    if rec.container == "gif":
        # A GIF has no audio track; asking for one fails the whole capture.
        return argv
    from .audio import apply

    return apply(argv, rec.audio, rec.backend, rec.audio_device)


# ----------------------------------------------------------------- class ---

class Recorder:
    """Start/stop/pause the encoder, and keep the state file honest."""

    def __init__(self, path: str | None = None, *, spawn=None, which=shutil.which,
                 clock=time.time, signal_fn=os.kill, alive_fn=pid_alive,
                 grace: float = START_GRACE) -> None:
        self.path = path or state_path()
        self._spawn = spawn or self._default_spawn
        self._which = which
        self._clock = clock
        self._signal = signal_fn
        self._alive = alive_fn
        self._grace = grace
        self._process = None

    def _default_spawn(self, argv: list[str]):
        log_path = self._encoder_log()
        try:
            os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
            log = open(log_path, "w", encoding="utf-8")
        except OSError:
            log = subprocess.DEVNULL
        try:
            return subprocess.Popen(argv, stdout=log, stderr=log,
                                    start_new_session=True)
        except FileNotFoundError as exc:
            raise RecorderError(f"{argv[0]} is not installed") from exc

    def _encoder_log(self) -> str:
        """Where the encoder's stderr goes, so a dead start can be explained."""
        base = os.path.dirname(os.path.abspath(self.path)) or tempfile.gettempdir()
        return os.path.join(base, "encoder.log")

    def _explain_exit(self, code: int) -> str:
        head = f"the recorder exited immediately (status {code})"
        detail = self._last_encoder_error()
        return f"{head}: {detail}" if detail else head

    def _last_encoder_error(self) -> str:
        try:
            with open(self._encoder_log(), encoding="utf-8", errors="replace") as handle:
                lines = [line.strip() for line in handle if line.strip()]
        except OSError:
            return ""
        if not lines:
            return ""
        # ffmpeg/ffmpeg-based encoders end with a generic line, so prefer the
        # one that names the actual failure.
        for line in lines:
            if "vaapi" in line.lower() or "error" in line.lower():
                return line
        return lines[-1]

    def _died_immediately(self, process) -> str:
        """Empty string while the encoder is alive, else why it exited.

        A recorder that rejects its options exits in milliseconds. Without this
        check the state file looks valid, the next read drops it as stale, and
        the user is left with a 0-byte file and a "recording" message.
        """
        poll = getattr(process, "poll", None)
        if poll is None:
            return ""
        code = poll()  # an encoder that rejects its options has already exited
        if code is not None:
            return self._explain_exit(code)
        deadline = time.monotonic() + self._grace
        while time.monotonic() < deadline:
            time.sleep(0.05)
            code = poll()
            if code is not None:
                return self._explain_exit(code)
        return ""

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

    def _discard(self, rec: Recording) -> None:
        """Forget a dead recording and take its audio mix down with it."""
        from . import audio as audio_module

        if rec.audio_modules:
            audio_module.stop_mix(rec.audio_modules)
        self._clear_state()

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
            self._discard(rec)
            return None
        return rec

    # -- lifecycle
    def start(self, *, path: str, source: str = "output", geometry: str | None = None,
              output: str | None = None, codec: str = "h264", quality: str = "medium",
              fps: int = 60, audio: str = "none", audio_device: str | None = None,
              cursor: bool = True, backend: str = "auto",
              container: str = "mp4", vaapi: bool = False,
              replay: int = 0) -> Recording:
        current = self.active()
        if current is not None:
            raise RecorderError(f"already recording to {current.path}")

        container = container if container in CONTAINERS else "mp4"
        replay = max(0, min(REPLAY_MAX, int(replay or 0)))
        if replay:
            # The buffer is a wl-screenrec feature; wf-recorder has nothing
            # equivalent, and a GIF cannot hold one.
            if container == "gif":
                raise RecorderError("a GIF cannot be a replay buffer")
            if not self._which("wl-screenrec"):
                raise RecorderError("the replay buffer needs wl-screenrec")
            backend = "wl-screenrec"
        backend = pick_backend(backend, self._which, container=container)
        vaapi_device = None
        if vaapi and backend == "wf-recorder":
            if codec not in VAAPI_CODEC:
                raise RecorderError(
                    f"VAAPI cannot encode {codec} here (use h264 or hevc)")
            ok, vaapi_device, reason = vaapi_status()
            if not ok:
                raise RecorderError(f"VAAPI is not available: {reason}")
        else:
            vaapi = False
        mix_modules: list[int] = []
        if audio == "mix" and not audio_device:
            from . import audio as audio_module

            try:
                mix_modules, audio_device = audio_module.start_mix()
            except audio_module.AudioError as exc:
                raise RecorderError(str(exc)) from exc
        rec = Recording(
            pid=0,
            backend=backend,
            source=source,
            path=str(path),
            container=container,
            replay=replay,
            vaapi=bool(vaapi),
            vaapi_device=vaapi_device,
            geometry=geometry,
            output=output,
            audio=audio,
            audio_device=audio_device,
            audio_modules=mix_modules,
            codec=codec if codec in CODECS else "h264",
            quality=quality if quality in QUALITIES else "medium",
            fps=max(1, min(GIF_MAX_FPS if container == "gif" else 240, int(fps))),
            cursor=bool(cursor),
            started=self._clock(),
        )
        argv = with_audio(build_argv(rec), rec)
        os.makedirs(os.path.dirname(rec.path) or ".", exist_ok=True)
        try:
            process = self._spawn(argv)
        except Exception:
            if mix_modules:
                audio_module.stop_mix(mix_modules)
            raise
        rec.pid = int(getattr(process, "pid", 0) or 0)
        self._process = process
        failure = self._died_immediately(process)
        if failure:
            self._process = None
            if mix_modules:
                audio_module.stop_mix(mix_modules)
            self._remove_empty(rec.path)
            raise RecorderError(failure)
        self._write_state(rec)
        return rec

    @staticmethod
    def _remove_empty(path: str) -> None:
        try:
            if os.path.getsize(path) == 0:
                os.unlink(path)
        except OSError:
            pass

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

        if rec.audio_modules:
            from . import audio as audio_module

            audio_module.stop_mix(rec.audio_modules)
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

    def recover(self) -> Recording | None:
        """A crashed recording: the encoder is gone but the file may be fine.

        Returns the orphaned :class:`Recording` and clears the state file. The
        file was written under its final name from the first frame, so there is
        nothing to rename — only the decision of whether to keep it.
        """
        data = self.read_state()
        if not data:
            return None
        try:
            rec = Recording.from_dict(data)
        except TypeError:
            self._clear_state()
            return None
        if self._alive(rec.pid):
            return None
        self._discard(rec)
        try:
            if os.path.getsize(rec.path) > 0:
                return rec
        except OSError:
            pass
        return None

    def save_replay(self) -> str | None:
        """Flush the buffered seconds to the file and keep recording."""
        rec = self.active()
        if rec is None or not rec.replay:
            return None
        try:
            self._signal(rec.pid, signal.SIGUSR1)
        except (ProcessLookupError, OSError):
            return None
        return rec.path

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
            "container": rec.container,
            "replay": rec.replay,
            "vaapi": rec.vaapi,
            "codec": rec.codec,
            "fps": rec.fps,
            "bytes": size,
            "pid": rec.pid,
        }
