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

    readonly property int radius: 8
    readonly property int fontSize: 12

    // Request full-color icon variants; Papirus only colors folders at 22px+.
    readonly property int iconSource: 64

    function alpha(color, value) {
        return Qt.rgba(color.r, color.g, color.b, value);
    }
}
