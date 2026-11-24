"""Form-model builders and validation.

A panel returns a page: metadata plus sections of typed rows. The QML side has
one renderer (`FormPage.qml`) that understands these types, so a new panel is a
Python module plus a catalog entry, never a new QML page.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

ROW_TYPES = {
    "info", "toggle", "choice", "text", "number", "slider", "color",
    "path", "action", "list", "kv", "note",
}

STATUS_LABELS = {
    "full": "functional",
    "live": "live only",
    "partial": "partial",
    "read": "read only",
    "link": "external",
    "planned": "planned",
}


def _choices(value: Iterable[Any] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in value or []:
        if isinstance(item, dict):
            entry = {"value": str(item.get("value", "")), "label": str(item.get("label", item.get("value", "")))}
        else:
            entry = {"value": str(item), "label": str(item)}
        out.append(entry)
    return out


def info(label: str, value: Any, **extra: Any) -> dict:
    return {"type": "info", "label": label, "value": "" if value is None else str(value), **extra}


def toggle(key: str, label: str, value: bool, **extra: Any) -> dict:
    return {"type": "toggle", "key": key, "label": label, "value": bool(value), **extra}


def choice(key: str, label: str, value: Any, choices: Iterable[Any], **extra: Any) -> dict:
    return {
        "type": "choice", "key": key, "label": label,
        "value": "" if value is None else str(value),
        "choices": _choices(choices), **extra,
    }


def text(key: str, label: str, value: Any = "", **extra: Any) -> dict:
    return {"type": "text", "key": key, "label": label, "value": "" if value is None else str(value), **extra}


def number(
    key: str, label: str, value: Any, *, minimum: float | None = None,
    maximum: float | None = None, step: float = 1, **extra: Any,
) -> dict:
    row = {"type": "number", "key": key, "label": label, "value": value, "step": step, **extra}
    if minimum is not None:
        row["min"] = minimum
    if maximum is not None:
        row["max"] = maximum
    return row


def slider(key: str, label: str, value: Any, *, minimum: float, maximum: float, step: float = 1, **extra: Any) -> dict:
    row = number(key, label, value, minimum=minimum, maximum=maximum, step=step, **extra)
    row["type"] = "slider"
    return row


def color(key: str, label: str, value: Any, **extra: Any) -> dict:
    return {"type": "color", "key": key, "label": label, "value": "" if value is None else str(value), **extra}


def path(key: str, label: str, value: Any = "", *, mode: str = "file", **extra: Any) -> dict:
    return {"type": "path", "key": key, "label": label, "value": "" if value is None else str(value), "mode": mode, **extra}


def action(label: str, name: str, *, args: dict | None = None, variant: str = "default", danger: bool = False, **extra: Any) -> dict:
    return {
        "type": "action", "label": label, "action": name,
        "args": args or {}, "variant": variant, "danger": danger, **extra,
    }


def note(text_value: str, tone: str = "info", **extra: Any) -> dict:
    return {"type": "note", "text": text_value, "tone": tone, **extra}


def kv(items: Sequence[dict], **extra: Any) -> dict:
    return {"type": "kv", "items": [dict(item) for item in items], **extra}


def list_row(items: Sequence[dict], *, label: str = "", **extra: Any) -> dict:
    return {"type": "list", "label": label, "items": [dict(item) for item in items], **extra}


def section(title: str, rows: Sequence[dict], description: str | None = None) -> dict:
    return {"title": title, "description": description, "rows": [dict(row) for row in rows]}


def page(
    *,
    id: str,
    title: str,
    group: str,
    icon: str,
    description: str = "",
    status: str = "read",
    keywords: Sequence[str] = (),
    sections: Sequence[dict] = (),
    hero: dict | None = None,
) -> dict:
    return {
        "id": id,
        "title": title,
        "group": group,
        "icon": icon,
        "description": description,
        "status": status,
        "statusLabel": STATUS_LABELS.get(status, status),
        "keywords": list(keywords),
        "sections": [dict(item) for item in sections],
        "hero": hero or {},
    }


def unavailable_page(meta: dict, error: str, *, status: str = "read") -> dict:
    """A valid page explaining why a panel could not be probed."""
    return page(
        id=meta["id"], title=meta["title"], group=meta["group"], icon=meta["icon"],
        description=meta.get("description", ""), status=status,
        keywords=meta.get("keywords", []),
        sections=[section("Unavailable", [
            note(f"This panel could not read the system: {error}", "danger"),
            action("Retry", "panel.refresh"),
        ])],
    )


def validate(model: dict) -> list[str]:
    """Return a list of structural problems (empty means valid)."""
    problems: list[str] = []
    for key in ("id", "title", "group", "icon", "status"):
        if not model.get(key):
            problems.append(f"missing {key}")
    if model.get("status") not in STATUS_LABELS:
        problems.append(f"bad status {model.get('status')!r}")
    for index, sec in enumerate(model.get("sections") or []):
        if not isinstance(sec, dict) or "title" not in sec:
            problems.append(f"section {index} has no title")
            continue
        for jndex, row in enumerate(sec.get("rows") or []):
            where = f"section {index} row {jndex}"
            if not isinstance(row, dict):
                problems.append(f"{where} is not a mapping")
                continue
            kind = row.get("type")
            if kind not in ROW_TYPES:
                problems.append(f"{where} has unknown type {kind!r}")
                continue
            if kind in ("info", "note", "kv", "list", "action"):
                if kind == "info" and "label" not in row:
                    problems.append(f"{where} info row has no label")
                if kind == "action" and not row.get("action"):
                    problems.append(f"{where} action row has no action")
                if kind == "kv" and not isinstance(row.get("items"), list):
                    problems.append(f"{where} kv row has no items")
                if kind == "list" and not isinstance(row.get("items"), list):
                    problems.append(f"{where} list row has no items")
                continue
            if "key" not in row:
                problems.append(f"{where} has no key")
            if kind == "choice" and not isinstance(row.get("choices"), list):
                problems.append(f"{where} choice has no choices")
            if kind in ("number", "slider") and not isinstance(row.get("value"), (int, float)):
                problems.append(f"{where} numeric row has a non-number value")
    return problems


def coerce(value: Any, current: Any) -> Any:
    """Coerce a value coming from QML to the type the current value implies."""
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return current
    if isinstance(current, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return current
    if isinstance(current, str):
        return "" if value is None else str(value)
    return value
