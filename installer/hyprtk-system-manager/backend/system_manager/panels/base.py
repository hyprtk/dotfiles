"""Shared helpers for panel modules."""

from __future__ import annotations

from typing import Any, Sequence

from .. import catalog, form, util


def meta(panel_id: str) -> dict:
    return catalog.PANEL_INDEX[panel_id]


def make_page(
    panel_id: str,
    sections: Sequence[dict],
    *,
    status: str | None = None,
    hero: dict | None = None,
) -> dict:
    entry = meta(panel_id)
    return form.page(
        id=entry["id"],
        title=entry["title"],
        group=entry["group"],
        icon=entry["icon"],
        description=entry["description"],
        status=status or entry["status"],
        keywords=entry["keywords"],
        sections=list(sections),
        hero=hero,
    )


def ok(message: str, **extra: Any) -> dict:
    return {"ok": True, "message": message, "refresh": True, **extra}


def fail(message: str, **extra: Any) -> dict:
    return {"ok": False, "message": message, "refresh": False, **extra}


def denied(message: str, command: str) -> dict:
    return {
        "ok": False,
        "message": message,
        "refresh": False,
        "requires": "root",
        "details": [command],
        "hint": "Authentication was cancelled or is unavailable.",
    }


def missing_note(binary: str, what: str) -> dict:
    return form.note(f"{what} is not installed ({binary} not found).", "warn")


def contains(value: Any, choices: Sequence[str], default: str) -> str:
    text = "" if value is None else str(value)
    return text if text in choices else default


def first_line(result: util.RunResult, fallback: str = "") -> str:
    lines = result.lines()
    return lines[0] if lines else fallback
