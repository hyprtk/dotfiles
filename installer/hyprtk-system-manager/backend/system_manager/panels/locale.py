"""Region & Language — locale, language and keyboard layout.

Setting a locale is two independent steps: the locale has to exist
(``/etc/locale.gen`` + ``locale-gen``) and it has to be selected
(``localectl set-locale``). This panel does both in one privileged call so the
user authenticates once, and it never claims a locale is live when only the
choice was written.
"""

from __future__ import annotations

import os
import re
import shlex
import tempfile
from pathlib import Path

from .. import form, paths, priv, util
from . import base

SUPPORTED = Path("/usr/share/i18n/SUPPORTED")
LOCALE_GEN = "/etc/locale.gen"
LOCALE_RE = re.compile(r"^[a-z]{2,3}(_[A-Za-z]{2,4})?(@[a-z]+)?\.[A-Za-z0-9-]+$")

IM_START = "-- >>> hyprtk-system-manager managed input method (do not edit this block by hand)"
IM_END = "-- <<< hyprtk-system-manager managed input method"
IM_FRAMEWORKS = {
    "ibus": {"gtk": "ibus", "qt": "ibus", "xmod": "@im=ibus", "daemon": "ibus-daemon"},
    "fcitx5": {"gtk": "fcitx", "qt": "fcitx", "xmod": "@im=fcitx", "daemon": "fcitx5"},
    "fcitx": {"gtk": "fcitx", "qt": "fcitx", "xmod": "@im=fcitx", "daemon": "fcitx"},
}


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


def im_block(framework: str) -> str:
    values = IM_FRAMEWORKS[framework]
    lines = [IM_START,
             'hl.env("GTK_IM_MODULE", "{}")'.format(values["gtk"]),
             'hl.env("QT_IM_MODULE", "{}")'.format(values["qt"]),
             'hl.env("XMODIFIERS", "{}")'.format(values["xmod"]),
             IM_END]
    return "\n".join(lines) + "\n"


def strip_im_block(text: str) -> str:
    pattern = re.compile(re.escape(IM_START) + r".*?" + re.escape(IM_END) + r"\n?",
                         re.DOTALL)
    return pattern.sub("", text)


def read_im(text: str) -> str:
    """Framework named by the managed block, else by a plain hl.env line."""
    if IM_START in text:
        block = text.split(IM_START, 1)[1].split(IM_END, 1)[0]
        for line in block.splitlines():
            if "GTK_IM_MODULE" in line:
                for name, values in IM_FRAMEWORKS.items():
                    if values["gtk"] in line:
                        return name
        return "custom"
    for line in text.splitlines():
        if "GTK_IM_MODULE" not in line or line.strip().startswith("--"):
            continue
        for name, values in IM_FRAMEWORKS.items():
            if values["gtk"] in line:
                return name
    return ""


def _im_state() -> dict:
    installed = [name for name in ("fcitx5", "ibus", "fcitx")
                 if util.which(name) or util.which(IM_FRAMEWORKS[name]["daemon"])]
    running = {}
    for name in installed:
        daemon = IM_FRAMEWORKS[name]["daemon"]
        running[name] = bool(util.which("pgrep") and
                             util.run(["pgrep", "-x", daemon], timeout=4).ok)
    env = {key: os.environ.get(key, "") for key in
           ("GTK_IM_MODULE", "QT_IM_MODULE", "XMODIFIERS")}
    return {"installed": installed, "running": running, "env": env}


def probe() -> dict:
    if util.which("localectl") is None:
        return base.make_page("locale", [
            form.section("Unavailable", [base.missing_note("localectl", "systemd-localed")]),
            form.section("Input methods", _im_rows()),
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
        form.section("Input methods", _im_rows()),
        form.section("Configuration", [
            form.info("/etc/locale.conf", "\n".join(locale_conf) or "missing", mono=True),
        ]),
    ], status="partial")


def _im_rows() -> list[dict]:
    state = _im_state()
    env_file = (paths.hypr_dir() or Path("")) / "environment.lua"
    configured = read_im(util.read_text(env_file)) if env_file.is_file() else ""
    rows: list[dict] = []
    if not state["installed"]:
        rows.append(form.note("No input-method framework is installed (fcitx5 or ibus). "
                              "Install one to type languages that need composition.",
                              "info"))
    else:
        rows.append(form.info("Installed", ", ".join(state["installed"])))
        rows.append(form.info("Running", ", ".join(
            name for name, alive in state["running"].items() if alive) or "none"))
    rows.append(form.info("GTK_IM_MODULE", state["env"]["GTK_IM_MODULE"] or "unset", mono=True))
    rows.append(form.info("QT_IM_MODULE", state["env"]["QT_IM_MODULE"] or "unset", mono=True))
    choices = [{"value": "none", "label": "Not managed here"}]
    choices += [{"value": name, "label": name} for name in state["installed"]]
    if configured and configured not in [choice["value"] for choice in choices]:
        choices.append({"value": configured, "label": configured + " (from environment.lua)"})
    rows.append(form.choice("im_framework", "Framework", configured or "none", choices,
                            help="Written to environment.lua as a managed block; new "
                                 "sessions pick it up."))
    if state["installed"]:
        rows.append(form.action("Start the input method now", "locale.im_start"))
    rows.append(form.info("Configuration", str(env_file) if env_file.is_file() else "missing",
                          mono=True))
    rows.append(form.note("The managed block only sets GTK_IM_MODULE, QT_IM_MODULE and "
                          "XMODIFIERS. Adding a language inside the framework is its own "
                          "tool (fcitx5-configtool / ibus-setup).", "info"))
    return rows


def _keymap_ok(keymap: str) -> bool:
    if util.which("localectl") is None:
        return False
    listing = util.run(["localectl", "list-keymaps"], timeout=20)
    return keymap in {line.strip() for line in listing.lines()}


def _apply_input_method(framework: str) -> dict:
    env_file = (paths.hypr_dir() or Path("")) / "environment.lua"
    if not env_file.is_file():
        return base.fail("No environment.lua in the Hyprland config")
    original = util.read_text(env_file)
    stripped = strip_im_block(original).rstrip()
    updated = stripped + "\n"
    if framework != "none":
        if framework not in IM_FRAMEWORKS:
            return base.fail(f"Unknown input method framework {framework!r}")
        updated = stripped + "\n\n" + im_block(framework)
    if updated == original:
        return base.ok("Nothing to change")
    util.atomic_write(env_file, updated)
    ok, text = base.hypr_reload()
    if not ok:
        util.atomic_write(env_file, original)
        base.hypr_reload()
        return base.fail(f"Hyprland rejected the input method block: {text}")
    if framework == "none":
        return base.ok("Input method block removed", details=[str(env_file)])
    return base.ok(f"{framework} set as the input method for new sessions",
                   details=[str(env_file)])


def apply(changes: dict) -> dict:
    if "im_framework" in changes:
        return _apply_input_method(str(changes.get("im_framework") or "none"))

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
    if name == "locale.im_start":
        state = _im_state()
        for framework in ("fcitx5", "ibus", "fcitx"):
            if framework not in state["installed"]:
                continue
            daemon = IM_FRAMEWORKS[framework]["daemon"]
            command = [daemon, "-d"] if daemon in ("fcitx5", "ibus-daemon") else [daemon]
            if util.spawn(command):
                return base.ok(f"Started {framework}")
            return base.fail(f"Could not start {framework}")
        return base.fail("No input-method framework is installed")
    if name == "locale.open_hyprland":
        argv = ["config-manager", "open", "--page", "input"]
        if util.which(argv[0]) is None:
            return base.fail("config-manager is not installed")
        if not util.spawn(argv):
            return base.fail("Could not start config-manager")
        return base.ok("Opened Hyprland settings")
    return base.fail(f"unknown action {name!r}")
