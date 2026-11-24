// hyprtk theme — the same resolution order as hyprtk-bar-qt:
//   1. the bar's theme block in ~/.config/hyprtk-bar-qt/config.json
//   2. live pywal (~/.cache/wal/colors.json)
//   3. hyprtk fallbacks
//
// Colours are converted to real QML colours here: a `property color` bound to
// an "rgba(...)" string silently becomes #000000, so every value goes through
// hex()/alpha() instead.
pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    readonly property string home: Quickshell.env("HOME") || ""

    // ── files ──────────────────────────────────────────────────────────
    property var wal: ({})
    FileView {
        id: walFile
        path: root.home + "/.cache/wal/colors.json"
        watchChanges: true
        blockLoading: true
        printErrors: false
        onLoaded: root._parseWal()
        onTextChanged: root._parseWal()
        onFileChanged: reload()
    }
    function _parseWal() {
        try { root.wal = JSON.parse(walFile.text()) || ({}); }
        catch (e) { root.wal = ({}); }
    }

    property var barCfg: ({})
    FileView {
        id: cfgFile
        path: root.home + "/.config/hyprtk-bar-qt/config.json"
        watchChanges: true
        blockLoading: true
        printErrors: false
        onLoaded: root._parseCfg()
        onTextChanged: root._parseCfg()
        onFileChanged: reload()
    }
    function _parseCfg() {
        try { root.barCfg = JSON.parse(cfgFile.text()) || ({}); }
        catch (e) { root.barCfg = ({}); }
    }

    Component.onCompleted: { root._parseWal(); root._parseCfg(); }

    // ── helpers ────────────────────────────────────────────────────────
    function isHex(value) {
        return typeof value === "string" && /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(value.trim());
    }
    function hex(value, fallback) {
        return isHex(value) ? value.trim() : fallback;
    }
    function num(value, fallback) {
        return (typeof value === "number" && isFinite(value)) ? value : fallback;
    }
    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a); }

    // ── blocks ─────────────────────────────────────────────────────────
    readonly property var colors: root.wal.colors || ({})
    readonly property var special: root.wal.special || ({})
    readonly property var themeBlock: root.barCfg.theme || ({})
    readonly property var fontBlock: root.barCfg.font || ({})
    readonly property string source:
        (themeBlock.source === "manual" || (root.barCfg.use_pywal === false && !themeBlock.source))
            ? "manual" : "pywal"

    // ── palette ────────────────────────────────────────────────────────
    readonly property color background: root.source === "pywal"
        ? root.hex(root.special.background, "#1e1e2e")
        : root.hex(root.themeBlock.background, "#1e1e2e")
    readonly property color foreground: root.source === "pywal"
        ? root.hex(root.special.foreground, "#e5e7eb")
        : root.hex(root.themeBlock.foreground, "#e5e7eb")
    readonly property color accent: root.source === "pywal"
        ? root.hex(root.colors.color5, root.hex(root.themeBlock.accent, "#c084fc"))
        : root.hex(root.themeBlock.accent, "#c084fc")
    readonly property color accent2: root.hex(root.colors.color6, "#22d3ee")
    readonly property color ok: root.hex(root.colors.color2, "#a6e3a1")
    readonly property color warn: root.hex(root.colors.color3, "#f9e2af")
    readonly property color danger: root.hex(root.colors.color1, "#f38ba8")
    readonly property color info: root.hex(root.colors.color4, "#89b4fa")

    // ── surface ladder ─────────────────────────────────────────────────
    // Blending toward the foreground keeps every step visible on wallpapers
    // where color0 and the background are the same colour.
    function mixBase(base, towards, amount) {
        return Qt.rgba(
            base.r + (towards.r - base.r) * amount,
            base.g + (towards.g - base.g) * amount,
            base.b + (towards.b - base.b) * amount, 1);
    }
    readonly property color bg: root.background
    readonly property color surface0: root.mixBase(root.background, root.foreground, 0.035)
    readonly property color surface1: root.mixBase(root.background, root.foreground, 0.070)
    readonly property color surface2: root.mixBase(root.background, root.foreground, 0.115)
    readonly property color surface3: root.mixBase(root.background, root.foreground, 0.170)
    readonly property color border: root.alpha(root.foreground, 0.10)
    readonly property color borderStrong: root.alpha(root.accent, 0.35)
    readonly property color text: root.foreground
    readonly property color textMuted: root.alpha(root.foreground, 0.68)
    readonly property color textFaint: root.alpha(root.foreground, 0.45)
    readonly property color dim: root.textFaint
    readonly property color textOnAccent: "#000000"
    readonly property color textOnDanger: "#ffffff"
    readonly property color scrim: Qt.rgba(0, 0, 0, 0.35)

    // ── bar-qt dialog tokens ───────────────────────────────────────────
    // These mirror components/TButton, TTextField, TComboBox and the Settings
    // panel in hyprtk-bar-qt so every surface here reads as the same suite.
    readonly property real panelOpacity: Math.max(0.92, root.num(root.barCfg.opacity, 0.92))
    readonly property real panelOpacityStrong: Math.max(0.96, root.num(root.barCfg.opacity, 0.92))
    readonly property int controlHeight: 30
    readonly property int radiusControl: 6
    readonly property int radiusCard: 8
    readonly property color controlFill: root.alpha(root.background, 0.60)
    readonly property color controlBorder: root.alpha(root.accent2, 0.30)
    readonly property color hoverTint: root.alpha(root.accent2, 0.15)
    readonly property color pressTint: root.alpha(root.accent, 0.40)
    readonly property color buttonFill: root.alpha(root.accent2, 0.14)
    readonly property color buttonHover: root.alpha(root.accent2, 0.28)
    readonly property color buttonBorder: root.alpha(root.accent2, 0.35)
    readonly property color cardFill: root.alpha(root.background, 0.42)
    readonly property color cardBorder: root.alpha(root.accent2, 0.15)

    // ── metrics ────────────────────────────────────────────────────────
    readonly property int radiusSm: 8
    readonly property int radiusMd: 12
    readonly property int radiusLg: 14
    readonly property int borderWidth: {
        const value = root.barCfg.border_width;
        return (typeof value === "number" && value > 0) ? Math.min(4, value) : 2;
    }
    readonly property bool borderAnimation: root.themeBlock.border_animation !== false
    readonly property int animationPeriodMs: {
        const block = root.barCfg.animations || ({});
        if (block.mode === "custom")
            return Math.max(200, Math.round(4000 / Math.max(1, block.speed || 15)));
        return block.mode === "low" ? 3200 : 1400;
    }

    readonly property string fontFamily: {
        const value = root.fontBlock.family;
        return (typeof value === "string" && value.length > 0) ? value : "Noto Sans";
    }
    readonly property int fontSize: {
        const value = root.fontBlock.size;
        return (typeof value === "number" && value >= 8 && value <= 24) ? value : 12;
    }
    readonly property string monoFamily: "JetBrainsMono Nerd Font Mono"
    readonly property string iconFont: "Symbols Nerd Font"

    function size(step) {
        // 0: 10, 1: 11, 2: 12, 3: 13, 4: 15, 5: 18, 6: 22
        const ladder = [10, 11, 12, 13, 15, 18, 22];
        const index = Math.max(0, Math.min(ladder.length - 1, step || 0));
        return Math.max(9, Math.round(ladder[index] * root.fontSize / 12));
    }

    readonly property int gapXs: 4
    readonly property int gapSm: 8
    readonly property int gapMd: 12
    readonly property int gapLg: 16
    readonly property int gapXl: 24
}
