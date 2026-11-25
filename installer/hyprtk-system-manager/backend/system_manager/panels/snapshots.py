"""Snapshots — restore the files an Apply changed, and the system-file copies."""

from __future__ import annotations

from pathlib import Path

from .. import form, paths, state, util
from . import base


def _system_files() -> list[Path]:
    root = paths.CONFIG_ROOT / "system"
    if not root.is_dir():
        return []
    return sorted(root.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True)[:20]


def probe() -> dict:
    backups = state.backups()
    items = []
    for entry in backups[:30]:
        files = entry.get("files") or []
        items.append({
            "title": str(entry.get("stamp") or "?"),
            "subtitle": f"{entry.get('reason') or 'change'} · {len(files)} file(s)"
                        f" · {entry.get('started') or ''}",
            "badges": [str(entry.get("status") or "?")],
            "actions": [{
                "label": "Restore", "action": "snapshots.restore",
                "args": {"stamp": entry.get("stamp")},
                "danger": True, "confirm": str(entry.get("stamp") or ""),
                "message": "Put every file from this snapshot back as it was. "
                           "Later changes to those files are overwritten.",
            }],
        })

    system = []
    for path in _system_files():
        system.append({"title": path.name, "subtitle": util.human_bytes(
            path.stat().st_size) + " · " + path.parent.name, "actions": []})

    return base.make_page("snapshots", [
        form.section("File snapshots", [
            form.list_row(items) if items else
            form.note("No snapshots yet. Every Apply that changes a file keeps the "
                      "previous contents here first.", "info"),
        ]),
        form.section("System files", [
            form.list_row(system) if system else
            form.note("No root-owned file copies yet (/etc/fstab and similar).", "info"),
        ]),
        form.section("Backup location", [
            form.info("Folder", str(Path.home() / ".config" / "hyprtk-system-manager" /
                                    "backups"), mono=True),
            form.action("Open the folder", "snapshots.open_folder"),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    if name == "snapshots.restore":
        stamp = str(args.get("stamp") or "")
        if not stamp:
            return base.fail("No snapshot chosen")
        try:
            result = state.restore(stamp)
        except state.TransactionError as exc:
            return base.fail(str(exc))
        restored = result.get("restored") or []
        return base.ok(f"Restored {len(restored)} file(s) from {stamp}", details=restored)
    if name == "snapshots.open_folder":
        folder = Path.home() / ".config" / "hyprtk-system-manager" / "backups"
        if not folder.is_dir():
            return base.fail("There is no backup folder yet")
        command = ["hyprtk-fm", str(folder)] if util.which("hyprtk-fm") else \
            ["xdg-open", str(folder)]
        if not util.spawn(command):
            return base.fail("Could not open the folder")
        return base.ok("Opened the backup folder")
    return base.fail(f"unknown action {name!r}")
