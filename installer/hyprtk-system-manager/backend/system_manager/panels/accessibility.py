"""Accessibility — text scaling, animations, caret and cursor."""

from __future__ import annotations

from .. import form, util
from . import appearance, base

SCHEMA = "org.gnome.desktop.interface"
A11Y = "org.gnome.desktop.a11y"


def _get(schema: str, key: str, default: str = "") -> str:
    if util.which("gsettings") is None:
        return default
    result = util.run(["gsettings", "get", schema, key], timeout=8)
    return (result.out or default).strip().strip("'")


def _set(schema: str, key: str, value: str) -> bool:
    if util.which("gsettings") is None:
        return False
    return util.run(["gsettings", "set", schema, key, value], timeout=8).ok


def probe() -> dict:
    gtk = appearance.gtk_values()
    scaling = 1.0
    try:
        scaling = float(_get(SCHEMA, "text-scaling-factor", "1.0"))
    except ValueError:
        pass
    animations = _get(SCHEMA, "enable-animations", "true") == "true"
    caret = _get(A11Y, "always-show-text-caret", "false") == "true"
    cursor_size = int(gtk.get("gtk-cursor-theme-size") or 24)
    gsettings_ok = util.which("gsettings") is not None

    return base.make_page("accessibility", [
        form.section("Text", [
            form.slider("text_scaling", "Text scaling", round(scaling * 100),
                        minimum=100, maximum=250, step=5, unit="%"),
            form.toggle("show_caret", "Always show the text caret", caret),
            form.info("Interface font", gtk.get("gtk-font-name") or "unknown", mono=True),
        ]),
        form.section("Motion", [
            form.toggle("animations", "Enable animations", animations),
            form.note("Hyprland's own animations live in Hyprland settings.", "info"),
        ]),
        form.section("Pointer", [
            form.number("cursor_size", "Cursor size", cursor_size, minimum=12, maximum=64),
        ]),
        form.section("Keyboard", [
            form.note("Sticky keys and bounce keys need a desktop settings daemon that this "
                      "stack does not run; Hyprland repeat settings are in Input Devices.", "warn"),
        ]),
        form.section("Toolkit", [
            form.info("gsettings", "available" if gsettings_ok else "not installed"),
            form.info("Applied to", "GTK and Qt (QT_QPA_PLATFORMTHEME=gtk3)", mono=True),
        ]),
    ], status="partial")


def apply(changes: dict) -> dict:
    details: list[str] = []
    if "text_scaling" in changes:
        value = max(100, min(250, int(changes["text_scaling"]))) / 100
        if _set(SCHEMA, "text-scaling-factor", f"{value:.2f}"):
            details.append(f"text-scaling-factor {value:.2f}")
        else:
            return base.fail("gsettings is not available")
    if "animations" in changes:
        if _set(SCHEMA, "enable-animations", "true" if changes["animations"] else "false"):
            details.append("enable-animations")
    if "show_caret" in changes:
        if _set(A11Y, "always-show-text-caret", "true" if changes["show_caret"] else "false"):
            details.append("always-show-text-caret")
    if "cursor_size" in changes:
        size = max(12, min(64, int(changes["cursor_size"])))
        details.extend(appearance.gtk_set({"gtk-cursor-theme-size": str(size)}))
    if not details:
        return base.ok("Nothing to change")
    return base.ok("Accessibility updated", details=details,
                   note="Some applications only pick these up when they restart.")
