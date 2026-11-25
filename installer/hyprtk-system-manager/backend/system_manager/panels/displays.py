"""Displays — Hyprland monitor layout.

Changes apply live through ``hyprctl keyword monitor``. Persistence writes a
clearly delimited managed block into ``monitors.lua``; the rest of the file is
never touched, and the block can be removed by clearing it in the UI.
"""

from __future__ import annotations

import json
import re
import time

from .. import form, paths, util
from . import base

START = "-- >>> hyprtk-system-manager managed monitors (do not edit this block by hand)"
END = "-- <<< hyprtk-system-manager managed monitors"

TRANSFORMS = [
    {"value": "0", "label": "Normal"},
    {"value": "1", "label": "90° clockwise"},
    {"value": "2", "label": "180°"},
    {"value": "3", "label": "270° clockwise"},
    {"value": "4", "label": "Flipped"},
    {"value": "5", "label": "Flipped 90°"},
    {"value": "6", "label": "Flipped 180°"},
    {"value": "7", "label": "Flipped 270°"},
]


# Apply is a pure file edit, so a dry run can show it as a diff.
PREVIEW = "files"

def _mode(value: str) -> dict | None:
    raw = str(value).strip().removesuffix("Hz")
    try:
        size, refresh = raw.split("@", 1)
        width, height = size.lower().split("x", 1)
        return {"value": raw, "label": f"{int(width)}×{int(height)} @ {float(refresh):.2f} Hz",
                "width": int(width), "height": int(height), "refresh": float(refresh)}
    except (TypeError, ValueError):
        return None


def parse_monitors(payload) -> list[dict]:
    monitors: list[dict] = []
    for mon in payload if isinstance(payload, list) else []:
        if not isinstance(mon, dict):
            continue
        name = str(mon.get("name") or "")
        if not name:
            continue
        modes: list[dict] = []
        seen: set[str] = set()
        for entry in mon.get("availableModes") or []:
            mode = _mode(str(entry))
            if mode is None or mode["value"] in seen:
                continue
            seen.add(mode["value"])
            modes.append(mode)
        width = int(mon.get("width") or 0)
        height = int(mon.get("height") or 0)
        refresh = float(mon.get("refreshRate") or 0)
        current = f"{width}x{height}@{refresh:.2f}" if width and height and refresh else ""
        if current and current not in seen:
            modes.insert(0, {"value": current, "label": f"{width}×{height} @ {refresh:.2f} Hz",
                             "width": width, "height": height, "refresh": refresh})
        description = " ".join(str(part) for part in (
            mon.get("make"), mon.get("model"), mon.get("serial")) if part) or str(mon.get("description") or "")
        monitors.append({
            "name": name,
            "description": description,
            "width": width,
            "height": height,
            "refreshRate": refresh,
            "x": int(mon.get("x") or 0),
            "y": int(mon.get("y") or 0),
            "scale": float(mon.get("scale") or 1.0),
            "transform": int(mon.get("transform") or 0),
            "vrr": int(mon.get("vrr") or 0),
            # hyprctl reports the literal string "none" when an output is not
            # mirroring, which must not become `mirror = "none"` in the config.
            "mirror": "" if str(mon.get("mirrorOf") or "").lower() in ("", "none")
                      else str(mon.get("mirrorOf")),
            "format": str(mon.get("currentFormat") or ""),
            "currentCm": str(mon.get("colorManagementPreset") or ""),
            "disabled": bool(mon.get("disabled")),
            "modes": modes,
            "currentMode": current,
        })
    return monitors


def _live_monitors() -> list[dict]:
    payload = util.run_json(["hyprctl", "-j", "monitors", "all"], timeout=8)
    if not isinstance(payload, list):
        payload = util.run_json(["hyprctl", "-j", "monitors"], timeout=8)
    return parse_monitors(payload)


def probe() -> dict:
    if util.which("hyprctl") is None:
        page = base.make_page("displays", [
            form.section("Unavailable", [base.missing_note("hyprctl", "Hyprland")]),
        ])
        page["monitors"] = []
        return page

    monitors = _live_monitors()
    rows = []
    for mon in monitors:
        rows.append(form.info(
            mon["name"],
            f"{mon['width']}×{mon['height']} @ {mon['refreshRate']:.2f} Hz · "
            f"{mon['scale']:.2f}× · transform {mon['transform']} · {mon['x']}×{mon['y']}",
            mono=True,
        ))
    if not rows:
        rows.append(form.note("No monitors reported by the compositor.", "warn"))

    sections = [
        form.section("Connected monitors", rows),
        form.section("Layout", [
            form.note("Pick a monitor, then choose its mode, scale, rotation and position. "
                      "Changes apply immediately; use “Make persistent” to write them into "
                      "monitors.lua.", "info"),
        ]),
        form.section("Maintenance", [
            form.action("Reload Hyprland config", "displays.reload"),
            form.action("Remove the managed block", "displays.clear_persistent",
                        variant="default", danger=False),
        ]),
    ]
    page = base.make_page("displays", sections)
    page["monitors"] = monitors
    page["transforms"] = TRANSFORMS
    page["configFile"] = str(paths.monitors_file() or "")
    page["managed"] = bool(paths.monitors_file() and START in util.read_text(paths.monitors_file()))
    page["profiles"] = [
        {"name": name, "created": entry.get("created") or "",
         "count": len(entry.get("monitors") or [])}
        for name, entry in sorted(load_profiles().items())
    ]
    return page


def _lua_block(monitors: list[dict]) -> str:
    lines = [START]
    for mon in monitors:
        fields = [f"output = {json.dumps(mon['name'])}"]
        if mon.get("disabled"):
            fields.append('mode = "disable"')
        else:
            position = "{}x{}".format(int(mon.get("x") or 0), int(mon.get("y") or 0))
            mode = mon.get("mode") or mon.get("currentMode") or "preferred"
            fields.append("mode = " + json.dumps(str(mode)))
            fields.append("position = " + json.dumps(position))
            fields.append("scale = {:.2f}".format(float(mon.get("scale") or 1.0)).rstrip("0").rstrip("."))
            fields.append("transform = {}".format(int(mon.get("transform") or 0)))
            vrr = int(mon.get("vrr") or 0)
            if vrr:
                fields.append("vrr = {}".format(vrr))
            mirror = str(mon.get("mirror") or "")
            if mirror:
                fields.append("mirror = {}".format(json.dumps(mirror)))
            bitdepth = str(mon.get("bitdepth") or "auto")
            if bitdepth not in ("", "auto"):
                fields.append("bitdepth = {}".format(int(bitdepth)))
            cm = str(mon.get("cm") or "auto")
            if cm not in ("", "auto"):
                fields.append("cm = {}".format(json.dumps(cm)))
        lines.append("hl.monitor({ " + ", ".join(fields) + " })")
    lines.append(END)
    return "\n".join(lines) + "\n"


def _strip_block(text: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    return pattern.sub("", text)


def profiles_file():
    return paths.CONFIG_ROOT / "displays.json"


def load_profiles() -> dict:
    data = util.read_json(profiles_file(), {})
    profiles = data.get("profiles") if isinstance(data, dict) else None
    return profiles if isinstance(profiles, dict) else {}


def save_profiles(profiles: dict) -> None:
    target = profiles_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(target, {"version": 1, "profiles": profiles})


def _profile_monitors(monitors: list[dict]) -> list[dict]:
    keep = ("name", "mode", "x", "y", "scale", "transform", "vrr", "mirror",
            "bitdepth", "cm", "disabled")
    return [{key: mon[key] for key in keep if key in mon} for mon in monitors]


def _valid_profile_name(name: str) -> bool:
    return bool(name) and len(name) <= 40 and "/" not in name and name.strip() == name


def _reload() -> tuple[bool, str]:
    """Reload the config; textual hyprctl errors count as failures."""
    return base.hypr_reload()


def _write_layout(monitors: list[dict], message: str) -> dict:
    if not isinstance(monitors, list) or not monitors:
        return base.fail("No monitor layout to save")
    if not any(not mon.get("disabled") for mon in monitors):
        return base.fail("At least one monitor must stay enabled")
    target = paths.monitors_file()
    if target is None:
        return base.fail("No Hyprland Lua config found (monitors.lua)")
    original = util.read_text(target)
    updated = _strip_block(original).rstrip() + "\n\n" + _lua_block(monitors)
    if updated == original:
        return base.ok("Nothing to change")
    util.atomic_write(target, updated)
    ok, text = _reload()
    if not ok:
        util.atomic_write(target, original)
        _reload()
        return base.fail(f"Hyprland rejected the layout: {text}")
    return base.ok(message, details=[str(target)])


def action(name: str, args: dict) -> dict:
    if name == "displays.apply":
        monitors = _live_monitors()
        target_name = str(args.get("name") or "")
        if not target_name:
            return base.fail("No monitor selected")
        found = False
        for mon in monitors:
            if mon["name"] != target_name:
                continue
            found = True
            for key in ("mode", "scale", "transform", "vrr", "mirror", "bitdepth", "cm"):
                if key in args:
                    mon[key] = args[key]
            for key in ("x", "y"):
                if key in args:
                    mon[key] = int(args[key] or 0)
            if "disabled" in args:
                mon["disabled"] = bool(args["disabled"])
        if not found:
            return base.fail(f"Monitor {target_name} is not connected")
        # A live change is only possible through the config on this Hyprland:
        # keyword requests are not supported, so apply = write + reload.
        return _write_layout(monitors, "Layout applied and saved to monitors.lua")

    if name == "displays.persist":
        monitors = args.get("monitors")
        if not isinstance(monitors, list):
            return base.fail("No monitor layout to save")
        return _write_layout(monitors, "Layout saved to monitors.lua")

    if name == "displays.clear_persistent":
        target = paths.monitors_file()
        if target is None:
            return base.fail("No Hyprland Lua config found (monitors.lua)")
        original = util.read_text(target)
        updated = _strip_block(original).rstrip() + "\n"
        if updated == original:
            return base.ok("No managed block to remove")
        util.atomic_write(target, updated)
        ok, text = _reload()
        if not ok:
            util.atomic_write(target, original)
            _reload()
            return base.fail(f"Hyprland rejected the reload: {text}")
        return base.ok("Managed monitor block removed", details=[str(target)])

    if name == "displays.profile_save":
        profile_name = str(args.get("name") or "").strip()
        if not _valid_profile_name(profile_name):
            return base.fail("Use a short name without slashes")
        monitors = args.get("monitors")
        if not isinstance(monitors, list) or not monitors:
            monitors = _live_monitors()
        if not any(not mon.get("disabled") for mon in monitors):
            return base.fail("A profile needs at least one enabled monitor")
        profiles = load_profiles()
        profiles[profile_name] = {
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "monitors": _profile_monitors(monitors),
        }
        save_profiles(profiles)
        return base.ok(f"Saved display profile {profile_name}",
                       details=[f"{len(monitors)} monitor(s)"])

    if name == "displays.profile_apply":
        profile_name = str(args.get("name") or "")
        entry = load_profiles().get(profile_name)
        if not entry:
            return base.fail(f"No display profile named {profile_name!r}")
        monitors = entry.get("monitors") or []
        if not monitors:
            return base.fail("That profile has no monitors")
        return _write_layout(monitors, f"Applied display profile {profile_name}")

    if name == "displays.profile_delete":
        profile_name = str(args.get("name") or "")
        profiles = load_profiles()
        if profile_name not in profiles:
            return base.fail(f"No display profile named {profile_name!r}")
        del profiles[profile_name]
        save_profiles(profiles)
        return base.ok(f"Deleted display profile {profile_name}")

    if name == "displays.reload":
        ok, text = _reload()
        if not ok:
            return base.fail(text or "hyprctl reload failed")
        return base.ok("Hyprland config reloaded")

    return base.fail(f"unknown action {name!r}")
