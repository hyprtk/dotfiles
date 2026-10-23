"""Surgical edits to the hyprtk Hyprland Lua tree.

Every function returns an `Edit` (relpath + original + updated text). Nothing
is written here: `state.Transaction` backs up, writes atomically, verifies the
new effective model, and rolls back on failure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import lua_scan
from .lua_probe import probe


class EditError(RuntimeError):
    pass


@dataclass
class Edit:
    relpath: str
    original: str
    updated: str
    note: str = ""

    @property
    def changed(self) -> bool:
        return self.original != self.updated

    def diff(self) -> str:
        import difflib

        return "".join(
            difflib.unified_diff(
                self.original.splitlines(keepends=True),
                self.updated.splitlines(keepends=True),
                fromfile=f"a/{self.relpath}",
                tofile=f"b/{self.relpath}",
            )
        )


def lua_literal(value: Any, kind: str | None = None) -> str:
    if kind == "color":
        return json.dumps(str(value))
    if kind == "str" or kind == "enum":
        return json.dumps(str(value))
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, dict):
        body = ", ".join(f"{k} = {lua_literal(v)}" for k, v in value.items())
        return "{ " + body + " }"
    if isinstance(value, (list, tuple)):
        return "{ " + ", ".join(lua_literal(v) for v in value) + " }"
    raise EditError(f"cannot express {type(value).__name__} as a Lua literal")


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _call_at_line(text: str, calls: list[lua_scan.Call], line: int) -> lua_scan.Call | None:
    for call in calls:
        first = _line_of(text, call.start)
        last = _line_of(text, call.close_paren)
        if first <= line <= last:
            return call
    return None


def _read(root: Path, relpath: str) -> str:
    return (root / relpath).read_text(encoding="utf-8")


def _rel(root: Path, path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            return str(p.relative_to(root))
        except ValueError as exc:
            raise EditError(f"{p} is outside {root}") from exc
    return str(p)


def _kind_of(existing: str) -> str:
    s = existing.strip()
    if s.startswith(("true", "false")):
        return "bool"
    if s.startswith(('"', "'")):
        return "str"
    if s.startswith("{"):
        return "table"
    return "number"


def set_config(root: Path, key_path: str, value: Any, *, kind: str | None = None) -> Edit:
    """Set a config value in the module that owns it."""
    root = Path(root).expanduser()
    parts = key_path.split(".")
    if not parts or any(not p for p in parts):
        raise EditError(f"invalid key path: {key_path!r}")

    model = probe(root)
    src = model["sources"].get(f"config.{parts[0]}")
    if not src or not src.get("file"):
        raise EditError(f"no module sets config.{parts[0]}")

    relpath = _rel(root, src["file"])
    text = _read(root, relpath)
    calls = lua_scan.find_calls(text, ("config",))
    call = _call_at_line(text, calls, int(src["line"]))
    if call is None:
        raise EditError(f"could not find the hl.config call at {relpath}:{src['line']}")

    masked = lua_scan.mask(text)
    table = lua_scan.first_table_arg(text, call)
    if table < 0:
        raise EditError(f"hl.config at {relpath}:{src['line']} has no table argument")

    span = lua_scan.find_path(masked, table, parts)
    if span is not None:
        literal = lua_literal(value, kind or _kind_of(text[span.start:span.end]))
        updated = lua_scan.replace_span(text, span, literal)
        note = f"replaced {key_path}"
    elif len(parts) == 1:
        updated = lua_scan.insert_key(text, table, parts[0], lua_literal(value, kind))
        note = f"added {key_path}"
    else:
        parent = lua_scan.find_path(masked, table, parts[:-1])
        if parent is None:
            raise EditError(f"{'.'.join(parts[:-1])} is not a table in {relpath}")
        brace = lua_scan._skip_ws(masked, parent.start)
        if masked[brace] != "{":
            raise EditError(f"{'.'.join(parts[:-1])} is not a table in {relpath}")
        updated = lua_scan.insert_key(text, brace, parts[-1], lua_literal(value, kind))
        note = f"added {key_path}"

    return Edit(relpath, text, updated, note)


def _find_animation_call(text: str, leaf: str) -> lua_scan.Call | None:
    masked = lua_scan.mask(text)
    for call in lua_scan.find_calls(text, ("animation",)):
        table = lua_scan.first_table_arg(text, call)
        if table < 0:
            continue
        span = lua_scan.find_key(masked, table, "leaf")
        if span is None:
            continue
        token = text[span.start:span.end].strip()
        if token.strip("\"'") == leaf:
            return call
    return None


def set_animation(root: Path, leaf: str, key: str, value: Any, *,
                  kind: str | None = None, module: str | None = None) -> Edit:
    """Set one field of an hl.animation({ leaf = ... }) entry.

    `module` targets a specific file (e.g. "animations-low"); otherwise the
    effective owner from the probe is used.
    """
    root = Path(root).expanduser()
    if module:
        relpath = _rel(root, module if str(module).endswith(".lua") else f"{module}.lua")
        if not (root / relpath).is_file():
            raise EditError(f"{relpath} does not exist")
    else:
        model = probe(root)
        src = model["sources"].get(f"animation.{leaf}")
        if src and src.get("file"):
            relpath = _rel(root, src["file"])
        else:
            relpath, _ = _animations_target(root)
    text = _read(root, relpath)
    masked = lua_scan.mask(text)
    call = _find_animation_call(text, leaf)

    if call is None:
        literal = lua_literal(value, kind)
        block = (
            "hl.animation({\n"
            f'    leaf = "{leaf}",\n'
            f"    {key} = {literal},\n"
            "})\n"
        )
        updated = text.rstrip("\n") + "\n\n" + block
        return Edit(relpath, text, updated, f"added animation.{leaf}")

    table = lua_scan.first_table_arg(text, call)
    if table < 0:
        raise EditError(f"animation {leaf} has no table")
    span = lua_scan.find_key(masked, table, key)
    if span is not None:
        literal = lua_literal(value, kind or _kind_of(text[span.start:span.end]))
        updated = lua_scan.replace_span(text, span, literal)
        note = f"set animation.{leaf}.{key}"
    else:
        updated = lua_scan.insert_key(text, table, key, lua_literal(value, kind))
        note = f"added animation.{leaf}.{key}"
    return Edit(relpath, text, updated, note)


def set_curve(root: Path, name: str, spec: dict, *,
              module: str | None = None) -> Edit:
    """Create or replace a curve, canonicalising that one call."""
    root = Path(root).expanduser()
    if module:
        relpath = _rel(root, module if str(module).endswith(".lua") else f"{module}.lua")
        if not (root / relpath).is_file():
            raise EditError(f"{relpath} does not exist")
    else:
        model = probe(root)
        src = model["sources"].get(f"curve.{name}")
        if src and src.get("file"):
            relpath = _rel(root, src["file"])
        else:
            relpath, _ = _animations_target(root)

    text = _read(root, relpath)
    target = None
    name_re = re.compile(
        r"""^\s*(?:"%s"|'%s')\s*,""" % (re.escape(name), re.escape(name))
    )
    for call in lua_scan.find_calls(text, ("curve",)):
        if lua_scan.first_table_arg(text, call) >= 0:
            continue  # curve's first arg is the name, not a table
        arg = text[call.open_paren + 1:call.close_paren]
        if name_re.match(arg):
            target = call
            break

    body = _curve_body(spec)
    call_text = f'hl.curve("{name}", {body})'
    if target is not None:
        line_start = text.rfind("\n", 0, target.start) + 1
        indent = text[line_start:target.start]
        updated = text[:target.start] + call_text + text[target.end:]
        note = f"curve {name} replaced"
    else:
        indent = ""
        updated = text.rstrip("\n") + "\n" + call_text + "\n"
        note = f"curve {name} added"
    return Edit(relpath, text, updated, note.strip())


def _curve_body(spec: dict) -> str:
    ctype = spec.get("type", "bezier")
    if ctype == "spring":
        damping_key = "damping" if "damping" in spec else "dampening"
        mass = spec.get("mass", 1)
        stiffness = spec.get("stiffness", 100)
        damping = spec.get(damping_key, 10)
        return (
            '{ type = "spring", mass = %s, stiffness = %s, %s = %s }'
            % (lua_literal(mass), lua_literal(stiffness), damping_key, lua_literal(damping))
        )
    points = spec.get("points") or [[0.25, 0.1], [0.25, 1.0]]
    pts = ", ".join("{ %s, %s }" % (lua_literal(p[0]), lua_literal(p[1])) for p in points)
    return '{ type = "bezier", points = { %s } }' % pts


def _animations_target(root: Path) -> tuple[str, str]:
    """Pick the active animations-*.lua module (falls back to hyprland.lua)."""
    text = _read(root, "hyprland.lua")
    for line in text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        m = re.search(r'''require\(\s*["']([^"']*animations-[\w-]+)["']\s*\)''', line)
        if not m:
            continue
        module = m.group(1)
        if (root / f"{module}.lua").is_file():
            return f"{module}.lua", module
    return "hyprland.lua", ""


def set_animations_mode(root: Path, mode: str) -> Edit:
    """Flip the active require('animations-<mode>') line in hyprland.lua."""
    root = Path(root).expanduser()
    if mode not in ("low", "high", "custom"):
        raise EditError(f"unknown animation mode: {mode}")
    text = _read(root, "hyprland.lua")
    module = f"animations-{mode}"
    if mode != "custom" and not (root / f"{module}.lua").is_file():
        raise EditError(f"{module}.lua does not exist")
    updated = lua_scan.set_require_active(text, module)
    return Edit("hyprland.lua", text, updated, f"animations mode -> {mode}")


def set_env(root: Path, key: str, value: Any, *, module: str | None = None) -> Edit:
    """Set an hl.env("KEY", "value") entry, adding it if missing."""
    root = Path(root).expanduser()
    model = probe(root)
    src = model["sources"].get(f"env.{key}")
    if src and src.get("file"):
        relpath = _rel(root, src["file"])
    elif module:
        relpath = _target_rel(root, module)
    else:
        relpath = "environment.lua"
        if not (root / relpath).is_file():
            owners = [
                _rel(root, item["file"])
                for name, item in (model.get("sources") or {}).items()
                if name.startswith("env.") and item.get("file")
            ]
            if not owners:
                raise EditError(f"no module sets env variables; cannot add env.{key}")
            relpath = owners[0]

    text = _read(root, relpath)
    masked = lua_scan.mask(text)
    for call in lua_scan.find_calls(text, ("env",)):
        start = lua_scan._skip_ws(masked, call.open_paren + 1)
        end = lua_scan._value_end(masked, start, call.close_paren)
        token = text[start:end].strip().strip("\"'")
        if token != key:
            continue
        vstart = lua_scan._skip_ws(masked, end + 1)
        if vstart >= call.close_paren:
            raise EditError(f"hl.env({key!r}) has no value argument")
        vend = lua_scan._value_end(masked, vstart, call.close_paren)
        span = lua_scan.Span(vstart, vend)
        updated = lua_scan.replace_span(text, span, lua_literal(value, "str"))
        return Edit(relpath, text, updated, f"set env.{key}")

    updated = text.rstrip("\n") + f'\nhl.env("{key}", {lua_literal(value, "str")})\n'
    return Edit(relpath, text, updated, f"added env.{key}")


def _target_rel(root: Path, module: str) -> str:
    rel = _rel(root, module if str(module).endswith(".lua") else f"{module}.lua")
    if not (root / rel).is_file():
        raise EditError(f"{rel} does not exist")
    return rel


def _call_on_line(text: str, kinds: tuple[str, ...], line: int) -> lua_scan.Call:
    calls = lua_scan.find_calls(text, kinds)
    call = _call_at_line(text, calls, int(line))
    if call is None:
        raise EditError(f"no hl.{kinds[0]} call on line {line}")
    return call


def set_exec(root: Path, module: str, line: int, command: str) -> Edit:
    """Replace the command string of hl.exec/exec_cmd/exec_once on `line`."""
    root = Path(root).expanduser()
    rel = _target_rel(root, module)
    text = _read(root, rel)
    call = _call_on_line(text, ("exec", "exec_cmd", "exec_once"), line)
    spans = lua_scan.arg_spans(text, call)
    if not spans:
        raise EditError(f"hl.{call.kind} on line {line} has no command argument")
    updated = lua_scan.replace_span(text, spans[0], lua_literal(command, "str"))
    return Edit(rel, text, updated, f"set {call.kind} command (line {line})")


def set_bind(root: Path, module: str, line: int, keys: str, action: str) -> Edit:
    """Replace keys + dispatcher expression of hl.bind on `line`."""
    root = Path(root).expanduser()
    rel = _target_rel(root, module)
    text = _read(root, rel)
    if not str(action).strip():
        raise EditError("binding action cannot be empty")
    if line is None or int(line) <= 0:
        updated = text.rstrip("\n") + f'\nhl.bind({lua_literal(keys, "str")}, {action.strip()})\n'
        return Edit(rel, text, updated, "added binding")
    call = _call_on_line(text, ("bind",), int(line))
    spans = lua_scan.arg_spans(text, call)
    if len(spans) < 2:
        raise EditError(f"hl.bind on line {line} needs keys and a dispatcher")
    updated = lua_scan.replace_span(text, spans[1], action.strip())
    updated = lua_scan.replace_span(updated, spans[0], lua_literal(keys, "str"))
    return Edit(rel, text, updated, f"set binding {keys}")


def set_call_field(root: Path, module: str, line: int, call_kind: str,
                   key_path: str, value: Any, *, kind: str | None = None) -> Edit:
    """Set a nested key inside any `hl.<call_kind>({...})` table call."""
    root = Path(root).expanduser()
    rel = _target_rel(root, module)
    text = _read(root, rel)
    call = _call_on_line(text, (call_kind,), int(line))
    table = lua_scan.first_table_arg(text, call)
    if table < 0:
        raise EditError(f"hl.{call_kind} on line {line} has no table argument")
    masked = lua_scan.mask(text)
    parts = [p for p in str(key_path).split(".") if p]
    if not parts:
        raise EditError("empty key path")

    span = lua_scan.find_path(masked, table, parts)
    if span is not None:
        literal = lua_literal(value, kind or _kind_of(text[span.start:span.end]))
        updated = lua_scan.replace_span(text, span, literal)
        note = f"set {call_kind}.{key_path} (line {line})"
    else:
        parent_path = parts[:-1]
        if not parent_path:
            updated = lua_scan.insert_key(text, table, parts[0], lua_literal(value, kind))
        else:
            parent = lua_scan.find_path(masked, table, parent_path)
            if parent is None:
                raise EditError(f"{'.'.join(parent_path)} is not a table in {rel}:{line}")
            brace = lua_scan._skip_ws(masked, parent.start)
            if masked[brace] != "{":
                raise EditError(f"{'.'.join(parent_path)} is not a table in {rel}:{line}")
            updated = lua_scan.insert_key(text, brace, parts[-1], lua_literal(value, kind))
        note = f"added {call_kind}.{key_path} (line {line})"
    return Edit(rel, text, updated, note)


_REQUIRE_LINE = re.compile(
    r'^(?P<indent>\s*)(?P<comment>--\s*)?require\(\s*(?P<q>["\'])(?P<module>[^"\']+)(?P=q)\s*\)(?P<tail>.*)$'
)


def set_require(root: Path, line: int, module: str, active: bool) -> Edit:
    """Rename and/or enable a require() line in hyprland.lua."""
    root = Path(root).expanduser()
    rel = "hyprland.lua"
    text = _read(root, rel)
    lines = text.splitlines(keepends=True)
    idx = int(line) - 1
    if idx < 0 or idx >= len(lines):
        raise EditError(f"line {line} is outside {rel}")
    m = _REQUIRE_LINE.match(lines[idx].rstrip("\n"))
    if m is None:
        raise EditError(f"line {line} is not a require() line in {rel}")
    tail = m.group("tail") or ""
    newline = (m.group("indent") + ("" if active else "-- ")
               + f'require("{module}")' + tail + "\n")
    lines[idx] = newline
    updated = "".join(lines)
    return Edit(rel, text, updated, f"require {module} ({'on' if active else 'off'})")


def add_require(root: Path, module: str) -> Edit:
    root = Path(root).expanduser()
    rel = "hyprland.lua"
    text = _read(root, rel)
    updated = text.rstrip("\n") + f'\nrequire("{module}")\n'
    return Edit(rel, text, updated, f"added require({module})")
