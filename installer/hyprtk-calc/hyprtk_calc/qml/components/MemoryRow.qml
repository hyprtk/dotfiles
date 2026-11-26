import QtQuick
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// Memory and `ans` strip above the keypad: MC / MR / M+ / M- / MS plus the last
// answer as a token. Sits outside CalcKey because those keys are 50px tall and
// this row is deliberately small.
RowLayout {
    id: row

    property var th: null
    property string mono: "monospace"
    property real fontScale: 1.0
    property bool set: false            // memory holds a value
    property string memoryText: ""      // shown when set
    property string ansText: ""         // the last result, for the tooltip

    signal action(string name)          // clear | recall | add | subtract | store
    signal ansRequested()

    spacing: 6

    readonly property color accent: row.th ? row.th.accent : "#c084fc"
    readonly property color fg: row.th ? row.th.foreground : "#e5e7eb"
    readonly property color dim: row.th ? row.th.dim : "#8b8fa3"

    Repeater {
        model: [
            { label: "MC", name: "clear", tip: "Clear the memory" },
            { label: "MR", name: "recall", tip: "Recall the memory" },
            { label: "M+", name: "add", tip: "Add the last result to the memory" },
            { label: "M−", name: "subtract", tip: "Subtract the last result from the memory" },
            { label: "MS", name: "store", tip: "Store the last result in the memory" }
        ]

        delegate: Rectangle {
            id: key
            required property var modelData

            Layout.fillWidth: true
            Layout.preferredHeight: 26 * row.fontScale
            radius: 8
            color: mouse.containsMouse
                   ? Util.alpha(row.accent, 0.18)
                   : (row.th ? row.th.key_alt : "#141620")
            border.width: 1
            border.color: Util.alpha(row.accent, key.usable ? 0.22 : 0.08)
            opacity: key.usable ? 1.0 : 0.45

            // MC/MR only mean something when there is a value to recall.
            // Named `usable`: `enabled` is already a QQuickItem property.
            readonly property bool usable:
                (key.modelData.name === "clear" || key.modelData.name === "recall")
                ? row.set : true

            Text {
                anchors.centerIn: parent
                text: key.modelData.label
                color: row.fg
                font.pixelSize: 10.5 * row.fontScale
                font.weight: Font.DemiBold
                font.family: row.mono
            }

            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                enabled: key.usable
                onClicked: row.action(key.modelData.name)
            }
        }
    }

    // `ans` — the previous result, as a token you can click instead of retyping.
    Rectangle {
        id: ansKey

        Layout.preferredWidth: 62 * row.fontScale
        Layout.preferredHeight: 26 * row.fontScale
        radius: 8
        color: ansMouse.containsMouse
               ? Util.alpha(row.accent, 0.24)
               : Util.alpha(row.accent, 0.12)
        border.width: 1
        border.color: Util.alpha(row.accent, row.ansText.length ? 0.35 : 0.1)
        opacity: row.ansText.length ? 1.0 : 0.45

        Text {
            anchors.centerIn: parent
            text: "ans"
            color: row.accent
            font.pixelSize: 10.5 * row.fontScale
            font.weight: Font.DemiBold
            font.family: row.mono
        }

        MouseArea {
            id: ansMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            enabled: row.ansText.length > 0
            onClicked: row.ansRequested()
        }
    }

    // What is in the memory, when there is something to show.
    Text {
        Layout.fillWidth: true
        Layout.leftMargin: 2
        text: row.set ? "M " + row.memoryText : ""
        elide: Text.ElideLeft
        horizontalAlignment: Text.AlignRight
        color: row.dim
        font.pixelSize: 10 * row.fontScale
        font.family: row.mono
    }
}
