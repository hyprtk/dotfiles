"""Audio sources, read from PipeWire/PulseAudio through ``pactl``.

Four honest choices: nothing, the default output's monitor (system audio), the
default input (microphone), or **both**. Both is a real mixed source: a null sink
with two loopbacks feeding it (the sink monitor and the mic), recorded from that
sink's monitor. It cannot be faked by recording one side, and the modules have to
be unloaded again or a crash leaves a sink named ``hyprtk-rec-mix`` behind.
"""

from __future__ import annotations

import re
import shutil
import subprocess

AUDIO = ("none", "system", "mic", "mix")

#: The null sink that carries the mix; its monitor is what gets recorded.
MIX_SINK = "hyprtk-rec-mix"


class AudioError(RuntimeError):
    """The mix could not be created; the message is safe to show a user."""


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


def load_module(*args: str) -> int:
    """Load a pactl module; returns its id, or 0 when that failed."""
    out = _pactl("load-module", *args).strip()
    try:
        return int(out.splitlines()[-1])
    except (ValueError, IndexError):
        return 0


def unload(modules: list[int]) -> None:
    for module in modules:
        if module:
            _pactl("unload-module", str(module))


def start_mix() -> tuple[list[int], str]:
    """Create the mix sink and return ``(module ids, source to record)``.

    Two loopbacks are needed because a monitor is just another source: one from
    the default sink's monitor (system audio) and one from the default input
    (microphone). Both land in a null sink, so nothing is routed back to the
    speakers.
    """
    sink = default_sink()
    mic = default_source()
    if not sink:
        raise AudioError("no default output to take system audio from")
    if not mic:
        raise AudioError("no default microphone to mix in")

    modules: list[int] = []
    null_sink = load_module("module-null-sink", f"sink_name={MIX_SINK}")
    if not null_sink:
        raise AudioError("pactl could not create the mix sink")
    modules.append(null_sink)
    for source in (sink + ".monitor", mic):
        module = load_module("module-loopback", f"sink={MIX_SINK}", f"source={source}")
        if not module:
            unload(modules)
            raise AudioError(f"pactl could not add {source} to the mix")
        modules.append(module)
    return modules, f"{MIX_SINK}.monitor"


def stop_mix(modules: list[int]) -> None:
    """Unload a mix, newest module first (the sink goes last)."""
    unload(list(reversed(modules or [])))


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
    if kind == "mix":
        return f"{MIX_SINK}.monitor"
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
        "mix": "System + microphone",
    }.get(mode, mode)
