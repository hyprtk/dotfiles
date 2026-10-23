"""Live Hyprland monitor list for output/mode pickers.

Mirrors how nwg-displays builds its mode list: ask the compositor for every
connected output with `hyprctl -j monitors all`, then use each monitor's
`availableModes` entries ("WxH@RHz"). No config parsing and no nwg-displays
runtime dependency.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def _mode(value: str) -> dict[str, Any] | None:
    raw = str(value).strip()
    if raw.endswith("Hz"):
        raw = raw[:-2]
    try:
        size, refresh = raw.split("@", 1)
        width, height = size.lower().split("x", 1)
        return {
            "value": raw,
            "label": f"{int(width)}x{int(height)} @ {float(refresh):.2f} Hz",
            "width": int(width),
            "height": int(height),
            "refresh": float(refresh),
        }
    except (ValueError, TypeError):
        return None


def parse(all_payload: Any, active_payload: Any = None) -> list[dict[str, Any]]:
    """Normalize `hyprctl monitors all` / `hyprctl monitors` JSON."""
    all_monitors = all_payload if isinstance(all_payload, list) else []
    active_names = {
        str(item.get("name"))
        for item in (active_payload or [])
        if isinstance(item, dict)
    }

    monitors: list[dict[str, Any]] = []
    for mon in all_monitors:
        if not isinstance(mon, dict):
            continue
        name = str(mon.get("name") or "")
        if not name:
            continue

        modes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for entry in mon.get("availableModes") or []:
            mode = _mode(str(entry))
            if mode is None or mode["value"] in seen:
                continue
            seen.add(mode["value"])
            modes.append(mode)

        width = _int(mon.get("width"))
        height = _int(mon.get("height"))
        refresh = _float(mon.get("refreshRate"))
        current = f"{width}x{height}@{refresh:.2f}" if width and height and refresh else ""
        if current and current not in seen:
            modes.insert(0, {
                "value": current,
                "label": f"{width}x{height} @ {refresh:.2f} Hz",
                "width": width, "height": height, "refresh": refresh,
            })

        description = " ".join(
            str(part) for part in (mon.get("make"), mon.get("model"), mon.get("serial"))
            if part
        ) or str(mon.get("description") or "")

        monitors.append({
            "name": name,
            "description": description,
            "make": str(mon.get("make") or ""),
            "model": str(mon.get("model") or ""),
            "serial": str(mon.get("serial") or ""),
            "active": name in active_names if active_payload is not None else not bool(mon.get("disabled")),
            "disabled": bool(mon.get("disabled")),
            "x": _int(mon.get("x")),
            "y": _int(mon.get("y")),
            "width": width,
            "height": height,
            "scale": _float(mon.get("scale")) or 1.0,
            "transform": _int(mon.get("transform")),
            "refreshRate": refresh,
            "currentMode": current,
            "modes": modes,
        })
    return monitors


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _hyprctl(*args: str) -> Any:
    proc = subprocess.run(
        ["hyprctl", "-j", *args], capture_output=True, text=True, timeout=10
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "hyprctl failed").strip())
    return json.loads(proc.stdout or "[]")


def list_monitors() -> dict[str, Any]:
    if shutil.which("hyprctl") is None:
        return {"monitors": [], "error": "hyprctl not found"}
    try:
        all_payload = _hyprctl("monitors", "all")
        try:
            active_payload = _hyprctl("monitors")
        except (RuntimeError, json.JSONDecodeError):
            active_payload = None
    except (OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"monitors": [], "error": str(exc)}
    return {"monitors": parse(all_payload, active_payload)}
