"""Atomic JSON config patches.

The bar's config (~/.config/hyprtk-bar-qt/config.json) is shared with
config-manager and the bar's own Settings page. The contract is a recursive
merge where the patch wins; writes are atomic. Nothing here knows about the
schema, so a new key is never lost.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import paths
from .util import atomic_write, read_json


def load(path: str | Path | None = None) -> dict:
    data = read_json(path or paths.BAR_CONFIG, {})
    return data if isinstance(data, dict) else {}


def deep_merge(base: dict, patch: dict) -> dict:
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def patch(updates: dict, path: str | Path | None = None) -> dict:
    """Merge *updates* into the target JSON file atomically and return it."""
    target = Path(path or paths.BAR_CONFIG)
    current = load(target)
    deep_merge(current, updates)
    atomic_write(target, json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    return current


def get(key: str, default: Any = None, path: str | Path | None = None) -> Any:
    node: Any = load(path)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(data, dict):
        return out
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, name))
        else:
            out[name] = value
    return out
