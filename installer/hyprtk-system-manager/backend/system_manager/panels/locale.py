"""Region & Language — locale, language and keyboard layout."""

from __future__ import annotations

from .. import form, priv, util
from . import base


def parse_localectl(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip()
    return data


def probe() -> dict:
    if util.which("localectl") is None:
        return base.make_page("locale", [
            form.section("Unavailable", [base.missing_note("localectl", "systemd-localed")]),
        ])

    state = parse_localectl(util.run(["localectl", "status"], timeout=10).out)
    locale_conf = util.read_text("/etc/locale.conf").strip().splitlines()
    locales = sorted({line.strip() for line in util.run(["locale", "-a"], timeout=20).lines()})
    current = state.get("System Locale", "").split("=", 1)[-1]

    return base.make_page("locale", [
        form.section("Current", [
            form.info("System locale", current or "unset", mono=True),
            form.info("Language", state.get("System Locale", "").split(":", 1)[-1].strip(),
                      mono=True),
            form.info("Keyboard layout", state.get("X11 Layout", "unknown"), mono=True),
            form.info("Keymap", state.get("VC Keymap", "unknown"), mono=True),
        ]),
        form.section("Available", [
            form.choice("locale", "Locale", current, locales or [current]),
            form.note("Setting a locale needs the locale generated first "
                      "(/etc/locale.gen + locale-gen). This panel writes the choice but "
                      "does not regenerate locales.", "warn"),
            form.action("Apply locale", "locale.set", variant="primary", danger=False),
        ]),
        form.section("Keyboard layout", [
            form.note("The compositor's layout lives in Hyprland's input settings. "
                      "Use Input Devices for a live change, or config-manager for a "
                      "persistent one.", "info"),
            form.action("Open Hyprland settings", "locale.open_hyprland"),
        ]),
        form.section("Configuration", [
            form.info("/etc/locale.conf", "\n".join(locale_conf) or "missing", mono=True),
        ]),
    ])


def action(name: str, args: dict) -> dict:
    if name == "locale.set":
        locale = str(args.get("locale") or "").strip()
        if not locale:
            return base.fail("No locale selected")
        result = priv.run_priv(["localectl", "set-locale", f"LANG={locale}"])
        if not result.ok:
            return base.denied(result.text.strip() or "localectl failed",
                               priv.command_for(["localectl", "set-locale", f"LANG={locale}"]))
        return base.ok(f"Locale set to {locale}", details=["localectl set-locale",
                                                           "run locale-gen if the locale is new"])
    if name == "locale.open_hyprland":
        argv = ["config-manager", "open", "--page", "input"]
        if util.which(argv[0]) is None:
            return base.fail("config-manager is not installed")
        util.run(argv, timeout=10)
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
