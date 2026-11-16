"""Launcher usage state: app launch counts + run-mode history.

The in-bar launcher (``surface/Launcher.qml``) keeps its own small state file,
separate from the StartMenu's ``menu`` block: rofi keeps run/ssh history only,
so run history is parity and app counts are the launcher's frecency upgrade
(disable with ``launcher.show_recents``/``disable_history``).

State file: ``~/.cache/hyprtk-bar-qt/launcher-state.json``.

Usage::

    python3 launcher.py get
    python3 launcher.py record-app <app-id>
    python3 launcher.py record-run <command> [--max 25]
    python3 launcher.py clear-apps
    python3 launcher.py clear-run
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

try:
    from .paths import QT_CACHE
except ImportError:  # run as a script (python3 launcher.py)
    from paths import QT_CACHE

STATE = QT_CACHE / "launcher-state.json"
MAX_RUN_HISTORY = 25

# XDG data roots searched for a desktop entry when Quickshell's DesktopEntry
# does not expose enough (Link/URL entries, actions). Mirrors the common
# locations Quickshell scans.
_DATA_DIRS = (
    Path.home() / ".local" / "share" / "applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
    Path("/var/lib/flatpak/exports/share/applications"),
    Path.home() / ".local" / "share" / "flatpak" / "exports" / "share" / "applications",
    Path("/var/lib/snapd/desktop/applications"),
)



def empty_state() -> dict:
    return {"apps": {}, "run": []}


def load_state(path: Path | None = None) -> dict:
    """Read the state file; a missing/corrupt file yields an empty state."""
    state = empty_state()
    try:
        data = json.loads(Path(path if path is not None else STATE).read_text())
    except (OSError, json.JSONDecodeError):
        return state
    if not isinstance(data, dict):
        return state
    apps = data.get("apps")
    if isinstance(apps, dict):
        state["apps"] = {
            str(k): int(v) for k, v in apps.items()
            if isinstance(v, (int, float)) and int(v) > 0
        }
    run = data.get("run")
    if isinstance(run, list):
        state["run"] = [str(r) for r in run if str(r).strip()]
    return state


def save_state(state: dict, path: Path | None = None) -> bool:
    """Atomically write *state*; returns False on an I/O error."""
    path = Path(path if path is not None else STATE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".launcher.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def bump_app(apps: dict, app_id: str, step: int = 1) -> dict:
    """Return *apps* with *app_id*'s counter increased (new dict, no mutation)."""
    out = dict(apps or {})
    if not app_id:
        return out
    out[str(app_id)] = max(0, int(out.get(str(app_id), 0)) + int(step))
    return out


def record_run(history: list, command: str, max_items: int = MAX_RUN_HISTORY) -> list:
    """Newest-first, deduped, capped run history."""
    cmd = str(command or "").strip()
    if not cmd:
        return list(history or [])
    out = [cmd] + [c for c in (history or []) if c != cmd]
    return out[: max(1, int(max_items))]


def forget_run(history: list, command: str) -> list:
    """History without *command* (Shift+Delete in run/drun mode)."""
    cmd = str(command or "").strip()
    return [c for c in (history or []) if c != cmd]


def forget_app(apps: dict, app_id: str) -> dict:
    """App-count map without *app_id* (Shift+Delete in drun mode)."""
    out = dict(apps or {})
    out.pop(str(app_id or ""), None)
    return out


def run_candidates(path_env: str | None = None) -> list[str]:
    """Executable names found on ``$PATH`` (rofi's run-mode list).

    Deduplicated by name, first directory wins, case-insensitively sorted.
    """
    seen: dict[str, None] = {}
    raw = os.environ.get("PATH", "") if path_env is None else path_env
    for directory in raw.split(os.pathsep):
        if not directory:
            continue
        try:
            entries = os.scandir(directory)
        except OSError:
            continue
        with entries:
            for entry in entries:
                if entry.name in seen:
                    continue
                try:
                    if entry.is_file() and os.access(entry.path, os.X_OK):
                        seen[entry.name] = None
                except OSError:
                    continue
    return sorted(seen, key=str.lower)


def entry_info(app_id: str, data_dirs: tuple[Path, ...] = _DATA_DIRS) -> dict:
    """Type/URL/Exec/actions for a desktop entry id (Link entries etc.).

    ``app_id`` is Quickshell's id (no ``.desktop`` suffix) or a file name.
    Returns ``{}`` when the entry cannot be found.
    """
    name = str(app_id or "").strip()
    if not name:
        return {}
    if not name.endswith(".desktop"):
        name += ".desktop"
    for directory in data_dirs:
        path = Path(directory) / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        info = {"id": str(app_id), "file": str(path), "type": "", "url": "",
                "exec": "", "actions": []}
        in_entry = False
        action = ""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                in_entry = line == "[Desktop Entry]"
                action = line[1:-1] if line.startswith("[Desktop Action ") else ""
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if in_entry and key in ("Type", "URL", "Exec"):
                info[key.lower()] = value
            elif action and key == "Name":
                info["actions"].append({"id": action, "name": value})
        return info
    return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="launcher usage state")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("get")
    sub.add_parser("run-list")
    rec_app = sub.add_parser("record-app")
    rec_app.add_argument("app_id")
    rec_run = sub.add_parser("record-run")
    rec_run.add_argument("command")
    rec_run.add_argument("--max", type=int, default=MAX_RUN_HISTORY)
    forget_app_p = sub.add_parser("forget-app")
    forget_app_p.add_argument("app_id")
    forget_run_p = sub.add_parser("forget-run")
    forget_run_p.add_argument("command")
    sub.add_parser("clear-apps")
    sub.add_parser("clear-run")
    info_p = sub.add_parser("entry-info")
    info_p.add_argument("app_id")
    args = ap.parse_args(argv)

    if args.action == "run-list":
        print(json.dumps(run_candidates()))
        return 0
    if args.action == "entry-info":
        print(json.dumps(entry_info(args.app_id)))
        return 0

    state = load_state()
    if args.action == "get":
        print(json.dumps(state))
        return 0
    if args.action == "record-app":
        state["apps"] = bump_app(state["apps"], args.app_id)
    elif args.action == "record-run":
        state["run"] = record_run(state["run"], args.command, args.max)
    elif args.action == "forget-app":
        state["apps"] = forget_app(state["apps"], args.app_id)
    elif args.action == "forget-run":
        state["run"] = forget_run(state["run"], args.command)
    elif args.action == "clear-apps":
        state["apps"] = {}
    elif args.action == "clear-run":
        state["run"] = []
    return 0 if save_state(state) else 1


if __name__ == "__main__":
    raise SystemExit(main())
