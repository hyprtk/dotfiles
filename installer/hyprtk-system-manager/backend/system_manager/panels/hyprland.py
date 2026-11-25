"""Hyprland — config-manager's pages, rendered inside System Settings.

config-manager already owns the compositor configuration: it reads the Lua tree,
renders typed pages from a schema and writes edits with validation, a backup and
a reload. Rather than duplicate any of that, this panel asks it for the schema and
the current values and renders the same pages with this app's form renderer.
Edits go back through ``config-manager set``, so the policy stays in one place.
"""

from __future__ import annotations

from typing import Any

from .. import form, util
from . import base

# Every write is performed by config-manager, not this process: no preview.
PREVIEW = ""


def available() -> bool:
    return util.which("config-manager") is not None


def _schema() -> dict:
    result = util.run(["config-manager", "schema"], timeout=25)
    data = result.json({})
    return data if isinstance(data, dict) else {}


def _dump() -> dict:
    result = util.run(["config-manager", "dump"], timeout=45)
    data = result.json({})
    return data if isinstance(data, dict) else {}


def get_value(config: Any, path: str) -> Any:
    node = config
    for part in (path or "").split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def option_row(option: dict, value: Any) -> dict | None:
    path = str(option.get("path") or "")
    label = str(option.get("label") or path.rsplit(".", 1)[-1])
    if not path:
        return None
    kind = str(option.get("type") or "str")
    choices = option.get("choices") or option.get("values") or []
    if value is None:
        value = option.get("default")
    help_text = str(option.get("help") or "")
    if kind == "bool":
        return form.toggle(path, label, bool(value), help=help_text)
    if kind in ("int", "float") and isinstance(value, (int, float)):
        low = option.get("min")
        high = option.get("max")
        if low is not None and high is not None:
            if kind == "float":
                return form.slider(path, label, float(value), minimum=float(low),
                                   maximum=float(high), step=float(option.get("step") or 0.05),
                                   help=help_text)
            return form.number(path, label, int(value), minimum=low, maximum=high,
                               help=help_text)
        return form.number(path, label, value, help=help_text)
    if choices:
        items = choices if isinstance(choices, list) else []
        return form.choice(path, label, value, items, help=help_text)
    if kind == "color":
        return form.color(path, label, value, help=help_text)
    return form.text(path, label, "" if value is None else value, mono=True,
                     help=help_text)


def probe() -> dict:
    if not available():
        return base.make_page("hyprland", [
            form.section("Hyprland settings", [
                form.note("The Hyprland settings backend (config-manager) is not "
                          "installed, so the compositor pages cannot be shown.", "warn"),
            ]),
        ], status="link")

    schema = _schema()
    model = _dump()
    pages = schema.get("pages") or []
    config = model.get("config") or {}
    if model.get("error"):
        return base.make_page("hyprland", [
            form.section("Could not read the config", [
                form.note(str(model["error"]), "danger"),
                form.action("Open Hyprland settings", "hyprland.open_app"),
            ]),
        ], status="link")

    sections = []
    for page in pages:
        rows = []
        for option in page.get("options") or []:
            row = option_row(option, get_value(config, str(option.get("path") or "")))
            if row:
                rows.append(row)
        if rows:
            sections.append(form.section(
                str(page.get("title") or page.get("id")),
                rows, str(page.get("description") or "") or None))

    sections.append(form.section("Binds, monitors and rules", [
        form.note("Key bindings, monitor layout and window rules are edited in the "
                  "Hyprland settings app; they do not map to single values.", "info"),
        form.action("Open the Hyprland settings app", "hyprland.open_app",
                    variant="primary"),
    ]))
    status = "full" if sections else "link"
    return base.make_page("hyprland", sections, status=status)


def _serialise(value: Any, kind: str) -> str:
    if kind == "bool":
        return "true" if value else "false"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _kinds(schema: dict) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for page in schema.get("pages") or []:
        for option in page.get("options") or []:
            path = str(option.get("path") or "")
            if path:
                kinds[path] = str(option.get("type") or "str")
    return kinds


def apply(changes: dict) -> dict:
    if not available():
        return base.fail("config-manager is not installed")
    if not changes:
        return base.ok("Nothing to change")
    kinds = _kinds(_schema())
    done: list[str] = []
    for path, value in changes.items():
        if path not in kinds:
            return base.fail(f"{path} is not a Hyprland option",
                             details=done or None)
        argv = ["config-manager", "set", path, _serialise(value, kinds[path]),
                "--kind", kinds[path]]
        result = util.run(argv, timeout=45)
        if not result.ok:
            return base.fail(result.text.strip() or f"config-manager could not set {path}",
                             details=done or None)
        done.append(path)
    return base.ok(f"Updated {len(done)} Hyprland setting(s)", details=done)


def action(name: str, args: dict) -> dict:
    if name == "hyprland.open_app":
        if not available():
            return base.fail("config-manager is not installed")
        if not util.spawn(["config-manager", "open"]):
            return base.fail("Could not open the Hyprland settings app")
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
