"""Privacy & Security — screen lock, firewall and session summary."""

from __future__ import annotations

from pathlib import Path

from .. import form, util
from . import base


def _firewall() -> dict:
    systemd = util.run(["systemctl", "is-active", "nftables"], timeout=6)
    ufw = util.run(["ufw", "status"], timeout=8) if util.which("ufw") else None
    nft = util.run(["nft", "list", "rulesets"], timeout=8) if util.which("nft") else None
    if ufw is not None and ufw.ok and "Status: active" in ufw.out:
        return {"state": "active", "tool": "ufw"}
    if systemd.ok and systemd.out.strip() == "active":
        return {"state": "active", "tool": "nftables.service"}
    if nft is not None and nft.ok and nft.out.strip():
        return {"state": "rules present", "tool": "nftables"}
    if ufw is not None and "inactive" in ufw.out.lower():
        return {"state": "inactive", "tool": "ufw"}
    return {"state": "not detected", "tool": "—"}


def probe() -> dict:
    hypr = Path.home() / ".config" / "hypr"
    lock_conf = hypr / "hyprlock.conf"
    lock_script = hypr / "scripts" / "lock.sh"
    idle_conf = hypr / "hypridle.conf"
    firewall = _firewall()
    sessions = util.run(["loginctl", "list-sessions", "--no-legend"], timeout=8)

    return base.make_page("privacy", [
        form.section("Screen lock", [
            form.info("Lock screen", "hyprlock" if util.which("hyprlock") else "not installed"),
            form.info("Configuration", str(lock_conf) if lock_conf.is_file() else "missing", mono=True),
            form.info("Lock script", str(lock_script) if lock_script.is_file() else "missing", mono=True),
            form.action("Lock the screen now", "privacy.lock", variant="primary"),
        ]),
        form.section("Firewall", [
            form.info("State", firewall["state"], tone="warn" if firewall["state"] != "active" else "ok"),
            form.info("Tool", firewall["tool"]),
            form.note("Firewall rules are not edited here: a wrong rule locks you out of "
                      "your own machine more easily than any other setting.", "info"),
            form.action("Open firewall status in a terminal", "privacy.firewall_terminal"),
        ]),
        form.section("Sessions", [
            form.info("Active sessions", len(sessions.lines())),
            form.kv([{"label": line, "value": ""} for line in sessions.lines()[:10]]),
        ]),
        form.section("Idle", [
            form.info("hypridle", "configured" if idle_conf.is_file() else "missing", mono=True),
            form.info("hypridle running", "yes" if util.run(["pgrep", "-x", "hypridle"], timeout=4).ok else "no"),
        ]),
        form.section("Permissions", [
            form.note("Per-application camera/microphone/location permissions are not "
                      "tracked by this desktop stack yet.", "warn"),
        ]),
    ], status="partial")


def action(name: str, args: dict) -> dict:
    if name == "privacy.lock":
        script = Path.home() / ".config" / "hypr" / "scripts" / "lock.sh"
        if util.which("hyprlock"):
            result = util.run(["hyprlock"], timeout=8)
        elif script.is_file():
            result = util.run(["bash", str(script)], timeout=8)
        else:
            return base.fail("No lock screen available")
        if not result.ok:
            return base.fail(result.text.strip() or "lock failed")
        return base.ok("Screen locked")
    if name == "privacy.firewall_terminal":
        command = "sudo ufw status verbose" if util.which("ufw") else "sudo nft list ruleset"
        if util.which("hyprtk-term"):
            util.run(["hyprtk-term", "-e", "sh", "-c", command + "; read -r"], timeout=8)
        else:
            return base.fail("No terminal available", details=[command])
        return base.ok("Opened firewall status")
    return base.fail(f"unknown action {name!r}")
