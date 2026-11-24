"""Sound — PipeWire/WirePlumber sinks, sources, per-app streams and mute.

The panel can set the default output and input volume/mute, pick the default
devices, and adjust every active application stream individually (each stream
is two rows: volume and mute).
"""

from __future__ import annotations

from .. import form, util
from . import base


def parse_wpctl(text: str) -> dict:
    """Parse ``wpctl status`` into sinks, sources and application streams."""
    data = {"sinks": [], "sources": [], "streams": []}
    section = ""
    for line in text.splitlines():
        stripped = line.strip().strip("│").strip()
        if stripped.endswith(":") and stripped and not stripped[0].isdigit():
            words = (stripped[:-1].replace("├", " ").replace("─", " ")
                     .replace("└", " ").split())
            name = words[-1].lower() if words else ""
            section = name if name in ("sinks", "sources", "streams") else ""
            continue
        if not section or not stripped:
            continue
        # Under Streams, only the top-level app node is a stream; the indented
        # port lines contain "<" or ">" and belong to it.
        if section == "streams" and ("<" in stripped or ">" in stripped):
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


def parse_cards(text: str) -> list[dict]:
    """Parse ``pactl list cards`` into cards with their selectable profiles."""
    cards: list[dict] = []
    card: dict | None = None
    in_profiles = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Card #"):
            card = {"name": "", "description": "", "active": "", "profiles": []}
            cards.append(card)
            in_profiles = False
            continue
        if card is None:
            continue
        if stripped.startswith("Name:"):
            card["name"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("device.description"):
            card["description"] = stripped.split("=", 1)[1].strip().strip('"')
            continue
        if stripped == "Profiles:":
            in_profiles = True
            continue
        if stripped.startswith("Active Profile:"):
            card["active"] = stripped.split(":", 1)[1].strip()
            in_profiles = False
            continue
        if stripped in ("Ports:", "Properties:", "Volume:", "Formats:"):
            in_profiles = False
            continue
        if in_profiles and ": " in stripped:
            ident, _, rest = stripped.partition(": ")
            label = rest.split(" (sinks:", 1)[0].strip()
            available = "available: yes" in rest
            card["profiles"].append({
                "id": ident.strip(), "label": label, "available": available,
            })
    return [card for card in cards if card["name"]]


def _volume(target: str) -> tuple[float, bool]:
    result = util.run(["wpctl", "get-volume", target], timeout=6)
    volume = 0.0
    muted = "[MUTED]" in result.out
    for part in result.out.split():
        try:
            volume = float(part)
            break
        except ValueError:
            continue
    return volume, muted


def _default_name(items: list[dict]) -> str:
    return next((item["name"] for item in items if item["default"]), "none")


def probe() -> dict:
    if util.which("wpctl") is None:
        return base.make_page("sound", [
            form.section("Unavailable", [base.missing_note("wpctl", "WirePlumber")]),
        ])

    parsed = parse_wpctl(util.run(["wpctl", "status"], timeout=10).out)
    sink_volume, sink_muted = _volume("@DEFAULT_AUDIO_SINK@")
    source_volume, source_muted = _volume("@DEFAULT_AUDIO_SOURCE@")

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

    card_rows: list[dict] = []
    for card in parse_cards(util.run(["pactl", "list", "cards"], timeout=10).out):
        choices = [
            {"value": profile["id"], "label": profile["label"]}
            for profile in card["profiles"] if profile["available"]
        ]
        if not choices:
            continue
        card_rows.append(form.choice(
            f"card::{card['name']}::profile",
            card["description"] or card["name"],
            card["active"],
            choices,
            help="Card profile (output/input combination and codec).",
        ))

    stream_rows: list[dict] = []
    for stream in parsed["streams"]:
        volume, muted = _volume(str(stream["id"]))
        stream_rows.append(form.slider(
            f"stream.{stream['id']}.volume", stream["name"],
            round(volume * 100), minimum=0, maximum=150,
            help="Application volume",
        ))
        stream_rows.append(form.toggle(
            f"stream.{stream['id']}.muted", "Mute", muted,
            help=f"Application stream {stream['id']}",
        ))
    if not stream_rows:
        stream_rows.append(form.note("No application streams are active.", "info"))

    return base.make_page("sound", [
        form.section("Output", [
            form.slider("volume", "Volume", round(sink_volume * 100),
                        minimum=0, maximum=150, unit="%"),
            form.toggle("muted", "Mute", sink_muted),
            form.info("Default sink", _default_name(parsed["sinks"])),
        ]),
        form.section("Output devices", [
            form.list_row(sink_items) if sink_items else form.note("No audio outputs found.", "warn"),
        ]),
        form.section("Input", [
            form.slider("input_volume", "Volume", round(source_volume * 100),
                        minimum=0, maximum=150, unit="%"),
            form.toggle("input_muted", "Mute", source_muted),
            form.info("Default source", _default_name(parsed["sources"])),
        ]),
        form.section("Input devices", [
            form.list_row(source_items) if source_items else form.note("No audio inputs found.", "warn"),
        ]),
        form.section("Card profiles", card_rows,
                     "Choose an output/input combination for each sound card.") if card_rows else
        form.section("Card profiles", [form.note("No selectable card profiles.", "info")]),
        form.section("Application streams", stream_rows,
                     "Per-application volume and mute for active PipeWire streams."),
        form.section("Service", [
            form.info("PipeWire", "running" if util.which("pipewire") else "not installed", mono=True),
        ]),
    ])


def _set_volume(target: str, level: int) -> str:
    result = util.run(["wpctl", "set-volume", target, f"{level}%"], timeout=8)
    if not result.ok:
        raise RuntimeError(result.text.strip() or f"wpctl set-volume {target} failed")
    return f"wpctl set-volume {target} {level}%"


def _set_mute(target: str, muted: bool) -> str:
    result = util.run(["wpctl", "set-mute", target, "1" if muted else "0"], timeout=8)
    if not result.ok:
        raise RuntimeError(result.text.strip() or f"wpctl set-mute {target} failed")
    return f"wpctl set-mute {target} {'1' if muted else '0'}"


def apply(changes: dict) -> dict:
    if util.which("wpctl") is None:
        return base.fail("wpctl is not installed")
    details: list[str] = []
    try:
        if "volume" in changes:
            details.append(_set_volume("@DEFAULT_AUDIO_SINK@",
                                      max(0, min(150, int(changes["volume"])))))
        if "muted" in changes:
            details.append(_set_mute("@DEFAULT_AUDIO_SINK@", bool(changes["muted"])))
        if "input_volume" in changes:
            details.append(_set_volume("@DEFAULT_AUDIO_SOURCE@",
                                      max(0, min(150, int(changes["input_volume"])))))
        if "input_muted" in changes:
            details.append(_set_mute("@DEFAULT_AUDIO_SOURCE@", bool(changes["input_muted"])))
        for key, value in (changes or {}).items():
            if key.startswith("card::") and key.endswith("::profile"):
                card = key[len("card::"):-len("::profile")]
                profile = str(value)
                if not card or not profile:
                    continue
                result = util.run(["pactl", "set-card-profile", card, profile], timeout=10)
                if not result.ok:
                    raise RuntimeError(result.text.strip() or f"pactl set-card-profile {card} failed")
                details.append(f"pactl set-card-profile {card} {profile}")
                continue
            if not key.startswith("stream."):
                continue
            parts = key.split(".")
            if len(parts) != 3 or not parts[1].isdigit():
                continue
            target, field = parts[1], parts[2]
            if field == "volume":
                details.append(_set_volume(target, max(0, min(150, int(value)))))
            elif field == "muted":
                details.append(_set_mute(target, bool(value)))
    except (RuntimeError, TypeError, ValueError) as exc:
        return base.fail(str(exc))
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Audio updated", details=details)


def action(name: str, args: dict) -> dict:
    ident = str(args.get("id") or "")
    if not ident:
        return base.fail("No device given")
    if name in ("sound.default_sink", "sound.default_source"):
        result = util.run(["wpctl", "set-default", ident], timeout=8)
    else:
        return base.fail(f"unknown action {name!r}")
    if not result.ok:
        return base.fail(result.text.strip() or "wpctl failed")
    return base.ok("Default device changed", details=[f"wpctl set-default {ident}"])
