"""Updates — pending packages, last upgrade and the package cache."""

from __future__ import annotations

from pathlib import Path

from .. import form, util
from . import base

PACMAN_LOG = Path("/var/log/pacman.log")


def parse_checkupdates(text: str) -> list[dict]:
    """Parse ``pkg 1.2.3-1 -> 1.2.4-1`` lines from checkupdates."""
    packages: list[dict] = []
    for line in text.splitlines():
        if " -> " not in line:
            continue
        left, _, new = line.partition(" -> ")
        bits = left.rsplit(maxsplit=1)
        if len(bits) != 2:
            continue
        name, old = bits
        packages.append({"name": name.strip(), "old": old.strip(), "new": new.strip()})
    return packages


def last_upgrade() -> str:
    """Find the most recent full-system upgrade in pacman.log."""
    text = util.read_text(PACMAN_LOG)
    stamp = ""
    for line in text.splitlines()[-20000:]:
        if "starting full system upgrade" in line:
            stamp = line[1:17]
    return stamp or "unknown"


def probe() -> dict:
    packages: list[dict] = []
    error = ""
    if util.which("checkupdates") is None:
        error = "checkupdates (pacman-contrib) is not installed"
    else:
        result = util.run(["checkupdates"], timeout=90)
        # checkupdates exits 2 when there is nothing to do.
        packages = parse_checkupdates(result.out)

    rows = [
        form.info("Pending packages", len(packages)),
        form.info("Last full upgrade", last_upgrade(), mono=True),
        form.info("Package manager", "pacman" + (" + yay" if util.which("yay") else "")),
    ]

    if packages:
        listing = [{"label": f"{pkg['old']} → {pkg['new']}", "value": pkg["name"]} for pkg in packages[:80]]
        rows.append(form.note(f"{len(packages)} package(s) can be upgraded.", "info"))
    elif error:
        rows.append(form.note(error, "warn"))
    else:
        rows.append(form.note("Everything is up to date.", "ok"))

    return base.make_page("updates", [
        form.section("Status", rows),
        form.section("Pending", [
            form.kv(listing) if packages else form.note("No pending packages.", "ok"),
        ]),
        form.section("Actions", [
            form.action("Check again", "updates.refresh", variant="primary"),
            form.action("Copy upgrade command", "updates.copy_command"),
            form.action("Clean the package cache", "updates.clean_cache"),
            form.note("Upgrading is deliberately not automated here: it needs a visible "
                      "terminal and a decision about restarting services.", "info"),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    if name == "updates.refresh":
        result = util.run(["checkupdates"], timeout=120)
        packages = parse_checkupdates(result.out)
        return base.ok(f"{len(packages)} package(s) pending", details=[p["name"] for p in packages[:40]])
    if name == "updates.copy_command":
        command = "sudo pacman -Syu"
        if util.which("wl-copy") is None:
            return base.fail("wl-copy is not installed", details=[command])
        util.run(["wl-copy"], input=command + "\n", timeout=10)
        return base.ok("Upgrade command copied", details=[command])
    if name == "updates.clean_cache":
        if util.which("paccache") is None:
            return base.fail("paccache (pacman-contrib) is not installed")
        result = util.run(["paccache", "-d"], timeout=180)
        return base.ok("Package cache cleaned", details=result.out.strip().splitlines()[-5:])
    return base.fail(f"unknown action {name!r}")
