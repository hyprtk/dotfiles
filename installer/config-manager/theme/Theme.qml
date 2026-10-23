// hyprtk theme — resolves the same tokens as hyprtk-bar-qt:
//   1. hyprtk-bar-qt's theme block in ~/.config/hyprtk-bar-qt/config.json
//   2. live pywal (~/.cache/wal/colors.json)
//   3. hyprtk fallbacks
//
// The settings window therefore follows wallpaper changes, manual theme
// overrides, opacity, border width and border-animation state set in the bar.
pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    readonly property string home: Quickshell.env("HOME") || ""

    function num(v, fallback) {
        return (typeof v === "number" && isFinite(v)) ? v : fallback;
    }
    function pick(v, fallback) {
        return (typeof v === "string" && v.trim().length > 0) ? v : fallback;
    }

    // ── live pywal palette ─────────────────────────────────────────────
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
        try {
            root.wal = JSON.parse(walFile.text()) || ({});
        } catch (e) {
            root.wal = ({});
        }
    }

    // ── bar config (theme, opacity, font, animations) ──────────────────
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
        try {
            root.barCfg = JSON.parse(cfgFile.text()) || ({});
        } catch (e) {
            root.barCfg = ({});
        }
    }

    Component.onCompleted: {
        root._parseWal();
        root._parseCfg();
    }

    readonly property var colors: root.wal.colors || ({})
    readonly property var special: root.wal.special || ({})
    readonly property var themeBlock: root.barCfg.theme || ({})
    readonly property var fontBlock: root.barCfg.font || ({})
    readonly property var animBlock: root.barCfg.animations || ({})

    // `theme.source` wins; the legacy `use_pywal` flag seeds the default.
    readonly property string source: pick(root.themeBlock.source,
        root.barCfg.use_pywal === false ? "manual" : "pywal")

    // ── core palette (identical resolution to hyprtk-bar-qt) ───────────
    readonly property color background: root.source === "pywal"
        ? pick(root.special.background, "#1e1e2e")
        : pick(root.themeBlock.background, "#1e1e2e")
    readonly property color foreground: root.source === "pywal"
        ? pick(root.special.foreground, "#e5e7eb")
        : pick(root.themeBlock.foreground, "#e5e7eb")
    readonly property color accent: root.source === "pywal"
        ? pick(root.colors.color5, pick(root.colors.color4, "#c084fc"))
        : pick(root.themeBlock.accent, "#c084fc")
    readonly property color accent2: pick(root.colors.color6, "#22d3ee")
    readonly property color dim: pick(root.colors.color8, "#6b7280")
    readonly property color err: pick(root.colors.color1, "#f38ba8")
    readonly property color warn: pick(root.colors.color3, "#f9e2af")
    readonly property color textOnAccent: "#000000"
    readonly property color textOnDanger: "#ffffff"
    readonly property color scrim: Qt.rgba(0, 0, 0, 0.35)

    readonly property real opacity: root.num(root.barCfg.opacity, 0.92)
    readonly property real panelOpacity: Math.max(0.92, root.opacity)
    readonly property real panelOpacityStrong: Math.max(0.96, root.opacity)

    // ── chrome ─────────────────────────────────────────────────────────
    readonly property int radiusPanel: 14
    readonly property int radiusPopup: 10
    readonly property int borderWidth: root.num(root.barCfg.border_width, 2)
    readonly property bool borderAnimation: root.themeBlock.border_animation !== false
    readonly property int animationPeriodMs: {
        const mode = root.animBlock.mode || "high";
        if (mode === "custom")
            return Math.max(200, Math.round(4000 / Math.max(1, root.animBlock.speed || 15)));
        return mode === "low" ? 3200 : 1400;
    }
    readonly property real hoverAlpha: 0.15
    readonly property real pressedAlpha: 0.40
    readonly property real borderAlpha: 0.30

    readonly property string fontFamily: pick(root.fontBlock.family, "Noto Sans")
    readonly property int fontSize: root.num(root.fontBlock.size, 12)

    function scaled(n, fallback) {
        const base = root.fontSize > 0 ? root.fontSize : (fallback || 12);
        return Math.max(1, Math.round((n || 0) * base / 12));
    }

    // Translucent variant of a colour (alpha 0..1), for surface tints.
    function alpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a);
    }

    // pywal palette colour by index (1..16).
    function walColor(n, fallback) {
        const c = root.colors ? root.colors["color" + n] : undefined;
        return (typeof c === "string" && c.length > 0) ? c : fallback;
    }

    // ── aliases used across the app ────────────────────────────────────
    readonly property color text: root.foreground
    readonly property color panel: root.background
    readonly property color card: root.alpha(root.background, 0.42)
    readonly property color border: root.alpha(root.accent2, 0.15)
    readonly property color danger: root.err
    readonly property int radius: root.radiusPanel
    readonly property int pad: 16
    readonly property int controlHeight: 32
    readonly property int controlWidth: 200
    readonly property int rowSpacing: 8
}
