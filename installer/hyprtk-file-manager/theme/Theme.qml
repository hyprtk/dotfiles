pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    readonly property string home:
        Quickshell.env("HYPRTK_WAL_HOME") || Quickshell.env("HOME") || ""
    property var wal: ({})

    FileView {
        id: walFile
        path: root.home + "/.cache/wal/colors.json"
        watchChanges: true
        blockLoading: true
        printErrors: false
        onLoaded: root._parse()
        onTextChanged: root._parse()
        onFileChanged: reload()
    }

    function _parse() {
        try {
            root.wal = JSON.parse(walFile.text()) || ({});
        } catch (e) {
            root.wal = ({});
        }
    }

    Component.onCompleted: root._parse()

    readonly property var palette: root.wal.colors || ({})
    readonly property var special: root.wal.special || ({})

    readonly property color background: root.special.background || "#1e1e2e"
    readonly property color foreground: root.special.foreground || "#cdd6f4"
    readonly property color surface: root.palette.color0 || "#313244"
    readonly property color surfaceAlt: root.palette.color8 || "#45475a"
    readonly property color muted: root.palette.color7 || "#a6adc8"
    readonly property color accent: root.palette.color5 || "#c084fc"
    readonly property color accent2: root.palette.color6 || "#22d3ee"
    readonly property color danger: root.palette.color1 || "#f38ba8"
    readonly property color textOnAccent: root.palette.color0 || "#11111b"

    // Status tones + dialog tokens shared with the rest of the suite
    // (hyprtk-system-manager / bar-qt call these the same names).
    readonly property color dim: root.alpha(root.foreground, 0.45)
    readonly property color warn: root.palette.color3 || "#f9e2af"
    readonly property color ok: root.palette.color2 || "#a6e3a1"
    readonly property color info: root.palette.color4 || "#89b4fa"
    readonly property color controlFill: root.alpha(root.background, 0.60)
    readonly property color controlBorder: root.alpha(root.accent2, 0.30)
    readonly property color rowHover: root.alpha(root.accent2, 0.12)

    readonly property int radius: 8
    readonly property int radiusLg: 14
    readonly property int fontSize: 12
    readonly property string fontFamily: "Noto Sans"

    function size(step) {
        // 0: 10, 1: 11, 2: 12, 3: 13, 4: 15, 5: 18, 6: 22
        const ladder = [10, 11, 12, 13, 15, 18, 22];
        const index = Math.max(0, Math.min(ladder.length - 1, step || 0));
        return Math.max(9, Math.round(ladder[index] * root.fontSize / 12));
    }

    // Request full-color icon variants; Papirus only colors folders at 22px+.
    readonly property int iconSource: 64

    // Bumped whenever papirus-folders rewrites the folder-colour symlinks
    // (wallpaper hook or the bar's Icons page). Qt caches themed icon pixmaps
    // by name and never sees the underlying file change, so views re-resolve
    // their icon names when this changes.
    property int iconEpoch: 0

    FileView {
        id: papirusState
        path: root.home + "/.config/papirus-folders.sh/keep"
        watchChanges: true
        printErrors: false
        onLoaded: root.iconEpoch += 1
        onTextChanged: root.iconEpoch += 1
        onFileChanged: reload()
    }

    function alpha(color, value) {
        return Qt.rgba(color.r, color.g, color.b, value);
    }
}
