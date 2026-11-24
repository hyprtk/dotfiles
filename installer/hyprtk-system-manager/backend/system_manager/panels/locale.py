"""Region & Language — locale, language and keyboard layout.

Setting a locale is two independent steps: the locale has to exist
(``/etc/locale.gen`` + ``locale-gen``) and it has to be selected
(``localectl set-locale``). This panel does both in one privileged call so the
user authenticates once, and it never claims a locale is live when only the
choice was written.
"""

from __future__ import annotations

import re
import shlex
import tempfile
from pathlib import Path

from .. import form, priv, util
from . import base

SUPPORTED = Path("/usr/share/i18n/SUPPORTED")
LOCALE_GEN = "/etc/locale.gen"
LOCALE_RE = re.compile(r"^[a-z]{2,3}(_[A-Za-z]{2,4})?(@[a-z]+)?\.[A-Za-z0-9-]+$")


def parse_localectl(text: str) -> dict[str, str]:
    """Parse ``localectl status``; every key but the first is indented."""
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key:
            data[key] = value.strip()
    return data


def parse_locale_gen(text: str) -> list[str]:
    """Locales enabled in /etc/locale.gen (uncommented lines)."""
    enabled: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = stripped.split()[0]
        if name and name not in enabled:
            enabled.append(name)
    return enabled


def supported_locales(supported: str, generated: list[str]) -> list[str]:
    """UTF-8 locales that ``locale-gen`` can build, plus the generated ones."""
    found: list[str] = []
    for line in supported.splitlines():
        parts = line.split()
        if len(parts) < 2 or "UTF-8" not in (parts[1] or "").upper():
            continue
        if parts[0] not in found:
            found.append(parts[0])
    for name in generated:
        norm = name.replace(".utf8", ".UTF-8")
        if norm not in found:
            found.append(norm)
    return sorted(found)


def normalise_locale(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\.utf-?8$", ".UTF-8", text, flags=re.IGNORECASE)
    if "." not in text:
        text += ".UTF-8"
    return text


def enable_locale(text: str, locale: str) -> str:
    """Return /etc/locale.gen content with *locale* uncommented (or appended)."""
    charset = locale.split(".", 1)[1] if "." in locale else "UTF-8"
    lines = text.splitlines()
    hit = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        candidate = stripped.lstrip("#").strip()
        if not candidate or candidate.startswith("%"):
            continue
        name = candidate.split()[0]
        if name.lower() != locale.lower():
            continue
        lines[index] = f"{locale} {charset}"
        hit = True
    if not hit:
        lines.append(f"{locale} {charset}")
    return "\n".join(lines) + "\n"


def probe() -> dict:
    if util.which("localectl") is None:
        return base.make_page("locale", [
            form.section("Unavailable", [base.missing_note("localectl", "systemd-localed")]),
        ])

    state = parse_localectl(util.run(["localectl", "status"], timeout=10).out)
    locale_conf = util.read_text("/etc/locale.conf").strip().splitlines()
    generated = sorted({line.strip() for line in util.run(["locale", "-a"], timeout=20).lines()})
    current = normalise_locale(state.get("System Locale", "").split("=", 1)[-1].strip())
    enabled = parse_locale_gen(util.read_text(LOCALE_GEN))
    choices = supported_locales(util.read_text(SUPPORTED), generated)
    if current and current not in choices:
        choices = sorted(set(choices) | {current})
    keymap = state.get("VC Keymap", "")

    return base.make_page("locale", [
        form.section("Current", [
            form.info("Language", current or "unset", mono=True),
            form.info("Keyboard layout", state.get("X11 Layout", "unknown"), mono=True),
            form.info("Keymap", keymap or "unknown", mono=True),
            form.info("Generated locales", ", ".join(generated) or "unknown", mono=True),
        ]),
        form.section("Language", [
            form.choice("locale", "Locale", current, choices,
                        help="UTF-8 locales from /usr/share/i18n/SUPPORTED."),
            form.toggle("generate", "Generate if missing", True),
            form.note("Applying writes LANG to /etc/locale.conf; enabling generation also "
                      "uncomments the locale in /etc/locale.gen and runs locale-gen. Newly "
                      "generated locales are available to applications started afterwards.",
                      "info"),
            form.info("Enabled in /etc/locale.gen", ", ".join(enabled) or "none", mono=True),
        ]),
        form.section("Keyboard", [
            form.text("keymap", "Console keymap", keymap,
                      placeholder="uk",
                      help="A name from `localectl list-keymaps` (text console)."),
            form.note("The compositor's layout is a Hyprland input setting: change it live in "
                      "Input Devices or persistently in config-manager.", "info"),
            form.action("Open Hyprland settings", "locale.open_hyprland"),
        ]),
        form.section("Configuration", [
            form.info("/etc/locale.conf", "\n".join(locale_conf) or "missing", mono=True),
        ]),
    ], status="partial")


def _keymap_ok(keymap: str) -> bool:
    if util.which("localectl") is None:
        return False
    listing = util.run(["localectl", "list-keymaps"], timeout=20)
    return keymap in {line.strip() for line in listing.lines()}


def apply(changes: dict) -> dict:
    target = normalise_locale(str(changes.get("locale") or ""))
    generate = bool(changes.get("generate"))
    keymap = str(changes.get("keymap") or "").strip()

    steps: list[str] = []
    details: list[str] = []
    temp = ""

    if target:
        if not LOCALE_RE.match(target):
            return base.fail(f"{target!r} is not a valid locale name")
        if generate:
            updated = enable_locale(util.read_text(LOCALE_GEN), target)
            handle = tempfile.NamedTemporaryFile("w", prefix="locale.gen-", delete=False)
            temp = handle.name
            with handle:
                handle.write(updated)
            steps.append(f"install -m 0644 {shlex.quote(temp)} {LOCALE_GEN} && locale-gen")
            details.append(f"enabled {target} in {LOCALE_GEN} and ran locale-gen")
        steps.append(f"localectl set-locale LANG={shlex.quote(target)}")
        details.append(f"set-locale LANG={target}")

    if keymap:
        if len(keymap) > 32 or any(ch.isspace() for ch in keymap):
            return base.fail("The keymap name looks invalid")
        if not _keymap_ok(keymap):
            return base.fail(f"{keymap!r} is not in `localectl list-keymaps`")
        steps.append(f"localectl set-keymap {shlex.quote(keymap)}")
        details.append(f"set-keymap {keymap}")

    if not steps:
        return base.ok("Nothing to change")

    script = " && ".join(steps)
    argv = ["sh", "-c", script]
    result = priv.run_priv(argv)
    if temp:
        try:
            Path(temp).unlink()
        except OSError:
            pass
    if not result.ok:
        return base.denied((result.err or result.out).strip() or "localectl failed",
                           priv.command_for(["localectl", "set-locale", f"LANG={target}"]))
    note = None
    if generate and target:
        note = "Restart applications (or log out) to pick up a newly generated locale."
    return base.ok("Region & language updated", details=details + [priv.command_for(argv)],
                   note=note)


def action(name: str, args: dict) -> dict:
    if name == "locale.open_hyprland":
        argv = ["config-manager", "open", "--page", "input"]
        if util.which(argv[0]) is None:
            return base.fail("config-manager is not installed")
        if not util.spawn(argv):
            return base.fail("Could not start config-manager")
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
