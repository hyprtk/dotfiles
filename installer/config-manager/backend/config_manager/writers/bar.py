"""Read/write the hyprtk-bar-qt animation keys in its config.json.

The bar's own settings are a plain JSON file. We only touch the animation
subset and always do an atomic read-modify-write so the rest of the schema is
never clobbered.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..paths import BAR_CONFIG
from ..state import atomic_write

ANIMATION_KEYS = (
    "theme.border_animation",
    "animations.mode",
    "animations.speed",
    "uiAnimations",
    "animationDuration",
)


def read(path: Path = BAR_CONFIG) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get(path: Path = BAR_CONFIG) -> dict:
    """Return the animation subset, flattened to dotted keys."""
    data = read(path)
    out: dict[str, Any] = {}
    for key in ANIMATION_KEYS:
        node: Any = data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                node = None
                break
            node = node[part]
        if node is not None:
            out[key] = node
    return out


def _set_dotted(data: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def update(updates: dict[str, Any], path: Path = BAR_CONFIG) -> dict:
    """Apply dotted-key updates atomically; return the full new document."""
    path = Path(path)
    data = read(path)
    before = json.dumps(data, sort_keys=True)
    for key, value in updates.items():
        if key not in ANIMATION_KEYS:
            raise ValueError(f"{key!r} is not a managed bar animation key")
        _set_dotted(data, key, value)
    after = json.dumps(data, sort_keys=True)
    if after != before:
        atomic_write(path, json.dumps(data, indent=2) + "\n")
    return data
