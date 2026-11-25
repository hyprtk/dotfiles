"""Profiles — capture the editable file settings and replay them per host.

A profile is a snapshot of every panel value that is stored in a file (the same
set a dry-run preview can show). Saving one records it under the current
hostname; applying it feeds the values back through each panel's own ``apply``,
so every write keeps its validation, snapshot and reload behaviour.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .. import catalog, form, paths, util
from . import base

SCALAR_ROWS = {"toggle", "choice", "text", "number", "slider", "color", "path"}
SKIP_KEYS = ("fstab_", "profile_name")

# Saving a profile is a JSON file edit, so a dry run can show it.
PREVIEW = "files"


def profiles_file() -> Path:
    return paths.CONFIG_ROOT / "profiles.json"


def load() -> dict:
    data = util.read_json(profiles_file(), {})
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        return {"version": 1, "profiles": {}}
    return data


def save(profiles: dict) -> None:
    target = profiles_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    util.write_json(target, profiles)


def collect() -> dict[str, dict]:
    """Every editable scalar value from panels whose apply is a file edit."""
    changes: dict[str, dict] = {}
    for panel in catalog.PANELS:
        try:
            module = catalog.module_for(panel["id"])
        except Exception:  # noqa: BLE001 - a broken panel is simply skipped
            continue
        if getattr(module, "PREVIEW", "") != "files" or not hasattr(module, "apply"):
            continue
        try:
            model = module.probe()
        except Exception:  # noqa: BLE001
            continue
        values: dict = {}
        for section in model.get("sections") or []:
            for row in section.get("rows") or []:
                key = row.get("key")
                if row.get("type") not in SCALAR_ROWS or not key:
                    continue
                if str(key).startswith(SKIP_KEYS):
                    continue
                values[str(key)] = row.get("value")
        if values:
            changes[panel["id"]] = values
    return changes


def apply_profile(name: str) -> dict:
    data = load()
    entry = data["profiles"].get(name)
    if not entry:
        return base.fail(f"No profile named {name!r}")
    messages: list[str] = []
    errors: list[str] = []
    for panel_id, values in (entry.get("changes") or {}).items():
        try:
            module = catalog.module_for(panel_id)
        except KeyError:
            errors.append(f"{panel_id}: that panel no longer exists")
            continue
        apply = getattr(module, "apply", None)
        if apply is None:
            errors.append(f"{panel_id}: read-only")
            continue
        try:
            result = apply(dict(values))
        except Exception as exc:  # noqa: BLE001 - report, keep going
            errors.append(f"{panel_id}: {type(exc).__name__}: {exc}")
            continue
        if isinstance(result, dict) and not result.get("ok", True):
            errors.append(f"{panel_id}: {result.get('message') or 'failed'}")
        else:
            messages.append(panel_id)
    if errors and not messages:
        return base.fail("The profile could not be applied", details=errors)
    details = [f"applied {panel}" for panel in messages] + errors
    return base.ok(f"Applied {name}", details=details)


def probe() -> dict:
    data = load()
    items = []
    for name, entry in sorted(data["profiles"].items()):
        changes = entry.get("changes") or {}
        count = sum(len(values) for values in changes.values())
        items.append({
            "title": name,
            "subtitle": f"{entry.get('host') or 'unknown host'} · {count} values"
                        f" · {entry.get('created') or ''}",
            "badges": ["this host"] if entry.get("host") == util.hostname() else [],
            "actions": [
                {"label": "Apply", "action": "profiles.apply", "args": {"name": name}},
                {"label": "Delete", "action": "profiles.delete", "args": {"name": name},
                 "danger": True, "confirm": name,
                 "message": f"Delete the profile {name!r}? Files on disk are not "
                            "changed by deleting it."},
            ],
        })
    return base.make_page("profiles", [
        form.section("Save this host", [
            form.text("profile_name", "Profile name", "",
                      help="Captures every settings value that is stored in a file "
                           "and names it after this machine."),
            form.note("Applying a profile replays the values through each panel, so "
                      "validation, snapshots and reloads still happen.", "info"),
        ]),
        form.section("Profiles", [
            form.list_row(items) if items else
            form.note("No profiles yet. Save one above, then apply it on another "
                      "machine with the same suite.", "info"),
        ]),
    ])


def apply(changes: dict) -> dict:
    name = str(changes.get("profile_name") or "").strip()
    if not name:
        return base.fail("Give the profile a name")
    if len(name) > 60 or "/" in name:
        return base.fail("Use a short name without slashes")
    data = load()
    captured = collect()
    if not captured:
        return base.fail("Nothing to capture: no panel reported editable file settings")
    data["profiles"][name] = {
        "host": util.hostname(),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "changes": captured,
    }
    save(data)
    return base.ok(f"Saved profile {name}", details=[
        f"{panel}: {len(values)} values" for panel, values in captured.items()])


def action(name: str, args: dict) -> dict:
    if name == "profiles.apply":
        return apply_profile(str(args.get("name") or ""))
    if name == "profiles.delete":
        profile = str(args.get("name") or "")
        data = load()
        if profile not in data["profiles"]:
            return base.fail(f"No profile named {profile!r}")
        del data["profiles"][profile]
        save(data)
        return base.ok(f"Deleted profile {profile}")
    return base.fail(f"unknown action {name!r}")
