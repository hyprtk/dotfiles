"""Default Applications — MIME associations through xdg-mime."""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import form, util
from . import base

CATEGORIES = [
    ("Web browser", "x-scheme-handler/http"),
    ("Email", "x-scheme-handler/mailto"),
    ("File manager", "inode/directory"),
    ("Text editor", "text/plain"),
    ("Image viewer", "image/png"),
    ("Video player", "video/mp4"),
    ("Music player", "audio/mpeg"),
    ("PDF viewer", "application/pdf"),
    ("Archive manager", "application/zip"),
]


def registered(mime: str) -> list[str]:
    result = util.run(["gio", "mime", mime], timeout=8)
    apps: list[str] = []
    for line in result.lines():
        if line.startswith("Default application"):
            continue
        if line.strip().startswith("Registered applications"):
            continue
        candidate = line.strip()
        if candidate.endswith(".desktop"):
            apps.append(candidate)
    return apps


def _label(desktop_id: str) -> str:
    for root in (Path.home() / ".local" / "share" / "applications",
                 Path("/usr/share/applications"),
                 Path("/usr/local/share/applications")):
        path = root / desktop_id
        if path.is_file():
            data = util.parse_desktop_file(path)
            name = data.get("Name")
            if name:
                return name
    return desktop_id.removesuffix(".desktop")


def probe() -> dict:
    rows = []
    for label, mime in CATEGORIES:
        current = (util.run(["xdg-mime", "query", "default", mime], timeout=8).out or "").strip()
        choices = registered(mime)
        if current and current not in choices:
            choices.insert(0, current)
        rows.append(form.choice(
            mime, label, current,
            [{"value": app, "label": _label(app)} for app in choices] or [current],
            help=mime,
        ))

    terminal = "not configured"
    if shutil.which("hyprtk-term"):
        terminal = "hyprtk-term (suite default)"

    return base.make_page("defaults", [
        form.section("Associations", rows),
        form.section("Terminal", [
            form.info("Terminal emulator", terminal),
            form.note("xdg-settings has no default-terminal target on Arch or Debian; the "
                      "suite uses $TERMINAL plus the keybinding, as before.", "info"),
        ]),
        form.section("Applied to", [
            form.info("Command", "xdg-mime default <app> <mime>", mono=True),
            form.info("Desktop entries", "~/.local/share/applications", mono=True),
        ]),
    ], status="partial")


def apply(changes: dict) -> dict:
    details: list[str] = []
    for mime, desktop in (changes or {}).items():
        if mime not in {m for _, m in CATEGORIES}:
            continue
        if not desktop:
            continue
        result = util.run(["xdg-mime", "default", str(desktop), mime], timeout=10)
        if not result.ok:
            return base.fail(f"Could not set {mime}: {result.text.strip() or result.code}")
        details.append(f"xdg-mime default {desktop} {mime}")
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Default applications updated", details=details)
