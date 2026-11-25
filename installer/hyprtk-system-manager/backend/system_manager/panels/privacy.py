"""Privacy & Security — screen lock, firewall, capture devices and permissions."""

from __future__ import annotations

import re
from pathlib import Path

from .. import form, priv, util
from . import base


def parse_ufw_status(text: str) -> dict:
    active = False
    rules: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("status:"):
            value = stripped.split(":", 1)[1].strip().lower()
            active = value == "active"
            continue
        if not stripped or stripped.startswith("To ") or stripped.startswith("--"):
            continue
        if re.match(r"^[A-Za-z][A-Za-z ()/.-]*:", stripped):
            continue  # Logging: / Default: / New profiles: …
        rules.append(stripped)
    return {"active": active, "rules": rules}


def parse_flatpak_permissions(text: str) -> list[dict]:
    """Parse ``flatpak permissions``: table, object, app, then permissions."""
    rows: list[dict] = []
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0] in ("Table", "Application"):
            continue
        rows.append({
            "table": parts[0], "object": parts[1], "app": parts[2],
            "permissions": " ".join(parts[3:]),
        })
    return rows


def parse_source_outputs(text: str) -> list[str]:
    """Applications currently capturing audio, from ``pactl list source-outputs``."""
    names: list[str] = []
    for line in (text or "").splitlines():
        match = re.search(r'application\.name\s*=\s*"([^"]+)"', line)
        if match and match.group(1) not in names:
            names.append(match.group(1))
    return names


def _firewall() -> dict:
    state = util.run(["systemctl", "is-active", "nftables"], timeout=6)
    ufw = util.run(["ufw", "status"], timeout=8) if util.which("ufw") else None
    nft = util.run(["nft", "list", "rulesets"], timeout=8) if util.which("nft") else None
    parsed = parse_ufw_status(ufw.out) if ufw is not None and ufw.ok else {"active": False,
                                                                          "rules": []}
    if ufw is not None and parsed["active"]:
        return {"state": "active", "tool": "ufw", "rules": parsed["rules"],
                "source": ufw.out}
    if state.ok and state.out.strip() == "active":
        return {"state": "active", "tool": "nftables.service",
                "rules": (nft.lines()[:12] if nft is not None else []),
                "source": nft.out if nft is not None else ""}
    if nft is not None and nft.ok and nft.out.strip():
        return {"state": "rules present", "tool": "nftables",
                "rules": nft.lines()[:12], "source": nft.out}
    if ufw is not None and "inactive" in ufw.out.lower():
        return {"state": "inactive", "tool": "ufw", "rules": [], "source": ufw.out}
    return {"state": "not detected", "tool": "—", "rules": [], "source": ""}


def _flatpak_rows() -> list[dict]:
    if util.which("flatpak") is None:
        return [form.note("Flatpak is not installed; there are no sandbox permissions "
                          "to review.", "info")]
    listed = util.run(["flatpak", "list", "--app", "--columns=application,origin"],
                      timeout=20)
    apps = [line.split()[0] for line in listed.lines() if line.split()]
    permissions = util.run(["flatpak", "permissions"], timeout=20)
    rows = parse_flatpak_permissions(permissions.out)
    out: list[dict] = []
    for app in apps[:20]:
        granted = [item["permissions"] for item in rows if item["app"] == app]
        actions = [{
            "label": "Reset permissions", "action": "privacy.flatpak_reset",
            "args": {"app": app},
            "danger": True, "confirm": app,
            "message": f"Reset every permission override for {app}? Type the "
                       "application id to confirm.",
        }]
        out.append({"title": app,
                    "subtitle": " · ".join(granted) if granted else "no overrides",
                    "badges": ["override"] if granted else [], "actions": actions})
    if not out:
        return [form.note("No Flatpak applications are installed.", "info")]
    return [form.list_row(out)]


def _capture_rows() -> list[dict]:
    rows: list[dict] = []
    if util.which("pactl"):
        sources = util.run(["pactl", "list", "source-outputs"], timeout=10)
        names = parse_source_outputs(sources.out)
        rows.append(form.info("Microphone in use by",
                              ", ".join(names) if names else "nothing", mono=True))
    else:
        rows.append(form.info("Microphone in use by", "pactl not installed"))
    cameras = sorted(Path("/dev").glob("video*"))
    if cameras:
        rows.append(form.info("Camera devices", ", ".join(str(item) for item in cameras),
                              mono=True))
    else:
        rows.append(form.info("Camera devices", "none"))
    rows.append(form.note("This desktop has no per-application camera or location "
                          "permission store; Flatpak apps carry their own sandbox "
                          "permissions below.", "info"))
    return rows


def probe() -> dict:
    hypr = Path.home() / ".config" / "hypr"
    lock_conf = hypr / "hyprlock.conf"
    lock_script = hypr / "scripts" / "lock.sh"
    idle_conf = hypr / "hypridle.conf"
    firewall = _firewall()
    sessions = util.run(["loginctl", "list-sessions", "--no-legend"], timeout=8)

    firewall_rows = [
        form.info("State", firewall["state"],
                  tone="ok" if firewall["state"] == "active" else "warn"),
        form.info("Tool", firewall["tool"]),
    ]
    if firewall["rules"]:
        firewall_rows.append(form.kv([
            {"label": rule, "value": ""} for rule in firewall["rules"][:12]
        ]))
    if util.which("ufw"):
        firewall_rows.append(form.action(
            "Disable the firewall" if firewall["state"] == "active" else "Enable the firewall",
            "privacy.firewall_toggle",
            danger=firewall["state"] == "active",
            confirm="disable" if firewall["state"] == "active" else "",
            message="Traffic is allowed in and out while the firewall is off."))
    elif util.which("systemctl"):
        firewall_rows.append(form.action("Start nftables", "privacy.nftables_start"))
    else:
        firewall_rows.append(form.note("Neither ufw nor systemd is available; install "
                                       "a firewall to manage it from here.", "warn"))
    firewall_rows.append(form.action("Open firewall status in a terminal",
                                     "privacy.firewall_terminal"))

    return base.make_page("privacy", [
        form.section("Screen lock", [
            form.info("Lock screen", "hyprlock" if util.which("hyprlock") else "not installed"),
            form.info("Configuration", str(lock_conf) if lock_conf.is_file() else "missing",
                      mono=True),
            form.info("Lock script", str(lock_script) if lock_script.is_file() else "missing",
                      mono=True),
            form.action("Lock the screen now", "privacy.lock", variant="primary"),
        ]),
        form.section("Firewall", firewall_rows),
        form.section("Capture devices", _capture_rows()),
        form.section("Application permissions", _flatpak_rows()),
        form.section("Sessions", [
            form.info("Active sessions", len(sessions.lines())),
            form.kv([{"label": line, "value": ""} for line in sessions.lines()[:10]]),
        ]),
        form.section("Idle", [
            form.info("hypridle", "configured" if idle_conf.is_file() else "missing", mono=True),
            form.info("hypridle running", "yes" if util.run(["pgrep", "-x", "hypridle"],
                                                            timeout=4).ok else "no"),
        ]),
    ], status="full" if util.which("ufw") or util.which("flatpak") else "partial")


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
    if name == "privacy.firewall_toggle":
        if util.which("ufw") is None:
            return base.fail("ufw is not installed")
        status = util.run(["ufw", "status"], timeout=8)
        active = parse_ufw_status(status.out)["active"]
        verb = "disable" if active else "--force enable"
        argv = ["ufw", verb] if active else ["ufw", "--force", "enable"]
        result = priv.run_priv(argv, timeout=60, action="privacy")
        if not result.ok:
            return base.denied(result.text.strip() or "ufw failed",
                               priv.command_for(argv, "privacy"))
        return base.ok("Firewall disabled" if active else "Firewall enabled")
    if name == "privacy.nftables_start":
        result = priv.run_priv(["systemctl", "enable", "--now", "nftables"], timeout=90,
                               action="privacy")
        if not result.ok:
            return base.denied(result.text.strip() or "systemctl failed",
                               priv.command_for(["systemctl", "enable", "--now", "nftables"], "privacy"))
        return base.ok("nftables started and enabled")
    if name == "privacy.flatpak_reset":
        app = str(args.get("app") or "")
        if not app or "/" in app or " " in app:
            return base.fail("Invalid application id")
        if util.which("flatpak") is None:
            return base.fail("Flatpak is not installed")
        result = util.run(["flatpak", "permission-reset", app], timeout=60)
        if not result.ok:
            return base.fail(result.text.strip() or "flatpak failed")
        return base.ok(f"Permissions reset for {app}")
    if name == "privacy.firewall_terminal":
        command = "sudo ufw status verbose" if util.which("ufw") else "sudo nft list ruleset"
        terminal = "hyprtk-term" if util.which("hyprtk-term") else "alacritty"
        if util.which(terminal) and util.spawn([terminal, "-e", "sh", "-c",
                                                command + "; read -r"]):
            return base.ok("Opened firewall status")
        return base.fail("No terminal available", details=[command])
    return base.fail(f"unknown action {name!r}")
