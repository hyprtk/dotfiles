"""Input Devices — keyboard layout, repeat and pointer behaviour (live)."""

from __future__ import annotations

import json
import re

from .. import form, paths, util
from . import base

START = "-- >>> hyprtk-system-manager managed input (do not edit this block by hand)"
END = "-- <<< hyprtk-system-manager managed input"

OPTIONS = {
    "kb_layout": ("input:kb_layout", "str"),
    "kb_variant": ("input:kb_variant", "str"),
    "repeat_rate": ("input:repeat_rate", "int"),
    "repeat_delay": ("input:repeat_delay", "int"),
    "sensitivity": ("input:sensitivity", "float"),
    "accel_profile": ("input:accel_profile", "str"),
    "natural_scroll": ("input:touchpad:natural_scroll", "bool"),
    "tap_to_click": ("input:touchpad:tap-to-click", "bool"),
    "disable_while_typing": ("input:touchpad:disable_while_typing", "bool"),
}


# Apply is a pure file edit, so a dry run can show it as a diff.
PREVIEW = "files"

def parse_option(text: str) -> str:
    """``hyprctl getoption`` prints ``str: gb`` / ``int: 25`` on the first line.

    An unset string option prints the literal marker ``[[EMPTY]]``, which must
    become an empty value — writing it into the Lua block would configure a
    profile called "[[EMPTY]]" instead of leaving the option alone.
    """
    for line in text.splitlines():
        if ":" in line and line.split(":", 1)[0].strip() in ("str", "int", "float", "bool", "color"):
            value = line.split(":", 1)[1].strip().strip('"')
            return "" if value == "[[EMPTY]]" else value
    return ""


def _get(key: str) -> str:
    hypr_key, _kind = OPTIONS[key]
    return parse_option(util.run(["hyprctl", "getoption", hypr_key], timeout=6).out)


def _devices() -> dict[str, list[str]]:
    payload = util.run_json(["hyprctl", "devices", "-j"], timeout=8)
    out = {"keyboards": [], "mice": [], "touchpads": []}
    if not isinstance(payload, dict):
        return out
    for kind in out:
        for item in payload.get(kind) or []:
            if isinstance(item, dict) and item.get("name"):
                out[kind].append(str(item["name"]))
    return out


def probe() -> dict:
    if util.which("hyprctl") is None:
        return base.make_page("input", [
            form.section("Unavailable", [base.missing_note("hyprctl", "Hyprland")]),
        ])

    devices = _devices()
    layout = _get("kb_layout") or "us"
    variant = _get("kb_variant")
    rate = int(float(_get("repeat_rate") or 25))
    delay = int(float(_get("repeat_delay") or 600))
    sensitivity = float(_get("sensitivity") or 0.0)
    profile = _get("accel_profile")
    natural = _get("natural_scroll") == "true"
    tap = _get("tap_to_click") == "true"
    dwt = _get("disable_while_typing") == "true"

    config = paths.input_file()
    managed = bool(config and START in util.read_text(config))
    page = base.make_page("input", [
        form.section("Keyboard", [
            form.text("kb_layout", "Layout", layout, help="XKB layout code, e.g. gb, us, de."),
            form.text("kb_variant", "Variant", variant),
            form.number("repeat_rate", "Repeat rate", rate, minimum=1, maximum=100),
            form.number("repeat_delay", "Repeat delay", delay, minimum=100, maximum=2000, unit="ms"),
        ], "Written to input.lua and applied by reloading the compositor."),
        form.section("Pointer", [
            form.slider("sensitivity", "Mouse sensitivity", sensitivity, minimum=-1.0, maximum=1.0, step=0.05),
            form.choice("accel_profile", "Acceleration profile", profile, [
                {"value": "", "label": "Compositor default"},
                {"value": "flat", "label": "Flat"},
                {"value": "adaptive", "label": "Adaptive"},
            ]),
        ]),
        form.section("Touchpad", [
            form.toggle("natural_scroll", "Natural scrolling", natural),
            form.toggle("tap_to_click", "Tap to click", tap),
            form.toggle("disable_while_typing", "Disable while typing", dwt),
        ]),
        form.section("Connected devices", [
            form.kv(
                [{"label": f"Keyboard · {name}", "value": ""} for name in devices["keyboards"][:15]] +
                [{"label": f"Pointer · {name}", "value": ""} for name in devices["mice"][:15]]
            ),
        ]),
        form.section("Persistence", [
            form.note("Applying writes the managed block into input.lua and reloads "
                      "Hyprland — this build has no runtime `keyword` path. The block "
                      "only contains the settings on this page.", "info"),
            form.action("Save current values", "input.persist", variant="primary"),
            form.action("Remove saved settings", "input.clear_persistent"),
            form.info("Config file", str(config) if config else "not found", mono=True),
            form.action("Open Hyprland settings", "input.open_hyprland"),
        ]),
    ], status="partial")
    page["managed"] = managed
    return page


def _merge(values: dict, changes: dict) -> dict:
    """Overlay validated panel changes onto the live values."""
    merged = dict(values)
    for key, value in (changes or {}).items():
        if key not in OPTIONS:
            continue
        kind = OPTIONS[key][1]
        if kind == "bool":
            merged[key] = bool(value)
        elif kind == "int":
            merged[key] = int(value)
        elif kind == "float":
            merged[key] = float(value)
        else:
            merged[key] = "" if value is None else str(value).strip()
    merged["repeat_rate"] = max(1, min(100, int(merged.get("repeat_rate") or 25)))
    merged["repeat_delay"] = max(100, min(2000, int(merged.get("repeat_delay") or 600)))
    merged["sensitivity"] = max(-1.0, min(1.0, float(merged.get("sensitivity") or 0.0)))
    return merged


def apply(changes: dict) -> dict:
    """Write the managed block and reload.

    ``hyprctl keyword`` is unsupported on this Lua-dispatch build (it answers
    "unknown request" while exiting 0), so a runtime change is only possible by
    writing the config and reloading — the same path the Displays panel uses.
    """
    if not any(key in OPTIONS for key in (changes or {})):
        return base.ok("Nothing to change")
    values = _merge(_values(), changes)
    return _write(_lua_block(values),
                  message="Input settings applied and saved to input.lua")


def _values() -> dict:
    return {
        "kb_layout": _get("kb_layout") or "us",
        "kb_variant": _get("kb_variant"),
        "repeat_rate": int(float(_get("repeat_rate") or 25)),
        "repeat_delay": int(float(_get("repeat_delay") or 600)),
        "sensitivity": float(_get("sensitivity") or 0.0),
        "accel_profile": _get("accel_profile"),
        "natural_scroll": _get("natural_scroll") == "true",
        "tap_to_click": _get("tap_to_click") == "true",
        "disable_while_typing": _get("disable_while_typing") == "true",
    }


def _lua_block(values: dict) -> str:
    lines = [
        START,
        "hl.config({",
        "    input = {",
        f"        kb_layout = {json.dumps(values['kb_layout'])},",
        f"        kb_variant = {json.dumps(values['kb_variant'])},",
        f"        repeat_rate = {values['repeat_rate']},",
        f"        repeat_delay = {values['repeat_delay']},",
        f"        sensitivity = {values['sensitivity']:g},",
    ]
    if values["accel_profile"]:
        lines.append(f"        accel_profile = {json.dumps(values['accel_profile'])},")
    lines += [
        "        touchpad = {",
        f"            natural_scroll = {'true' if values['natural_scroll'] else 'false'},",
        f"            [\"tap-to-click\"] = {'true' if values['tap_to_click'] else 'false'},",
        f"            disable_while_typing = {'true' if values['disable_while_typing'] else 'false'},",
        "        },",
        "    },",
        "})",
        END,
    ]
    return "\n".join(lines) + "\n"


def _strip_block(text: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    return pattern.sub("", text)


def _write(block: str | None, message: str = "") -> dict:
    target = paths.input_file()
    if target is None:
        return base.fail("No Hyprland Lua config found (input.lua)")
    original = util.read_text(target)
    stripped = _strip_block(original).rstrip()
    updated = stripped + ("\n\n" + block if block else "\n")
    if updated == original:
        return base.ok("Nothing to change")
    util.atomic_write(target, updated)
    ok, text = base.hypr_reload()
    if not ok:
        util.atomic_write(target, original)
        base.hypr_reload()
        return base.fail(f"Hyprland rejected the block: {text}")
    return base.ok(
        message or ("Saved input settings to input.lua" if block
                    else "Removed saved input settings"),
        details=[str(target)],
    )


def action(name: str, args: dict) -> dict:
    if name == "input.persist":
        return _write(_lua_block(_values()))
    if name == "input.clear_persistent":
        target = paths.input_file()
        if target and START not in util.read_text(target):
            return base.ok("No saved input settings to remove")
        return _write(None)
    if name == "input.open_hyprland":
        argv = ["config-manager", "open", "--page", "input"]
        if util.which(argv[0]) is None:
            return base.fail("config-manager is not installed")
        util.run(argv, timeout=10)
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
