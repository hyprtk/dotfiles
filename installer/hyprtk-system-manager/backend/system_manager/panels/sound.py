"""Sound — PipeWire/WirePlumber sinks, sources, volume and mute."""

from __future__ import annotations

from .. import form, util
from . import base


def parse_wpctl(text: str) -> dict:
    """Parse ``wpctl status`` into sinks, sources and default ids."""
    data = {"sinks": [], "sources": []}
    section = ""
    for line in text.splitlines():
        stripped = line.strip().strip("│").strip()
        if stripped.endswith(":") and stripped and not stripped[0].isdigit():
            words = stripped[:-1].replace("├", " ").replace("─", " ").split()
            name = words[-1].lower() if words else ""
            section = name if name in ("sinks", "sources") else ""
            continue
        if not section or not stripped:
            continue
        default = stripped.startswith("*")
        cleaned = stripped.lstrip("*").strip()
        ident, _, rest = cleaned.partition(".")
        if not ident.strip().isdigit():
            continue
        label = rest.strip()
        volume = ""
        if "[vol:" in label:
            label, _, tail = label.partition("[vol:")
            volume = tail.split("]", 1)[0].strip()
        data[section].append({
            "id": int(ident.strip()),
            "name": label.strip(),
            "volume": volume,
            "default": default,
        })
    return data


def _default_volume() -> tuple[float, bool]:
    result = util.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=6)
    volume = 0.0
    muted = "[MUTED]" in result.out
    for part in result.out.split():
        try:
            volume = float(part)
            break
        except ValueError:
            continue
    return volume, muted


def probe() -> dict:
    if util.which("wpctl") is None:
        return base.make_page("sound", [
            form.section("Unavailable", [base.missing_note("wpctl", "WirePlumber")]),
        ])

    status = util.run(["wpctl", "status"], timeout=10)
    parsed = parse_wpctl(status.out)
    volume, muted = _default_volume()

    sink_items = [
        {"title": sink["name"], "subtitle": f"id {sink['id']} · volume {sink['volume'] or '?'}",
         "badges": ["default"] if sink["default"] else [],
         "actions": [] if sink["default"] else [
             {"label": "Use as output", "action": "sound.default_sink", "args": {"id": sink["id"]}},
         ]}
        for sink in parsed["sinks"]
    ]
    source_items = [
        {"title": source["name"], "subtitle": f"id {source['id']}",
         "badges": ["default"] if source["default"] else [],
         "actions": [] if source["default"] else [
             {"label": "Use as input", "action": "sound.default_source", "args": {"id": source["id"]}},
         ]}
        for source in parsed["sources"]
    ]

    return base.make_page("sound", [
        form.section("Output", [
            form.slider("volume", "Volume", round(volume * 100), minimum=0, maximum=100, unit="%"),
            form.toggle("muted", "Mute", muted),
            form.info("Default sink", next((s["name"] for s in parsed["sinks"] if s["default"]), "none")),
        ]),
        form.section("Output devices", [
            form.list_row(sink_items) if sink_items else form.note("No audio outputs found.", "warn"),
        ]),
        form.section("Input devices", [
            form.list_row(source_items) if source_items else form.note("No audio inputs found.", "warn"),
        ]),
        form.section("Service", [
            form.info("PipeWire", "running" if util.which("pipewire") else "not installed", mono=True),
            form.note("Per-application streams and profiles arrive in the next milestone.", "info"),
        ]),
    ])


def apply(changes: dict) -> dict:
    if util.which("wpctl") is None:
        return base.fail("wpctl is not installed")
    details: list[str] = []
    if "volume" in changes:
        level = max(0, min(100, int(changes["volume"])))
        result = util.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{level}%"], timeout=8)
        if not result.ok:
            return base.fail(result.text.strip() or "wpctl failed")
        details.append(f"wpctl set-volume {level}%")
    if "muted" in changes:
        value = "1" if changes["muted"] else "0"
        result = util.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", value], timeout=8)
        if not result.ok:
            return base.fail(result.text.strip() or "wpctl failed")
        details.append(f"wpctl set-mute {value}")
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Audio updated", details=details)


def action(name: str, args: dict) -> dict:
    ident = str(args.get("id") or "")
    if not ident:
        return base.fail("No device given")
    if name == "sound.default_sink":
        result = util.run(["wpctl", "set-default", ident], timeout=8)
    elif name == "sound.default_source":
        result = util.run(["wpctl", "set-default", ident], timeout=8)
    else:
        return base.fail(f"unknown action {name!r}")
    if not result.ok:
        return base.fail(result.text.strip() or "wpctl failed")
    return base.ok("Default device changed", details=[f"wpctl set-default {ident}"])
