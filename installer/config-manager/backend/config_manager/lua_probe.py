"""Execute the real Hyprland Lua config under a recording `hl` stub.

This is the read path: instead of parsing Lua, we run it exactly as Hyprland
does (same require() chain, same variables, same conditionals) and capture the
resulting hl.* calls together with their source file and line.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

PRELUDE = Path(__file__).with_name("data") / "prelude.lua"

_REQUIRE = re.compile(r'^\s*require\(\s*["\']([^"\']+)["\']\s*\)')


class ProbeError(RuntimeError):
    def __init__(self, message: str, *, raw: dict | None = None) -> None:
        super().__init__(message)
        self.raw = raw or {}


def lua_binary() -> str:
    for name in ("lua5.4", "lua", "luajit"):
        found = shutil.which(name)
        if found:
            return found
    raise ProbeError("no Lua interpreter found (need lua5.4 / lua)")


def _active_requires(root: Path) -> list[str]:
    """Modules referenced by require() outside comments, in file order."""
    try:
        text = (root / "hyprland.lua").read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        m = _REQUIRE.match(line)
        if m:
            out.append(m.group(1))
    return out


def run(root: Path, *, main: str = "hyprland.lua", timeout: float = 10.0) -> dict:
    """Run the config and return the raw JSON document from the prelude."""
    root = Path(root).expanduser()
    if not (root / main).is_file():
        raise ProbeError(f"no {main} in {root}")
    if not PRELUDE.is_file():
        raise ProbeError(f"recording prelude missing: {PRELUDE}")

    env = dict(os.environ)
    env["HYPR_CM_DIR"] = str(root)
    env["HYPR_CM_MAIN"] = main

    try:
        proc = subprocess.run(
            [lua_binary(), str(PRELUDE)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"Lua config timed out after {timeout:g}s") from exc
    except OSError as exc:
        raise ProbeError(f"cannot run Lua: {exc}") from exc

    out = (proc.stdout or "").strip()
    if not out:
        raise ProbeError(
            "Lua produced no output"
            + (f": {proc.stderr.strip()}" if proc.stderr.strip() else "")
        )
    # The JSON document is the last line; anything earlier is config noise.
    line = out.splitlines()[-1]
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"invalid probe output: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProbeError("invalid probe output: not an object")
    return raw


def _merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def normalize(raw: dict, root: Path) -> dict:
    """Turn the call log into the model the GUI and CLI consume."""
    root = Path(root).expanduser()
    model: dict[str, Any] = {
        "root": str(root),
        "main": "hyprland.lua",
        "requires": _active_requires(root),
        "config": {},
        "curves": {},
        "animations": {},
        "animation_order": [],
        "binds": [],
        "monitors": [],
        "rules": {"window_rule": [], "layer_rule": [], "workspace_rule": []},
        "gestures": [],
        "env": {},
        "exec": [],
        "unknown": [],
        "sources": {},
        "error": raw.get("error"),
    }

    for call in raw.get("calls") or []:
        if not isinstance(call, dict):
            continue
        kind = call.get("kind")
        name = call.get("name")
        value = call.get("value")
        src = {"file": call.get("file") or "", "line": int(call.get("line") or 0)}

        if kind == "config" and isinstance(value, dict):
            _merge(model["config"], value)
            for key in value:
                model["sources"][f"config.{key}"] = src
        elif kind == "curve" and isinstance(name, str):
            spec = value if isinstance(value, dict) else {}
            model["curves"][name] = spec
            model["sources"][f"curve.{name}"] = src
        elif kind == "animation" and isinstance(value, dict):
            leaf = value.get("leaf")
            if isinstance(leaf, str):
                model["animations"][leaf] = value
                if leaf not in model["animation_order"]:
                    model["animation_order"].append(leaf)
                model["sources"][f"animation.{leaf}"] = src
        elif kind == "bind" and isinstance(value, dict):
            item = dict(value)
            item["_src"] = src
            model["binds"].append(item)
        elif kind == "monitor" and isinstance(value, dict):
            item = dict(value)
            item["_src"] = src
            model["monitors"].append(item)
        elif kind in model["rules"] and isinstance(value, dict):
            item = dict(value)
            item["_src"] = src
            model["rules"][kind].append(item)
        elif kind == "gesture" and isinstance(value, dict):
            item = dict(value)
            item["_src"] = src
            model["gestures"].append(item)
        elif kind == "env" and isinstance(value, dict):
            key = value.get("key")
            if isinstance(key, str):
                model["env"][key] = value.get("value")
                model["sources"][f"env.{key}"] = src
        elif kind == "exec" and isinstance(value, dict):
            item = dict(value)
            item["kind"] = name
            item["_src"] = src
            model["exec"].append(item)
        elif kind == "other":
            model["unknown"].append(
                {"name": name, "value": value, "_src": src}
            )

    return model


def probe(root: Path, *, main: str = "hyprland.lua") -> dict:
    """Run + normalize. Raises ProbeError only if the config cannot run."""
    root = Path(root).expanduser()
    raw = run(root, main=main)
    if raw.get("error"):
        raise ProbeError(str(raw["error"]), raw=raw)
    return normalize(raw, root)


def discover(path: str | os.PathLike[str] | None = None) -> dict:
    """Probe an explicit dir, else the first known Hyprland config dir."""
    from .paths import find_hypr_dir

    root = Path(path).expanduser() if path else find_hypr_dir()
    if root is None:
        raise ProbeError("no hyprland.lua found (set HYPR_CM_DIR or --root)")
    return probe(root)
