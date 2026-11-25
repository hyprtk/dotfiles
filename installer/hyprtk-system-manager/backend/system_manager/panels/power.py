"""Power — power sources, profiles, battery care and idle behaviour."""

from __future__ import annotations

from pathlib import Path

from .. import form, priv, util
from . import base

PROFILE_SLOTS = ("performance", "balanced", "power-saver")


def _read(path: Path) -> str:
    return util.read_text(path).strip()


def _supplies(root: Path | None = None) -> list[dict]:
    items: list[dict] = []
    root = Path(root) if root is not None else Path("/sys/class/power_supply")
    if not root.is_dir():
        return items
    for entry in sorted(root.iterdir()):
        kind = _read(entry / "type")
        if not kind:
            continue
        items.append({
            "name": entry.name,
            "type": kind,
            "online": _read(entry / "online"),
            "capacity": _read(entry / "capacity"),
            "status": _read(entry / "status"),
            "path": entry,
        })
    return items


def _design_and_full(entry: Path) -> tuple[str, str]:
    for prefix in ("energy", "charge"):
        full = _read(entry / f"{prefix}_full")
        design = _read(entry / f"{prefix}_full_design")
        if full and design:
            return full, design
    return "", ""


def parse_powerprofiles(text: str) -> tuple[list[dict], str]:
    """Parse ``powerprofilesctl list`` into (choices, active profile)."""
    choices: list[dict] = []
    active = ""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.endswith(":") is False and ":" not in stripped:
            continue
        name = stripped.split(":", 1)[0].strip().lstrip("*").strip()
        if name not in PROFILE_SLOTS:
            continue
        chosen = stripped.startswith("*")
        if chosen:
            active = name
        if all(entry["value"] != name for entry in choices):
            choices.append({"value": name, "label": name.replace("-", " ").title()})
    if not active and choices:
        active = choices[0]["value"]
    return choices, active


def _power_profiles() -> dict:
    if util.which("powerprofilesctl") is None:
        return {"available": False, "choices": [], "active": ""}
    listed = util.run(["powerprofilesctl", "list"], timeout=8)
    choices, active = parse_powerprofiles(listed.out or listed.err)
    if not choices:
        choices = [{"value": slot, "label": slot.replace("-", " ").title()}
                   for slot in PROFILE_SLOTS]
        listed = util.run(["powerprofilesctl", "get"], timeout=8)
        active = base.first_line(listed, "balanced").strip()
    return {"available": True, "choices": choices, "active": active}


def _battery_rows(entry: dict) -> list[dict]:
    path = entry["path"]
    rows: list[dict] = []
    full, design = _design_and_full(path)
    if full and design:
        try:
            health = float(full) / float(design) * 100
            rows.append(form.info("Health", f"{health:.0f}% of design capacity"))
        except (ValueError, ZeroDivisionError):
            pass
    cycles = _read(path / "cycle_count")
    if cycles:
        rows.append(form.info("Charge cycles", cycles))
    limit = path / "charge_control_end_threshold"
    current = _read(limit)
    if current:
        rows.append(form.slider(
            f"charge_limit::{entry['name']}", "Charge limit", int(current),
            minimum=40, maximum=100, step=1,
            help="Caps the charge level to extend battery life. Writes the "
                 "kernel threshold for this battery and needs root.",
        ))
    start = path / "charge_control_start_threshold"
    if _read(start):
        rows.append(form.info("Start threshold", _read(start)))
    return rows


def _lid_state() -> str:
    states = list(Path("/proc/acpi/button/lid").glob("*/state"))
    if not states:
        return ""
    return _read(states[0])


def _lid_binding() -> str:
    root = Path.home() / ".config" / "hypr"
    if not root.is_dir():
        return ""
    for path in sorted(root.glob("*.lua")):
        for line in util.read_text(path).splitlines():
            if "switch:on:Lid Switch" in line or "switch:off:Lid Switch" in line:
                return line.strip()
    return ""


def _idle_rows() -> list[dict]:
    hypr = Path.home() / ".config" / "hypr"
    idle_conf = hypr / "hypridle.conf"
    running = util.which("pgrep") and util.run(["pgrep", "-x", "hypridle"], timeout=4).ok
    rows = [
        form.info("hypridle", "running" if running else "not running",
                  tone="ok" if running else "warn"),
        form.info("Configuration", str(idle_conf) if idle_conf.is_file() else "missing",
                  mono=True),
    ]
    if util.which("hypridle"):
        rows.append(form.action("Restart hypridle" if running else "Start hypridle",
                                "power.idle_restart"))
    else:
        rows.append(form.note("hypridle is not installed; install it to apply the "
                              "idle configuration.", "warn"))
    rows.append(form.action("Edit the idle configuration", "power.idle_edit"))
    return rows


def probe() -> dict:
    supplies = _supplies()
    source_rows: list[dict] = []
    battery_rows: list[dict] = []
    for item in supplies:
        if item["type"] == "Battery":
            source_rows.append(form.info(
                item["name"], f"{item['capacity']}% · {item['status']}", mono=True))
            battery_rows.extend(_battery_rows(item))
        else:
            source_rows.append(form.info(
                item["name"], "connected" if item["online"] == "1" else "disconnected",
                mono=True))
    if not source_rows:
        source_rows.append(form.note(
            "This machine has no battery or AC adapter reported through "
            "/sys/class/power_supply (desktop).", "info"))

    profiles = _power_profiles()
    profile_rows: list[dict] = []
    if profiles["available"]:
        profile_rows.append(form.choice("ppd_profile", "Power profile",
                                        profiles["active"], profiles["choices"],
                                        help="Platform profile through power-profiles-daemon."))
    else:
        profile_rows.append(form.note(
            "power-profiles-daemon is not installed; there is no platform profile "
            "to switch.", "info"))

    if util.which("tlp-stat"):
        mode = base.first_line(util.run(["tlp-stat", "-s"], timeout=12), "installed")
        profile_rows.append(form.info("TLP", mode))
        profile_rows.append(form.action("Show full TLP status", "power.tlp_status"))
    else:
        profile_rows.append(form.info("TLP", "not installed"))

    lid_state = _lid_state()
    lid_rows: list[dict] = []
    if lid_state:
        lid_rows.append(form.info("Lid", lid_state.split(":")[-1].strip() or lid_state))
    binding = _lid_binding()
    if binding:
        lid_rows.append(form.info("Hyprland binding", binding, mono=True))
    elif lid_state:
        lid_rows.append(form.note(
            "No lid switch binding is configured in the Hyprland Lua config. "
            "Set the lid behaviour in Hyprland settings so the compositor owns it.",
            "info"))
    lid_rows.append(form.action("Hyprland settings", "power.open_hyprland"))

    actions = [
        form.action("Suspend now", "power.suspend", variant="primary"),
        form.action("Lock the screen", "power.lock"),
    ]
    if util.which("systemctl"):
        hibernate = util.run(["systemctl", "hibernate", "--dry-run"], timeout=6)
        states = util.read_text("/sys/power/state")
        if "hibernate" in states:
            actions.append(form.action(
                "Hibernate now", "power.hibernate",
                message="Hibernate saves the session to swap and powers off. "
                        "The machine must have a usable swap device."))
        if not hibernate.ok and not states:
            actions.append(form.note("Hibernation is not available on this system.", "info"))

    return base.make_page("power", [
        form.section("Sources", source_rows),
        form.section("Battery", battery_rows or [
            form.note("No battery on this machine; charge limits and health need one.",
                      "info"),
        ]),
        form.section("Performance profile", profile_rows),
        form.section("Lid and power actions", lid_rows + actions),
        form.section("Idle behaviour", _idle_rows()),
    ], status="full" if (profiles["available"] or battery_rows) else "partial")


def _write_threshold(name: str, key: str, value) -> dict:
    entry = next((item for item in _supplies() if item["name"] == name), None)
    if entry is None:
        return base.fail(f"unknown battery {name!r}")
    target = entry["path"] / key
    if not target.exists():
        return base.fail(f"{name} does not expose {key}")
    try:
        number = int(value)
    except (TypeError, ValueError):
        return base.fail("charge limit must be a number")
    current = _read(target)
    if current == str(number):
        return base.ok("Nothing to change")
    result = priv.run_priv(["tee", str(target)], input=f"{number}\n", timeout=30,
                           action="power")
    if not result.ok:
        return base.denied(result.text.strip() or "Could not write the charge limit",
                           priv.command_for(["tee", str(target)], "power"))
    return base.ok(f"{name} charge limit set to {number}%",
                   details=[str(target)])


def apply(changes: dict) -> dict:
    for key, value in changes.items():
        if key.startswith("charge_limit::"):
            return _write_threshold(key.split("::", 1)[1],
                                    "charge_control_end_threshold", value)

    profile = changes.get("ppd_profile")
    if profile is not None:
        if util.which("powerprofilesctl") is None:
            return base.fail("power-profiles-daemon is not installed")
        wanted = str(profile)
        if wanted not in PROFILE_SLOTS:
            return base.fail(f"unknown power profile {wanted!r}")
        result = util.run(["powerprofilesctl", "set", wanted], timeout=20)
        if not result.ok:
            return base.fail(result.text.strip() or "powerprofilesctl failed")
        return base.ok(f"Power profile set to {wanted.replace('-', ' ')}")
    return base.ok("Nothing to change")


def _systemctl(verb: str, message: str) -> dict:
    if util.which("systemctl") is None:
        return base.fail("systemctl is not available")
    result = util.run(["systemctl", verb], timeout=20)
    if not result.ok:
        return base.fail(result.text.strip() or f"systemctl {verb} failed")
    return base.ok(message)


def _open_in_editor(path: Path, label: str) -> dict:
    if not path.is_file():
        return base.fail(f"{label} is missing", details=[str(path)])
    for candidate in (["hyprtk-edit", str(path)], ["xdg-open", str(path)]):
        if util.which(candidate[0]) and util.spawn(candidate):
            return base.ok(f"Opened {label}")
    return base.fail("No editor is available", details=[str(path)])


def action(name: str, args: dict) -> dict:
    if name == "power.suspend":
        return _systemctl("suspend", "Suspending")
    if name == "power.hibernate":
        return _systemctl("hibernate", "Hibernating")
    if name == "power.lock":
        script = Path.home() / ".config" / "hypr" / "scripts" / "lock.sh"
        if util.which("hyprlock"):
            util.spawn(["hyprlock"])
            return base.ok("Screen locked")
        if script.is_file() and util.spawn(["bash", str(script)]):
            return base.ok("Screen locked")
        return base.fail("No lock screen available")
    if name == "power.idle_restart":
        if util.which("hypridle") is None:
            return base.fail("hypridle is not installed")
        util.run(["pkill", "-x", "hypridle"], timeout=6)
        if not util.spawn(["hypridle"]):
            return base.fail("Could not start hypridle")
        return base.ok("hypridle restarted")
    if name == "power.idle_edit":
        return _open_in_editor(Path.home() / ".config" / "hypr" / "hypridle.conf",
                               "the idle configuration")
    if name == "power.open_hyprland":
        if util.which("hyprtk-settings") and util.spawn(["hyprtk-settings", "open", "--page", "hyprland"]):
            return base.ok("Opened Hyprland settings")
        if util.which("config-manager") and util.spawn(["config-manager", "open"]):
            return base.ok("Opened Hyprland settings")
        return base.fail("Hyprland settings are not installed")
    if name == "power.tlp_status":
        terminal = "hyprtk-term" if util.which("hyprtk-term") else "alacritty"
        if util.which(terminal) and util.spawn([terminal, "-e", "sh", "-c",
                                                "sudo tlp-stat -s; read -r"]):
            return base.ok("Opened TLP status")
        return base.fail("No terminal available", details=["sudo tlp-stat -s"])
    return base.fail(f"unknown action {name!r}")
