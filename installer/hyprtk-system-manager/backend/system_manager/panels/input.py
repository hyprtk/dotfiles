"""Input Devices — keyboard layout, repeat and pointer behaviour (live)."""

from __future__ import annotations

from .. import form, util
from . import base

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


def parse_option(text: str) -> str:
    """``hyprctl getoption`` prints ``str: gb`` / ``int: 25`` on the first line."""
    for line in text.splitlines():
        if ":" in line and line.split(":", 1)[0].strip() in ("str", "int", "float", "bool", "color"):
            return line.split(":", 1)[1].strip().strip('"')
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

    return base.make_page("input", [
        form.section("Keyboard", [
            form.text("kb_layout", "Layout", layout, help="XKB layout code, e.g. gb, us, de."),
            form.text("kb_variant", "Variant", variant),
            form.number("repeat_rate", "Repeat rate", rate, minimum=1, maximum=100),
            form.number("repeat_delay", "Repeat delay", delay, minimum=100, maximum=2000, unit="ms"),
        ], "Applied to the running compositor immediately."),
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
            form.note("These changes last until Hyprland reloads its config. For a "
                      "permanent setting use Hyprland settings (config-manager).", "warn"),
            form.action("Open Hyprland settings", "input.open_hyprland"),
        ]),
    ], status="live")


def apply(changes: dict) -> dict:
    details: list[str] = []
    for key, value in (changes or {}).items():
        if key not in OPTIONS:
            continue
        hypr_key, kind = OPTIONS[key]
        if kind == "bool":
            text = "true" if value else "false"
        elif kind == "float":
            text = f"{float(value):g}"
        else:
            text = str(value)
        result = util.run(["hyprctl", "keyword", hypr_key, text], timeout=8)
        if not result.ok:
            return base.fail(f"hyprctl rejected {hypr_key}: {result.text.strip()}")
        details.append(f"{hypr_key} = {text}")
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Input settings applied for this session", details=details, live=True)


def action(name: str, args: dict) -> dict:
    if name == "input.open_hyprland":
        argv = ["config-manager", "open", "--page", "input"]
        if util.which(argv[0]) is None:
            return base.fail("config-manager is not installed")
        util.run(argv, timeout=10)
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
