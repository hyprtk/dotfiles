"""Bar — the whole hyprtk-bar-qt configuration, edited in place.

The bar's Settings window is ten pages over one JSON file. Rather than copy the
pages, this panel renders the file itself: every scalar becomes a typed row and
the page is grouped by the top-level key it lives under. Lists of plain values
are edited as comma-separated text; lists of objects are the bar's own editors
and link there instead of guessing.
"""

from __future__ import annotations

import re
from typing import Any

from .. import form, jsonconf, paths, util
from . import base

# Apply is a JSON file edit, so a dry run can show it as a diff.
PREVIEW = "files"

LIMITS = {
    "opacity": (-1.0, 1.0, 0.01),  # -1 follows the theme
    "radius": (0, 40, 1),
    "height": (20, 96, 1),
    "fontSize": (8, 28, 1),
    "animationDuration": (0, 2000, 10),
    "gap_in": (0, 60, 1),
    "gap_out": (0, 120, 1),
    "sysmonInterval": (1, 60, 1),
    "sysmonDataPoints": (10, 600, 10),
}
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# The bar keeps the theme twice: a nested `theme` block and flat `theme*` keys
# that win at load. Writing one without the other is the bug system-manager
# shipped and fixed in 0.5.3, so a theme edit writes both.
ALIASES = {
    "theme.source": "themeSource",
    "theme.name": "themeName",
    "theme.background": "themeBackground",
    "theme.foreground": "themeForeground",
    "theme.accent": "themeAccent",
}


def _title(key: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", str(key))
    text = text.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _get(data: Any, path: str) -> Any:
    node = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _set(target: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    node = target
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def coerce(current: Any, value: Any) -> Any:
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(current, int) and not isinstance(current, bool):
        return int(round(float(value)))
    if isinstance(current, float):
        return float(value)
    if isinstance(current, list):
        idea = value if isinstance(value, list) else str(value).split(",")
        return [str(part).strip() for part in idea if str(part).strip()]
    return "" if value is None else str(value)


def _row(key: str, label: str, value: Any, *, help_text: str = "") -> dict | None:
    if isinstance(value, bool):
        return form.toggle(key, label, value, help=help_text)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        limits = LIMITS.get(key.split(".")[-1])
        if limits:
            low, high, step = limits
            if isinstance(value, float) or step < 1:
                return form.slider(key, label, value, minimum=low, maximum=high,
                                   step=step, help=help_text)
            return form.number(key, label, value, minimum=low, maximum=high,
                               step=step, help=help_text)
        return form.number(key, label, value, help=help_text)
    if isinstance(value, str):
        if COLOR_RE.match(value):
            return form.color(key, label, value, help=help_text)
        return form.text(key, label, value, mono=len(value) > 40, help=help_text)
    if isinstance(value, list) and all(not isinstance(item, (dict, list)) for item in value):
        return form.text(key, label, ", ".join(str(item) for item in value),
                         help=help_text or "Comma-separated.")
    return None


def _section(key: str, value: Any) -> dict | None:
    if isinstance(value, dict):
        rows = []
        for child_key, child in sorted(value.items()):
            if isinstance(child, dict):
                continue
            row = _row(f"{key}.{child_key}", _title(child_key), child)
            if row:
                rows.append(row)
        if rows:
            return form.section(_title(key), rows)
        return None
    row = _row(key, _title(key), value)
    if row:
        return form.section(_title(key), [row])
    if isinstance(value, list):
        return form.section(_title(key), [
            form.note(f"{len(value)} structured entries — edit these in the bar's own "
                      "Settings, where each entry has a row editor.", "info"),
            form.action("Open the bar's settings", "bar.open_settings"),
        ])
    return form.section(_title(key), [
        form.note("This key has a shape the generic editor does not edit.", "info"),
    ])


def probe() -> dict:
    if not paths.BAR_CONFIG.is_file():
        return base.make_page("bar", [
            form.section("Not configured", [
                form.note("There is no bar configuration yet. Start the bar once and "
                          "it writes ~/.config/hyprtk-bar-qt/config.json.", "warn",
                          ),
                form.action("Open the bar's settings", "bar.open_settings"),
            ]),
        ], status="read")
    config = jsonconf.load()
    sections = []
    for key in sorted(config):
        section = _section(key, config[key])
        if section:
            sections.append(section)
    sections.append(form.section("The bar's own editors", [
        form.note("Quicklinks, arc-menu items and other lists of objects keep their "
                  "row editors in the bar's Settings window.", "info"),
        form.action("Open the bar's settings", "bar.open_settings", variant="primary"),
    ]))
    return base.make_page("bar", sections, status="full")


def apply(changes: dict) -> dict:
    config = jsonconf.load()
    updates: dict = {}
    for path, value in changes.items():
        current = _get(config, path)
        if current is None:
            continue
        coerced = coerce(current, value)
        limits = LIMITS.get(path.split(".")[-1])
        if limits and isinstance(coerced, (int, float)) and not isinstance(coerced, bool):
            low, high, _step = limits
            coerced = max(low, min(high, coerced))
        _set(updates, path, coerced)
        flat = ALIASES.get(path)
        if flat and flat in config:
            updates[flat] = coerced
    if not updates:
        return base.ok("Nothing to change")
    jsonconf.patch(updates)
    return base.ok("Bar settings updated", details=[
        str(paths.BAR_CONFIG),
        "The bar re-reads config.json; a theme change applies without a restart.",
    ])


def action(name: str, args: dict) -> dict:
    if name == "bar.open_settings":
        if util.which("hyprtk-bar-qt-settings-toggle") is None:
            return base.fail("The bar's settings toggle is not installed")
        if not util.spawn(["hyprtk-bar-qt-settings-toggle"]):
            return base.fail("Could not open the bar's settings")
        return base.ok("Opened the bar's settings")
    return base.fail(f"unknown action {name!r}")
