"""Keyboard Shortcuts — the hl.bind table from keybindings.lua."""

from __future__ import annotations

import re

from .. import form, paths, util
from . import base

BIND_RE = re.compile(r"^\s*hl\.bind\((.*)\)\s*$")


def split_args(text: str) -> list[str]:
    """Split a Lua argument list on top-level commas."""
    parts: list[str] = []
    depth = 0
    quote = ""
    current = ""
    for char in text:
        if quote:
            current += char
            if char == quote and not current.endswith("\\" + quote):
                quote = ""
            continue
        if char in "\"'":
            quote = char
            current += char
        elif char in "([{":
            depth += 1
            current += char
        elif char in ")]}":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def describe_keys(raw: str) -> str:
    text = raw.replace("mainMod", '"SUPER"')
    text = re.sub(r'"\s*\.\.\s*"', "", text)
    text = text.replace('"', "").strip()
    return re.sub(r"\s+", " ", text)


def described_action(raw: str) -> str:
    text = raw.strip().replace("hl.dsp.", "")
    if text.startswith("exec_cmd(") and text.endswith(")"):
        inner = text[len("exec_cmd("):-1].strip().strip('"').replace('\\"', '"').replace("\\'", "'")
        suite = re.search(r"\$HOME/\.local/bin/([\w.+-]+)", inner)
        if suite:
            inner = suite.group(1)
        elif "exec " in inner:
            tail = inner.split("exec ", 1)[1].strip().strip('"\'').split(";")[0].strip().strip('"\'')
            inner = tail or inner
        text = inner or "run a command"
    text = re.sub(r"\bfunction\s*\(\)", "function()", text)
    return text[:120]


def parse_binds(text: str) -> list[dict]:
    binds: list[dict] = []
    for line in text.splitlines():
        match = BIND_RE.match(line)
        if not match:
            continue
        args = split_args(match.group(1))
        if len(args) < 2:
            continue
        description = ""
        if len(args) > 2:
            found = re.search(r'description\s*=\s*"([^"]*)"', args[2])
            description = found.group(1) if found else ""
        binds.append({
            "keys": describe_keys(args[0]),
            "action": described_action(args[1]),
            "description": description,
        })
    return binds


def probe() -> dict:
    root = paths.hypr_dir()
    if root is None:
        return base.make_page("shortcuts", [
            form.section("Unavailable", [form.note("No Hyprland Lua configuration found.", "warn")]),
        ])
    text = util.read_text(root / "keybindings.lua")
    binds = parse_binds(text)

    items = [
        {"title": bind["keys"], "subtitle": bind["description"] or bind["action"],
         "badges": [], "actions": []}
        for bind in binds
    ]

    return base.make_page("shortcuts", [
        form.section("Bindings", [
            form.list_row(items) if items else form.note("No hl.bind entries found.", "warn"),
            form.info("Total", len(binds)),
        ]),
        form.section("Editing", [
            form.note("Bindings are Lua calls in keybindings.lua. Edit them in the Hyprland "
                      "settings app so the tree is validated before it is written.", "info"),
            form.action("Open Hyprland settings", "shortcuts.open"),
        ]),
    ], status="read")


def action(name: str, args: dict) -> dict:
    if name == "shortcuts.open":
        if util.which("config-manager") is None:
            return base.fail("config-manager is not installed")
        util.run(["config-manager", "open", "--page", "keybinds"], timeout=10)
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
