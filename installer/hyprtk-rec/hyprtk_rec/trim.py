"""Trim a finished recording with ffmpeg's stream copy.

The recorder never re-encodes by default: ``-ss``/``-t`` with ``-c copy`` cuts on
keyframes, which is instant and lossless, and the right answer for a file that is
already encoded. A re-encode is available when frame accuracy matters, and only
then.

Times are seconds or ``MM:SS`` / ``HH:MM:SS``; the parser is the part worth
testing, because a typo in a time should be a clear error rather than a 4-second
clip.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FFMPEG = os.environ.get("HYPRTK_REC_FFMPEG", "ffmpeg")


class TrimError(RuntimeError):
    """The trim could not run; the message is user-facing."""


def parse_time(text: str | float | int | None) -> float | None:
    """``"12"``, ``"1:05"``, ``"0:01:05.5"`` → seconds; empty → ``None``."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        value = float(text)
        return value if value > 0 else None
    raw = str(text).strip()
    if not raw:
        return None
    parts = raw.split(":")
    if len(parts) > 3:
        raise TrimError(f"not a time: {raw} (use seconds, MM:SS or HH:MM:SS)")
    total = 0.0
    for part in parts:
        try:
            piece = float(part)
        except ValueError as exc:
            raise TrimError(f"not a time: {raw}") from exc
        if piece < 0:
            raise TrimError(f"not a time: {raw}")
        total = total * 60.0 + piece
    return total if total > 0 else None


def plan(path: str | os.PathLike, *, start: float | None = None,
         end: float | None = None, replace: bool = False,
         reencode: bool = False, program: str | None = None) -> dict:
    """Build the ffmpeg command and say where the result goes.

    With both ends the duration is explicit (``-ss START -t END-START``): an
    input-side ``-to`` means different things depending on where it sits, and a
    command that cannot be misread beats one that is shorter.
    """
    source = Path(path).expanduser()
    if start is not None and end is not None and end <= start:
        raise TrimError("the end must be after the start")
    if replace:
        output = source.with_name(source.stem + ".trim" + source.suffix)
    else:
        # unique_path: trimming the same clip twice used to overwrite the first
        # result silently (the output name was fixed and ffmpeg runs with -y).
        from .store import unique_path

        output = unique_path(source.with_name(source.stem + "-trimmed" + source.suffix))

    argv = [program or FFMPEG, "-hide_banner", "-loglevel", "error", "-y"]
    if start is not None:
        argv += ["-ss", f"{start:.3f}"]
    argv += ["-i", str(source)]
    if start is None and end is not None:
        argv += ["-t", f"{end:.3f}"]
    elif start is not None and end is not None:
        argv += ["-t", f"{end - start:.3f}"]
    if reencode:
        argv += ["-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "aac"]
    else:
        argv += ["-c", "copy"]
    argv += [str(output)]
    return {"argv": argv, "source": str(source), "output": str(output),
            "replace": bool(replace)}


def run(path: str | os.PathLike, *, start: float | None = None,
        end: float | None = None, replace: bool = False, reencode: bool = False,
        program: str | None = None, runner=subprocess.run) -> str:
    """Trim and return the path that holds the result."""
    program = program or FFMPEG
    if not shutil.which(program):
        raise TrimError("ffmpeg is not installed")
    job = plan(path, start=start, end=end, replace=replace,
               reencode=reencode, program=program)
    if not Path(job["source"]).is_file():
        raise TrimError(f"no such recording: {job['source']}")
    result = runner(job["argv"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=600, check=False)
    if result.returncode != 0:
        detail = (getattr(result, "stderr", b"") or b"").decode("utf-8", "replace").strip()
        try:
            os.unlink(job["output"])
        except OSError:
            pass
        raise TrimError(detail.splitlines()[-1] if detail else "ffmpeg failed")
    output = Path(job["output"])
    try:
        size = output.stat().st_size
    except OSError as exc:
        raise TrimError("ffmpeg wrote no file") from exc
    if size <= 0:
        raise TrimError("ffmpeg wrote an empty file")
    if replace:
        # Never overwrite the file an encoder is still writing.
        try:
            from .recorder import Recorder

            active = Recorder().active()
        except Exception:
            active = None
        if active is not None and os.path.abspath(active.path) == os.path.abspath(job["source"]):
            raise TrimError("that recording is still running")
        os.replace(output, job["source"])
        return job["source"]
    return job["output"]
