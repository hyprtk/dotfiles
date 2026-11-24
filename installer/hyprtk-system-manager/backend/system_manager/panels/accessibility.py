"""Accessibility — text scaling, motion, contrast, keyboard aids, reader and OSK.

The GNOME a11y schemas are present on this stack (``gsettings-desktop-schemas``),
but three different things are needed for a preference to take effect:

* **GTK/Qt read the interface keys directly** — text scaling, animations, cursor
  size, high contrast and reduced motion work as soon as the key is set.
* **sticky/bounce/slow/mouse keys need a settings daemon** (gnome-settings-daemon
  a11y plugins or an equivalent). The panel states whether one is running rather
  than pretending the toggle does something.
* **a screen reader or on-screen keyboard needs its own program** (orca, an OSK).
  Availability is reported from the binaries, not assumed.
"""

from __future__ import annotations

from .. import form, util
from . import appearance, base

INTERFACE = "org.gnome.desktop.interface"
A11Y = "org.gnome.desktop.a11y"
A11Y_IFACE = "org.gnome.desktop.a11y.interface"
A11Y_KB = "org.gnome.desktop.a11y.keyboard"
A11Y_APPS = "org.gnome.desktop.a11y.applications"

# key → (schema, gsettings key, default value)
TOGGLES: dict[str, tuple[str, str, bool]] = {
    "show_caret": (A11Y, "always-show-text-caret", False),
    "animations": (INTERFACE, "enable-animations", True),
    "reduced_motion": (A11Y_IFACE, "reduced-motion", False),
    "high_contrast": (A11Y_IFACE, "high-contrast", False),
    "sticky_keys": (A11Y_KB, "sticky-keys-enable", False),
    "bounce_keys": (A11Y_KB, "bouncekeys-enable", False),
    "slow_keys": (A11Y_KB, "slowkeys-enable", False),
    "mouse_keys": (A11Y_KB, "mousekeys-enable", False),
    "screen_reader": (A11Y_APPS, "screen-reader-enabled", False),
    "screen_keyboard": (A11Y_APPS, "screen-keyboard-enabled", False),
    "magnifier": (A11Y_APPS, "screen-magnifier-enabled", False),
}

PRESETS = [
    {"value": "100", "label": "Default (100%)"},
    {"value": "115", "label": "Large (115%)"},
    {"value": "125", "label": "Larger (125%)"},
    {"value": "150", "label": "Extra large (150%)"},
    {"value": "200", "label": "Largest (200%)"},
]

OSKS = ("squeekboard", "maliit-keyboard", "onboard", "wvkbd-mobintl", "wvkbd-comp")
DAEMONS = ("gsd-a11y-keyboard", "gsd-a11y-settings", "kaccess")


def _gsettings() -> bool:
    return util.which("gsettings") is not None


def get(schema: str, key: str, default: str = "") -> str:
    if not _gsettings():
        return default
    result = util.run(["gsettings", "get", schema, key], timeout=8)
    return (result.out or default).strip().strip("'") or default


def set_key(schema: str, key: str, value: str) -> bool:
    if not _gsettings():
        return False
    return util.run(["gsettings", "set", schema, key, value], timeout=8).ok


def truth(schema: str, key: str, default: bool = False) -> bool:
    return get(schema, key, "true" if default else "false").lower() == "true"


def osk_binary() -> str:
    for name in OSKS:
        found = util.which(name)
        if found:
            return found
    return ""


def reader_binary() -> str:
    return util.which("orca") or ""


def daemon_running() -> str:
    """Name of a running a11y settings daemon, or an empty string."""
    for name in DAEMONS:
        result = util.run(["pgrep", "-x", name[:15]], timeout=5)
        if result.ok and result.out.strip():
            return name
    return ""


def probe() -> dict:
    gtk = appearance.gtk_values()
    try:
        scaling = float(get(INTERFACE, "text-scaling-factor", "1.0"))
    except ValueError:
        scaling = 1.0
    try:
        cursor_size = int(get(INTERFACE, "cursor-size", "24"))
    except ValueError:
        cursor_size = int(gtk.get("gtk-cursor-theme-size") or 24)

    flags = {key: truth(schema, name, default) for key, (schema, name, default) in TOGGLES.items()}
    daemon = daemon_running()
    osk = osk_binary()
    reader = reader_binary()

    keyboard_rows: list[dict] = [
        form.toggle("sticky_keys", "Sticky keys", flags["sticky_keys"]),
        form.toggle("slow_keys", "Slow keys", flags["slow_keys"]),
        form.toggle("bounce_keys", "Bounce keys", flags["bounce_keys"]),
        form.toggle("mouse_keys", "Mouse keys (keypad pointer)", flags["mouse_keys"]),
    ]
    if daemon:
        keyboard_rows.append(form.note(
            f"{daemon} is running, so these keyboard aids take effect immediately.", "info"))
    else:
        keyboard_rows.append(form.note(
            "No accessibility settings daemon is running (gnome-settings-daemon's a11y "
            "plugins or kaccess). The toggles are stored and take effect in a session "
            "that runs one; Hyprland itself does not implement sticky/bounce keys.", "warn"))

    reader_rows: list[dict] = [form.toggle("screen_reader", "Enable screen reader", flags["screen_reader"])]
    if reader:
        reader_rows.append(form.info("Orca", reader, mono=True))
        reader_rows.append(form.action("Start Orca now", "accessibility.launch_reader"))
    else:
        reader_rows.append(form.note(
            "Orca is not installed. Install `orca` to read the screen; the preference "
            "above is kept for a session that has it.", "warn"))

    osk_rows: list[dict] = [form.toggle("screen_keyboard", "Enable on-screen keyboard",
                                        flags["screen_keyboard"])]
    if osk:
        osk_rows.append(form.info("On-screen keyboard", osk, mono=True))
        osk_rows.append(form.action("Open on-screen keyboard",
                                    "accessibility.launch_osk"))
    else:
        osk_rows.append(form.note(
            "No on-screen keyboard found (squeekboard, maliit-keyboard, onboard, wvkbd).",
            "warn"))

    return base.make_page("accessibility", [
        form.section("Text", [
            form.slider("text_scaling", "Text scaling", round(scaling * 100),
                        minimum=100, maximum=250, step=5, unit="%"),
            form.choice("preset", "Quick size", str(next(
                (row["value"] for row in PRESETS
                 if abs(int(row["value"]) - round(scaling * 100)) < 3), "100")),
                [row["label"] for row in PRESETS],
                help="Applies the same text-scaling-factor as the slider."),
            form.toggle("show_caret", "Always show the text caret", flags["show_caret"]),
            form.info("Interface font", gtk.get("gtk-font-name") or "unknown", mono=True),
        ]),
        form.section("Motion", [
            form.toggle("animations", "Enable animations", flags["animations"]),
            form.toggle("reduced_motion", "Prefer reduced motion", flags["reduced_motion"]),
            form.note("Window animations and blur belong to Hyprland; use Hyprland "
                      "settings for those.", "info"),
        ]),
        form.section("Contrast", [
            form.toggle("high_contrast", "High contrast", flags["high_contrast"]),
            form.note("High contrast switches GTK applications to the HighContrast theme "
                      "when that theme is installed.", "info"),
        ]),
        form.section("Keyboard aids", keyboard_rows),
        form.section("Screen reader", reader_rows),
        form.section("On-screen keyboard", osk_rows),
        form.section("Pointer", [
            form.number("cursor_size", "Cursor size", cursor_size, minimum=12, maximum=64),
            form.toggle("magnifier", "Enable screen magnifier", flags["magnifier"]),
            form.note("Hyprland has no built-in magnifier; the preference is stored for a "
                      "session that provides one.", "info"),
        ]),
        form.section("Toolkit", [
            form.info("gsettings", "available" if _gsettings() else "not installed"),
            form.info("Applied to", "GTK and Qt (QT_QPA_PLATFORMTHEME=gtk3)", mono=True),
        ]),
    ], status="partial")


def apply(changes: dict) -> dict:
    if not _gsettings():
        return base.fail("gsettings is not available")

    details: list[str] = []
    failures: list[str] = []

    scale = changes.get("text_scaling", changes.get("preset"))
    if scale is not None and str(scale) != "":
        value = max(100, min(250, int(scale))) / 100
        if set_key(INTERFACE, "text-scaling-factor", f"{value:.2f}"):
            details.append(f"text-scaling-factor {value:.2f}")
        else:
            failures.append("text-scaling-factor")

    for key, (schema, name, _default) in TOGGLES.items():
        if key not in changes:
            continue
        if set_key(schema, name, "true" if changes[key] else "false"):
            details.append(name)
        else:
            failures.append(name)

    if "cursor_size" in changes:
        size = max(12, min(64, int(changes["cursor_size"])))
        if set_key(INTERFACE, "cursor-size", str(size)):
            details.append("cursor-size")
        details.extend(appearance.gtk_set({"gtk-cursor-theme-size": str(size)}))

    if failures:
        return base.fail("Could not set " + ", ".join(failures),
                         details=details, refresh=True)
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Accessibility updated", details=details,
                   note="Some applications only pick these up when they restart.")


def action(name: str, args: dict) -> dict:
    if name == "accessibility.launch_reader":
        reader = reader_binary()
        if not reader:
            return base.fail("Orca is not installed")
        if not util.spawn([reader]):
            return base.fail("Could not start Orca")
        return base.ok("Starting Orca", details=[reader])
    if name == "accessibility.launch_osk":
        osk = osk_binary()
        if not osk:
            return base.fail("No on-screen keyboard is installed")
        if not util.spawn([osk]):
            return base.fail("Could not start the on-screen keyboard")
        return base.ok("Opening the on-screen keyboard", details=[osk])
    return base.fail(f"unknown action {name!r}")
