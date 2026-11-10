"""Config and session storage (atomic JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "hyprtk-file-manager" / "config.json"


def session_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "hyprtk-file-manager" / "session.json"


def load(path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path, data: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def merge(path, values: dict) -> dict:
    data = load(path)
    data.update(values or {})
    save(path, data)
    return data
