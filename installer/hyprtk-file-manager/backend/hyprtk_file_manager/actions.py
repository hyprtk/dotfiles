"""User-defined actions.

One JSON file per action in ``~/.config/hyprtk-file-manager/actions/``:

    {"name": "Optimise PNGs", "command": "optipng -quiet \"$@\"",
     "scope": "files", "confirm": false}

The command is run with ``sh -c`` in the current directory, with the selected
paths passed as positional arguments and also in ``$HYPRTK_FM_PATHS``
(newline-separated) and ``$HYPRTK_FM_DIR``. Nothing is interpolated into the
command text, so a file name can never become shell syntax.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def actions_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "hyprtk-file-manager" / "actions"


def load() -> list[dict]:
    root = actions_dir()
    if not root.is_dir():
        return []
    found: list[dict] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        command = str(data.get("command") or "").strip()
        name = str(data.get("name") or path.stem).strip()
        if not command or not name:
            continue
        found.append({
            "id": path.stem,
            "name": name[:60],
            "command": command,
            "scope": str(data.get("scope") or "files"),
            "confirm": bool(data.get("confirm", False)),
            "description": str(data.get("description") or "")[:200],
        })
    return found


def find(action_id: str) -> dict | None:
    return next((item for item in load() if item["id"] == action_id), None)


def run(action_id: str, paths: list[str], directory: str = "") -> dict:
    action = find(action_id)
    if action is None:
        raise RuntimeError(f"unknown action {action_id!r}")
    items = [str(Path(item).expanduser()) for item in paths or []]
    cwd = directory or (os.path.dirname(items[0]) if items else str(Path.home()))
    env = dict(os.environ)
    env["HYPRTK_FM_PATHS"] = "\n".join(items)
    env["HYPRTK_FM_DIR"] = cwd
    try:
        process = subprocess.Popen(
            ["sh", "-c", action["command"], "hyprtk-fm-action", *items],
            cwd=cwd, env=env, start_new_session=True,
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc
    return {"id": action["id"], "pid": process.pid, "cwd": cwd, "paths": len(items)}


def example() -> dict:
    return {
        "name": "Optimise PNGs",
        "command": 'optipng -quiet "$@"',
        "scope": "files",
        "confirm": False,
        "description": "Losslessly shrink every selected PNG.",
    }
