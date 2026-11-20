"""Audio sources, read from PipeWire/PulseAudio through ``pactl``.

The recorder offers three honest choices: nothing, the default output's monitor
(system audio), or the default input (microphone). "Both at once" needs a mixed
source, which is a v0.2 feature — pretending it works by recording one of them
would be worse than leaving it out.
"""

from __future__ import annotations

import re
import shutil
import subprocess

AUDIO = ("none", "system", "mic")


def _pactl(*args: str) -> str:
    if not shutil.which("pactl"):
        return ""
    try:
        result = subprocess.run(["pactl", *args], capture_output=True, text=True,
                                timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def default_sink() -> str:
    name = _pactl("get-default-sink").strip()
    if name:
        return name
    sinks = _pactl("list", "short", "sinks").splitlines()
    if sinks:
        return sinks[0].split("\t")[1]
    return ""


def default_source() -> str:
    name = _pactl("get-default-source").strip()
    if name:
        return name
    sources = _pactl("list", "short", "sources").splitlines()
    if sources:
        return sources[0].split("\t")[1]
    return ""


def system_monitor() -> str:
    """The monitor source of the default sink (what the desktop is playing)."""
    sink = default_sink()
    if sink:
        return sink + ".monitor"
    for line in _pactl("list", "short", "sources").splitlines():
        fields = line.split("\t")
        if len(fields) > 1 and fields[1].endswith(".monitor"):
            return fields[1]
    return ""


def sources() -> list[dict]:
    """Every capture source pactl reports, monitor and microphone alike."""
    rows = []
    for line in _pactl("list", "short", "sources").splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        name = fields[1]
        rows.append({
            "name": name,
            "driver": fields[2] if len(fields) > 2 else "",
            "spec": fields[3] if len(fields) > 3 else "",
            "monitor": name.endswith(".monitor"),
            "label": _friendly(name),
        })
    return rows


def _friendly(name: str) -> str:
    text = re.sub(r"^alsa_(input|output)\.", "", name)
    text = text.replace(".monitor", " (system)")
    text = text.replace("-00.", " · ").replace("_", " ")
    return text


def device_for(kind: str) -> str | None:
    """Resolve an audio mode to a PulseAudio/PipeWire source name."""
    if kind == "none":
        return None
    if kind == "system":
        return system_monitor() or None
    if kind == "mic":
        return default_source() or None
    raise ValueError(f"unknown audio mode: {kind}")


def apply(argv: list[str], mode: str, backend: str = "wf-recorder",
          device: str | None = None) -> list[str]:
    """Add the audio flags for ``mode`` to a recorder argv.

    ``device`` overrides the mode's own resolution (a named mic, for example).
    """
    name = device or device_for(mode)
    if not name:
        return argv
    if backend == "wl-screenrec":
        return argv + ["--audio", "--audio-device", name]
    return argv + [f"--audio={name}"]


def describe(mode: str) -> str:
    return {
        "none": "No audio",
        "system": "System audio",
        "mic": "Microphone",
    }.get(mode, mode)
