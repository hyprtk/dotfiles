"""Tags, colour labels, notes and smart folders.

The store is one JSON file in the state directory:

    {"paths": {"/abs/file": {"tags": ["work"], "color": "#fd4fb6", "note": ""}},
     "smart": [{"name": "Photos", "query": "jpg", "mode": "name", "root": "/home"}]}

Tags are free-form strings; colour is one of the preset hex values or empty.
Nothing here touches the files' own metadata, so a tag store describes one
machine's view and can be deleted without losing data.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

COLORS = ["#fd4fb6", "#02dede", "#5fb8f5", "#f5c15f", "#7bd88f", "#c084fc"]


def store_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "hyprtk-file-manager" / "tags.json"


def load() -> dict:
    path = store_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    paths = data.get("paths")
    smart = data.get("smart")
    if not isinstance(paths, dict):
        paths = {}
    if not isinstance(smart, list):
        smart = []
    return {"paths": paths, "smart": smart}


def save(data: dict) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def clean_tags(tags) -> list[str]:
    out: list[str] = []
    for item in tags if isinstance(tags, list) else []:
        text = str(item).strip().lower()
        if text and text not in out:
            out.append(text[:40])
    return out


def set_paths(paths: list[str], tags, color: str = "", note: str | None = None) -> dict:
    data = load()
    cleaned = clean_tags(tags)
    chosen = color if color in COLORS else ""
    for raw in paths:
        path = str(Path(raw).expanduser())
        if not cleaned and not chosen and note is None:
            data["paths"].pop(path, None)
            continue
        entry = data["paths"].get(path) or {}
        entry["tags"] = cleaned
        entry["color"] = chosen
        if note is not None:
            entry["note"] = str(note)[:500]
        entry["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        data["paths"][path] = entry
    save(data)
    return {"paths": len(paths), "tags": cleaned, "color": chosen}


def for_paths(paths: list[str]) -> dict:
    data = load()
    out: dict[str, dict] = {}
    for raw in paths:
        path = str(Path(raw).expanduser())
        entry = data["paths"].get(path)
        if entry:
            out[path] = entry
    return out


def listing(directory: str) -> dict:
    """Tags for every stored path inside *directory* (one level)."""
    base = str(Path(directory).expanduser()).rstrip("/")
    data = load()
    out: dict[str, dict] = {}
    for path, entry in data["paths"].items():
        if os.path.dirname(path) == base:
            out[path] = entry
    return out


def all_tags() -> list[dict]:
    counts: dict[str, int] = {}
    for entry in load()["paths"].values():
        for tag in entry.get("tags") or []:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"name": name, "count": counts[name]} for name in sorted(counts)]


def paths_with_tag(tag: str) -> list[str]:
    wanted = str(tag or "").strip().lower()
    return [path for path, entry in load()["paths"].items()
            if wanted and wanted in (entry.get("tags") or [])]


def smart_list() -> list[dict]:
    return [item for item in load()["smart"] if isinstance(item, dict)]


def smart_save(name: str, query: str, mode: str = "name", root: str = "") -> dict:
    name = str(name or "").strip()
    if not name:
        raise ValueError("a smart folder needs a name")
    entry = {"name": name[:60], "query": str(query or ""), "mode": str(mode or "name"),
             "root": str(root or "")}
    data = load()
    data["smart"] = [item for item in data["smart"]
                     if not (isinstance(item, dict) and item.get("name") == entry["name"])]
    data["smart"].append(entry)
    save(data)
    return entry


def smart_delete(name: str) -> bool:
    data = load()
    before = len(data["smart"])
    data["smart"] = [item for item in data["smart"]
                     if not (isinstance(item, dict) and item.get("name") == name)]
    save(data)
    return len(data["smart"]) != before
