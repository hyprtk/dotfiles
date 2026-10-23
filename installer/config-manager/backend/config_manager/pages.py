"""Sidebar sections derived from the real Lua tree.

Every `*.lua` module in the Hyprland config dir becomes a section. Options are
assigned to the module that owns them (provenance), so the sidebar mirrors the
actual file layout instead of a hard-coded page list. Animation modules are
collapsed into the single Animations page, which can target either file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import schema as schema_mod
from .lua_probe import probe

TITLES = {
    "hyprland": "Load order",
    "environment": "Environment",
    "autostart": "Autostart",
    "input": "Input",
    "monitors": "Monitors",
    "window": "Window",
    "decoration": "Decoration",
    "layouts": "Layouts",
    "misc": "Misc",
    "keybindings": "Keybindings",
    "windowrules": "Window rules",
    "nvidia": "NVIDIA",
    "default": "Default",
    "keyboard": "Keyboard",
}

DESCRIPTIONS = {
    "hyprland": "Entry file: the require() load order. hyprlock and hypridle are managed by the bar themer.",
    "environment": "Session environment variables (hl.env).",
    "autostart": "Commands run on hyprland.start (hl.on / hl.exec_cmd).",
    "input": "Keyboard, mouse and touchpad settings.",
    "monitors": "Monitor layout and modes (hl.monitor).",
    "window": "General window behaviour: gaps, borders, layout.",
    "decoration": "Rounding, opacity, blur, shadow and border colours.",
    "layouts": "Dwindle, master and bind behaviour.",
    "misc": "Miscellaneous compositor settings.",
    "keybindings": "Key bindings (hl.bind).",
    "windowrules": "Window, layer and workspace rules.",
    "nvidia": "NVIDIA environment variables.",
}

ICONS = {
    "environment": "env",
    "autostart": "boot",
    "input": "keyboard",
    "monitors": "monitor",
    "window": "window",
    "decoration": "sparkle",
    "layouts": "layout",
    "misc": "sliders",
    "keybindings": "keys",
    "windowrules": "rules",
    "nvidia": "gpu",
    "hyprland": "list",
}


def module_rel(module: str) -> str:
    rel = str(module).strip()
    if not rel:
        raise ValueError("empty module")
    return rel if rel.endswith(".lua") else f"{rel}.lua"


def module_files(root: Path) -> dict[str, Path]:
    root = Path(root).expanduser()
    return {p.stem: p for p in sorted(root.glob("*.lua"))}


def animation_files(root: Path, active: list[str]) -> list[dict[str, Any]]:
    active_stems = {Path(name).name for name in active}
    out: list[dict[str, Any]] = []
    for stem, _ in sorted(module_files(root).items()):
        if not stem.startswith("animations-"):
            continue
        mode = stem.split("-", 1)[1]
        title = {"high": "High quality", "low": "Low quality"}.get(mode, mode.title())
        out.append({
            "id": stem,
            "file": f"{stem}.lua",
            "title": title,
            "mode": mode,
            "active": stem in active_stems,
        })
    return out


def _humanise(key: str) -> str:
    words = key.replace("-", "_").split("_")
    text = " ".join(w for w in words if w)
    return text[:1].upper() + text[1:] if text else key


def _infer(path: str, value: Any, curated: dict[str, dict]) -> dict[str, Any]:
    base = dict(curated.get(path) or {})
    base["path"] = path
    base.setdefault("label", _humanise(path.split(".")[-1]))
    if "type" not in base:
        if isinstance(value, bool):
            base["type"] = "bool"
        elif isinstance(value, int):
            base.update({"type": "int", "min": -1000, "max": 10000})
        elif isinstance(value, float):
            base.update({"type": "float", "min": -1000.0, "max": 1000.0, "step": 0.01})
        else:
            base["type"] = "str"
    base["default"] = value
    return base


def _flatten(value: Any, prefix: list[str]) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        out: list[tuple[str, Any]] = []
        for key, child in value.items():
            out.extend(_flatten(child, prefix + [key]))
        return out
    if isinstance(value, (list, tuple)):
        return []
    return [(".".join(prefix), value)]


def _rel(root: Path, file: str) -> str:
    try:
        return str(Path(file).resolve().relative_to(Path(root).resolve()))
    except (OSError, ValueError):
        return ""


def _owned_config(model: dict, root: Path) -> dict[str, str]:
    """Map each top-level config key to the module that last set it."""
    owned: dict[str, str] = {}
    for key, src in (model.get("sources") or {}).items():
        if not key.startswith("config.") or not src.get("file"):
            continue
        owned[key.split(".", 1)[1]] = _rel(root, src["file"])
    return owned


def _options_for(module: str, model: dict, root: Path,
                 curated: dict[str, dict], owned: dict[str, str]) -> list[dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    for top, value in (model.get("config") or {}).items():
        if owned.get(top) != module:
            continue
        for path, leaf in _flatten(value, [top]):
            options[path] = _infer(path, leaf, curated)

    for path, opt in curated.items():
        top = path.split(".", 1)[0]
        if owned.get(top) != module or path in options:
            continue
        item = dict(opt)
        item["present"] = False
        options[path] = item

    ordered = [options[p] for p in sorted(options)]
    return ordered


def _fmt(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _fmt_arg(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key}={_fmt_arg(val)}" for key, val in value.items())
    if isinstance(value, list):
        return "[" + ", ".join(_fmt_arg(item) for item in value) + "]"
    return _fmt(value)


def _fmt_dispatch(value: Any) -> str:
    if isinstance(value, str) and value.startswith("function: "):
        return "function()"
    if isinstance(value, dict) and value.get("__dispatch"):
        name = str(value["__dispatch"]).replace("dsp.", "")
        args = value.get("args") or []
        if isinstance(args, list):
            parts = [_fmt_arg(arg) for arg in args]
            return name + ((" " + ", ".join(parts)) if parts else "")
        return name
    return _fmt(value)


def _field_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _fields(value: Any, prefix: list[str] | None = None) -> list[dict[str, Any]]:
    prefix = prefix or []
    out: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).startswith("_"):
                continue
            out.extend(_fields(child, prefix + [str(key)]))
    elif isinstance(value, (list, tuple)):
        return []
    else:
        path = ".".join(prefix)
        out.append({
            "path": path,
            "label": _humanise(prefix[-1] if prefix else path),
            "type": _field_type(value),
            "value": value,
        })
    out.sort(key=lambda field: field["path"])
    return out


def _action_source(text: str, line: int) -> str:
    from . import lua_scan

    calls = lua_scan.find_calls(text, ("bind",))
    call = None
    for item in calls:
        first = text.count("\n", 0, item.start) + 1
        last = text.count("\n", 0, item.close_paren) + 1
        if first <= line <= last:
            call = item
            break
    if call is None:
        return ""
    spans = lua_scan.arg_spans(text, call)
    if len(spans) < 2:
        return ""
    return text[spans[1].start:spans[1].end].strip()


def _items_for(module: str, model: dict, root: Path) -> list[dict[str, Any]]:
    files = module_files(root)
    module_path = files.get(Path(module).stem)
    if module_path is None:
        return []
    target = str(module_path.resolve())
    rel = module_path.name
    try:
        text = module_path.read_text(encoding="utf-8")
    except OSError:
        text = ""

    def src_file(item: dict) -> str:
        return _src_path(root, item.get("_src") or {})

    def src_line(item: dict) -> int:
        return int((item.get("_src") or {}).get("line") or 0)

    items: list[dict[str, Any]] = []

    for key, value in (model.get("env") or {}).items():
        src = (model.get("sources") or {}).get(f"env.{key}") or {}
        if _src_path(root, src) == target:
            items.append({
                "kind": "env", "key": key, "value": value,
                "file": rel, "line": int(src.get("line") or 0),
            })

    for call in model.get("exec") or []:
        if src_file(call) == target:
            items.append({
                "kind": "exec", "label": call.get("kind") or "exec_cmd",
                "command": _fmt(call.get("command")),
                "file": rel, "line": src_line(call),
            })

    for bind in model.get("binds") or []:
        if src_file(bind) == target:
            line = src_line(bind)
            items.append({
                "kind": "bind",
                "keys": _fmt(bind.get("keys")),
                "action": _action_source(text, line),
                "file": rel, "line": line,
            })

    for monitor in model.get("monitors") or []:
        if src_file(monitor) == target:
            fields = _fields({k: v for k, v in monitor.items() if k != "_src"})
            items.append({
                "kind": "monitor",
                "label": str(monitor.get("output") or "Monitor (auto)"),
                "fields": fields,
                "file": rel, "line": src_line(monitor),
            })

    for rule_kind, rules in (model.get("rules") or {}).items():
        for rule in rules:
            if src_file(rule) != target:
                continue
            fields = _fields({k: v for k, v in rule.items() if k != "_src"})
            label = rule.get("name") or (rule.get("match") or {}).get("title") \
                or (rule.get("match") or {}).get("class") or rule_kind.replace("_rule", "")
            items.append({
                "kind": "rule", "ruleKind": rule_kind,
                "label": str(label), "fields": fields,
                "file": rel, "line": src_line(rule),
            })

    return sorted(items, key=lambda item: (item.get("line") or 0))


def _require_lines(root: Path) -> list[dict[str, Any]]:
    import re

    try:
        text = (root / "hyprland.lua").read_text(encoding="utf-8")
    except OSError:
        return []
    pattern = re.compile(r'^(?P<indent>\s*)(?P<comment>--\s*)?require\(\s*["\'](?P<module>[^"\']+)["\']\s*\)')
    out: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        m = pattern.match(line)
        if m is None:
            continue
        out.append({
            "kind": "require",
            "module": m.group("module"),
            "active": m.group("comment") is None,
            "file": "hyprland.lua",
            "line": number,
        })
    return out


def _src_path(root: Path, src: dict) -> str:
    file = src.get("file") or ""
    if not file:
        return ""
    try:
        return str(Path(file).resolve())
    except OSError:
        return file


def _load_order(root: Path, model: dict) -> dict[str, Any]:
    return {
        "id": "hyprland",
        "title": TITLES["hyprland"],
        "icon": ICONS["hyprland"],
        "file": "hyprland.lua",
        "active": True,
        "description": DESCRIPTIONS["hyprland"],
        "options": [],
        "items": _require_lines(root),
    }


def build(root: Path, model: dict | None = None) -> dict[str, Any]:
    root = Path(root).expanduser()
    model = model if model is not None else probe(root)
    curated = {opt["path"]: opt for opt in schema_mod.options()}
    owned = _owned_config(model, root)
    files = module_files(root)
    requires = model.get("requires") or []

    active_stems: list[str] = []
    for name in requires:
        stem = Path(name).name
        if stem in active_stems:
            continue
        active_stems.append(stem)

    anim = animation_files(root, requires)
    anim_stems = {a["id"] for a in anim}

    pages: list[dict[str, Any]] = [{
        "id": "animations",
        "title": "Animations",
        "icon": "animation",
        "file": None,
        "active": True,
        "description": "Curves, the animation tree, and the hyprtk bar animation mirror.",
        "options": [],
        "items": [],
    }, _load_order(root, model)]

    seen = {"hyprland", "animations"}
    for stem in active_stems:
        if stem in seen or stem in anim_stems or stem not in files:
            continue
        seen.add(stem)
        rel = files[stem].name
        pages.append({
            "id": stem,
            "title": TITLES.get(stem, _humanise(stem)),
            "icon": ICONS.get(stem, "file"),
            "file": rel,
            "active": True,
            "description": DESCRIPTIONS.get(stem, f"Settings from {rel}."),
            "options": _options_for(rel, model, root, curated, owned),
            "items": _items_for(rel, model, root),
        })

    for stem in sorted(files):
        if stem in seen or stem in anim_stems:
            continue
        rel = files[stem].name
        pages.append({
            "id": stem,
            "title": TITLES.get(stem, _humanise(stem)),
            "icon": ICONS.get(stem, "file"),
            "file": rel,
            "active": False,
            "description": f"Not loaded by hyprland.lua. {DESCRIPTIONS.get(stem, '')}".strip(),
            "options": [],
            "items": [{
                "kind": "note",
                "label": rel,
                "value": "inactive — add a require() to hyprland.lua to use this file",
            }],
        })

    pages.sort(key=lambda page: str(page.get("title") or page["id"]).lower())

    return {
        "pages": pages,
        "animationFields": schema_mod.ANIMATION_FIELDS,
        "animationTree": schema_mod.ANIMATION_TREE,
        "animationFiles": anim,
        "root": str(root),
    }
