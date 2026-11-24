"""Autostart — XDG desktop entries started with the session."""

from __future__ import annotations

from pathlib import Path

from .. import form, paths, util
from . import base

SYSTEM_DIR = Path("/etc/xdg/autostart")


def entries() -> list[dict]:
    found: dict[str, dict] = {}
    for directory, system in ((SYSTEM_DIR, True), (paths.AUTOSTART_DIR, False)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.desktop")):
            data = util.parse_desktop_file(path)
            if not data:
                continue
            found[path.name] = {
                "file": path.name,
                "path": str(path),
                "name": data.get("Name") or path.stem,
                "comment": data.get("Comment", ""),
                "exec": data.get("Exec", ""),
                "hidden": data.get("Hidden", "false").lower() == "true",
                "system": system,
                "overridden": (paths.AUTOSTART_DIR / path.name).is_file(),
            }
    return list(found.values())


def _set_hidden(entry: dict, hidden: bool) -> Path:
    if entry["system"]:
        target = paths.AUTOSTART_DIR / entry["file"]
        if not target.is_file():
            source = Path(entry["path"]).read_text(encoding="utf-8", errors="replace")
            lines = [line for line in source.splitlines() if not line.startswith(("Hidden=", "X-GNOME-Autostart-enabled="))]
            target.parent.mkdir(parents=True, exist_ok=True)
            util.atomic_write(target, "\n".join(lines).rstrip() + f"\nHidden={'true' if hidden else 'false'}\n")
            return target
    target = Path(entry["path"])
    text = util.read_text(target)
    lines = [line for line in text.splitlines() if not line.startswith(("Hidden=", "X-GNOME-Autostart-enabled="))]
    lines.append(f"Hidden={'true' if hidden else 'false'}")
    util.atomic_write(target, "\n".join(lines).rstrip() + "\n")
    return target


def probe() -> dict:
    items = []
    for entry in entries():
        actions = [
            {"label": "Enable", "action": "autostart.enable", "args": {"file": entry["file"]}}
            if entry["hidden"] else
            {"label": "Disable", "action": "autostart.disable", "args": {"file": entry["file"]}},
            {"label": "Open entry", "action": "autostart.open", "args": {"file": entry["file"]}},
        ]
        badges = ["disabled"] if entry["hidden"] else []
        if entry["system"]:
            badges.append("system")
        if entry["overridden"]:
            badges.append("overridden")
        items.append({
            "title": entry["name"],
            "subtitle": entry["comment"] or entry["exec"],
            "badges": badges, "actions": actions,
        })

    return base.make_page("autostart", [
        form.section("Session programs", [
            form.list_row(items) if items else form.note("Nothing starts with your session.", "info"),
        ]),
        form.section("Folders", [
            form.info("User entries", str(paths.AUTOSTART_DIR), mono=True, copy=True),
            form.info("System entries", str(SYSTEM_DIR), mono=True, copy=True),
            form.note("Disabling a system entry writes a user override in the user folder; "
                      "the system file is never modified.", "info"),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    filename = str(args.get("file") or "")
    entry = next((item for item in entries() if item["file"] == filename), None)
    if entry is None:
        return base.fail("Unknown autostart entry")
    if name == "autostart.enable":
        target = _set_hidden(entry, False)
        return base.ok(f"Enabled {entry['name']}", details=[str(target)])
    if name == "autostart.disable":
        target = _set_hidden(entry, True)
        return base.ok(f"Disabled {entry['name']}", details=[str(target)])
    if name == "autostart.open":
        command = ["hyprtk-edit", entry["path"]] if util.which("hyprtk-edit") else ["xdg-open", entry["path"]]
        util.run(command, timeout=10)
        return base.ok("Opened the entry", details=[entry["path"]])
    return base.fail(f"unknown action {name!r}")
