"""Printers — CUPS queues (read only until the add-queue flow lands)."""

from __future__ import annotations

from .. import form, util
from . import base


def parse_lpstat(text: str) -> dict:
    queues: list[dict] = []
    default = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("printer "):
            parts = line.split()
            queues.append({"name": parts[1], "state": " ".join(parts[2:])})
        elif line.startswith("system default destination:"):
            default = line.split(":", 1)[1].strip()
    return {"queues": queues, "default": default}


def probe() -> dict:
    if util.which("lpstat") is None:
        return base.make_page("printers", [
            form.section("Unavailable", [
                base.missing_note("lpstat", "CUPS"),
                form.note("Install cups and cups-pdf to manage printers here.", "info"),
            ]),
        ])

    result = util.run(["lpstat", "-p", "-d"], timeout=10)
    parsed = parse_lpstat(result.out)
    items = [
        {"title": queue["name"], "subtitle": queue["state"],
         "badges": ["default"] if queue["name"] == parsed["default"] else [], "actions": []}
        for queue in parsed["queues"]
    ]

    return base.make_page("printers", [
        form.section("Queues", [
            form.list_row(items) if items else form.note("No printers configured.", "info"),
        ]),
        form.section("Service", [
            form.info("CUPS", "enabled" if util.run(["systemctl", "is-enabled", "cups"], timeout=6).ok else "not enabled"),
            form.info("Default printer", parsed["default"] or "none"),
            form.note("Adding and removing queues arrives in the next milestone; "
                      "use the CUPS web interface at http://localhost:631 meanwhile.", "info"),
        ]),
    ], status="read")
