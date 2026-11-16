// Launcher-owned palette. Templates the legacy rofi variants without reading
// any rofi file: `auto` follows the bar Theme (pywal or imported), and the
// named variants port the old rasi palettes to QML. Pywal colours still drive
// the accents, so wallpaper changes re-tint every variant.
pragma Singleton

import QtQuick
import Quickshell
import "../theme"

Singleton {
    id: root

    // Settings order; labels are shown in the Launcher page.
    readonly property var variants: [
        "auto", "hyprtk", "hyprtk-pywal", "hyprtk-aero", "hyprtk-clear",
        "hyprtk-glass", "hyprtk-inverse", "hyprtk-light",
        "hyprtk-liquid-glass", "hyprtk-negative", "hyprtk-reverse"
    ]
    readonly property var variantLabels: [
        "Follow bar theme", "Hyprtk (dark glass)", "Hyprtk Pywal", "Aero",
        "Clear", "Glass", "Inverse", "Light", "Liquid Glass", "Negative",
        "Reverse"
    ]

    readonly property string variant: LauncherConfig.theme
    readonly property bool isAuto: !variant || variant === "auto"
        || !root.palettes[variant]
    readonly property var palettes: ({
        // ── legacy rasi ports (panel, fg, dim, border, input, buttons, cells,
        //    selection); "@…" tokens resolve to the live pywal/bar palette ──
        "hyprtk": {
            panel: "rgba(10,10,20,0.60)", fg: "#ffffff", dim: "#c5c4c4",
            border: "rgba(255,255,255,0.08)",
            inputBg: "rgba(255,255,255,0.05)", inputBorder: "rgba(255,255,255,0.07)",
            buttonBg: "rgba(255,255,255,0.05)", cellBg: "transparent",
            cellBorder: "rgba(255,255,255,0.07)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-pywal": {
            panel: "@pywal-panel", fg: "@foreground", dim: "@dim",
            border: "rgba(255,255,255,0.08)",
            inputBg: "@pywal-panel", inputBorder: "rgba(255,255,255,0.07)",
            buttonBg: "@pywal-panel", cellBg: "@pywal-panel",
            cellBorder: "rgba(255,255,255,0.07)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-aero": {
            panel: "rgba(24,21,20,0.70)", fg: "#ffffff", dim: "#c5c4c4",
            border: "rgba(255,255,255,0.20)",
            inputBg: "rgba(255,255,255,0.06)", inputBorder: "rgba(255,255,255,0.15)",
            buttonBg: "rgba(255,255,255,0.05)", cellBg: "rgba(255,255,255,0.05)",
            cellBorder: "rgba(255,255,255,0.15)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-clear": {
            panel: "rgba(10,10,20,0.15)", fg: "rgba(220,220,235,0.90)",
            dim: "rgba(220,220,235,0.60)", border: "rgba(255,255,255,0.05)",
            inputBg: "rgba(255,255,255,0.05)", inputBorder: "rgba(255,255,255,0.05)",
            buttonBg: "rgba(255,255,255,0.05)", cellBg: "rgba(255,255,255,0.05)",
            cellBorder: "rgba(255,255,255,0.07)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-glass": {
            panel: "transparent", fg: "rgba(200,200,210,0.95)",
            dim: "rgba(200,200,210,0.55)", border: "rgba(255,255,255,0.12)",
            inputBg: "transparent", inputBorder: "rgba(255,255,255,0.12)",
            buttonBg: "transparent", cellBg: "transparent",
            cellBorder: "rgba(255,255,255,0.12)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-inverse": {
            panel: "transparent", fg: "rgba(220,220,235,0.90)",
            dim: "rgba(220,220,235,0.55)", border: "rgba(0,0,0,0.07)",
            inputBg: "rgba(20,20,30,0.55)", inputBorder: "rgba(0,0,0,0.07)",
            buttonBg: "rgba(20,20,30,0.55)", cellBg: "rgba(20,20,30,0.55)",
            cellBorder: "rgba(0,0,0,0.07)",
            selectedBg: "rgba(35,35,50,0.65)", selectedFg: "rgba(235,235,245,0.95)"
        },
        "hyprtk-light": {
            panel: "rgba(255,255,255,0.55)", fg: "rgba(20,20,30,0.90)",
            dim: "rgba(20,20,30,0.60)", border: "rgba(255,255,255,0.50)",
            inputBg: "rgba(255,255,255,0.35)", inputBorder: "rgba(255,255,255,0.40)",
            buttonBg: "rgba(255,255,255,0.35)", cellBg: "rgba(255,255,255,0.35)",
            cellBorder: "rgba(255,255,255,0.40)",
            selectedBg: "rgba(20,20,30,0.50)", selectedFg: "#ffffff"
        },
        "hyprtk-liquid-glass": {
            panel: "rgba(28,32,46,0.45)", fg: "rgba(238,241,248,0.95)",
            dim: "rgba(238,241,248,0.60)", border: "rgba(255,255,255,0.14)",
            inputBg: "rgba(255,255,255,0.07)", inputBorder: "rgba(255,255,255,0.12)",
            buttonBg: "rgba(255,255,255,0.07)", cellBg: "rgba(255,255,255,0.07)",
            cellBorder: "rgba(255,255,255,0.12)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        },
        "hyprtk-negative": {
            panel: "rgba(250,250,240,0.55)", fg: "rgba(35,35,20,0.90)",
            dim: "rgba(35,35,20,0.60)", border: "rgba(0,0,0,0.08)",
            inputBg: "rgba(0,0,0,0.04)", inputBorder: "rgba(0,0,0,0.07)",
            buttonBg: "rgba(0,0,0,0.04)", cellBg: "rgba(0,0,0,0.04)",
            cellBorder: "rgba(0,0,0,0.07)",
            selectedBg: "rgba(0,0,0,0.10)", selectedFg: "rgba(35,35,20,0.95)"
        },
        "hyprtk-reverse": {
            panel: "rgba(255,255,255,0.50)", fg: "rgba(20,20,30,0.90)",
            dim: "rgba(20,20,30,0.60)", border: "rgba(255,255,255,0.45)",
            inputBg: "rgba(255,255,255,0.40)", inputBorder: "rgba(0,0,0,0.06)",
            buttonBg: "rgba(255,255,255,0.40)", cellBg: "rgba(255,255,255,0.40)",
            cellBorder: "rgba(0,0,0,0.06)",
            selectedBg: "@accent", selectedFg: "#ffffff"
        }
    })

    readonly property var p: root.isAuto ? ({}) : (root.palettes[root.variant] || root.palettes["hyprtk"])

    function tok(v) {
        if (typeof v !== "string")
            return v;
        // QML's color parser does not accept CSS rgba() strings, so convert
        // them (the palettes are written in the old rasi syntax).
        const m = v.match(/^rgba\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$/);
        if (m)
            return Qt.rgba(Number(m[1]) / 255, Number(m[2]) / 255,
                           Number(m[3]) / 255, Number(m[4]));
        switch (v) {
        case "@foreground":
            return Theme.strKey(Theme.special, "foreground", "#e5e7eb");
        case "@background":
            return Theme.strKey(Theme.special, "background", "#1e1e2e");
        case "@pywal-panel": {
            const c = Qt.color(Theme.strKey(Theme.special, "background", "#1e1e2e"));
            return Qt.rgba(c.r, c.g, c.b, 0.5);
        }
        case "@accent":
            return Theme.walColor(5, "#c084fc");
        case "@accent2":
            return Theme.walColor(6, "#22d3ee");
        case "@dim":
            return Theme.walColor(8, "#6b7280");
        default:
            return v;
        }
    }

    readonly property color panelColor: root.isAuto
        ? Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b,
                  Theme.panelOpacity)
        : root.tok(root.p.panel)
    readonly property color foreground: root.isAuto ? Theme.foreground : root.tok(root.p.fg)
    readonly property color dim: root.isAuto ? Theme.dim : root.tok(root.p.dim)
    readonly property color accent: root.isAuto ? Theme.accent : root.tok("@accent")
    readonly property color accent2: root.isAuto ? Theme.accent2 : root.tok("@accent2")
    readonly property color borderColor: root.isAuto
        ? Theme.alpha(Theme.foreground, 0.08) : root.tok(root.p.border)
    readonly property color inputBg: root.isAuto
        ? Theme.alpha(Theme.background, 0.6) : root.tok(root.p.inputBg)
    readonly property color inputBorder: root.isAuto
        ? Theme.alpha(Theme.foreground, 0.07) : root.tok(root.p.inputBorder)
    readonly property color buttonBg: root.isAuto
        ? Theme.alpha(Theme.foreground, 0.05) : root.tok(root.p.buttonBg)
    readonly property color cellBg: root.isAuto ? "transparent" : root.tok(root.p.cellBg)
    readonly property color cellBorder: root.isAuto
        ? Theme.alpha(Theme.foreground, 0.07) : root.tok(root.p.cellBorder)
    readonly property color selectedBg: root.isAuto ? Theme.accent : root.tok(root.p.selectedBg)
    readonly property color selectedFg: root.isAuto ? "#ffffff" : root.tok(root.p.selectedFg)
    readonly property color chipBg: root.buttonBg
    readonly property color chipHover: Theme.alpha(root.accent, 0.25)
}
