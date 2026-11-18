import QtQuick
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// Settings sheet: every control writes through Bridge.setConfig, which
// validates and persists, so there is no second source of truth in QML.
Rectangle {
    id: sheet

    property var th: null
    property var cfg: ({})
    property string version: ""
    property real fontScale: 1.0

    readonly property real contentHeight: content.implicitHeight + 32

    signal closed()

    radius: 16
    color: sheet.th ? sheet.th.display : "#12141e"
    border.width: 1
    border.color: Util.alpha(sheet.th ? sheet.th.foreground : "#ffffff", 0.12)

    component SettingRow: ColumnLayout {
        id: settingRow

        property string label: ""
        property string hint: ""
        default property alias control: holder.data

        Layout.fillWidth: true
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                Text {
                    text: settingRow.label
                    font.pixelSize: 12 * sheet.fontScale
                    color: sheet.th ? sheet.th.foreground : "#e5e7eb"
                }

                Text {
                    text: settingRow.hint
                    visible: settingRow.hint.length > 0
                    font.pixelSize: 10 * sheet.fontScale
                    color: sheet.th ? sheet.th.dim : "#6e7075"
                }
            }

            RowLayout {
                id: holder
                spacing: 4
            }
        }
    }

    component Toggle: Rectangle {
        id: toggle

        property bool on: false
        signal toggled(bool on)

        implicitWidth: 40
        implicitHeight: 22
        radius: 11
        color: toggle.on
               ? Util.alpha(sheet.th ? sheet.th.accent : "#c084fc", 0.9)
               : Util.alpha(sheet.th ? sheet.th.foreground : "#ffffff", 0.16)

        Behavior on color { ColorAnimation { duration: 120 } }

        Rectangle {
            width: 16
            height: 16
            radius: 8
            y: 3
            x: toggle.on ? parent.width - 19 : 3
            color: toggle.on ? (sheet.th ? sheet.th.text_on_accent : "#11111b")
                             : (sheet.th ? sheet.th.muted : "#a6adc8")
            Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: toggle.toggled(!toggle.on)
        }
    }

    component Stepper: RowLayout {
        id: stepper

        property int value: 12
        property int low: 3
        property int high: 30
        signal stepped(int value)

        spacing: 2

        IconButton {
            th: sheet.th
            glyph: "\u2212"
            enabled: stepper.value > stepper.low
            onClicked: stepper.stepped(Math.max(stepper.low, stepper.value - 1))
        }

        Text {
            text: stepper.value
            horizontalAlignment: Text.AlignHCenter
            Layout.preferredWidth: 26
            font.pixelSize: 12 * sheet.fontScale
            font.weight: Font.DemiBold
            color: sheet.th ? sheet.th.foreground : "#e5e7eb"
        }

        IconButton {
            th: sheet.th
            glyph: "+"
            enabled: stepper.value < stepper.high
            onClicked: stepper.stepped(Math.min(stepper.high, stepper.value + 1))
        }
    }

    component ActionLink: Text {
        id: link

        signal clicked()

        font.pixelSize: 11 * sheet.fontScale
        color: hover.containsMouse
               ? (sheet.th ? sheet.th.foreground : "#e5e7eb")
               : (sheet.th ? sheet.th.muted : "#a6adc8")

        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: link.clicked()
        }
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "Settings"
                font.pixelSize: 14 * sheet.fontScale
                font.weight: Font.DemiBold
                color: sheet.th ? sheet.th.foreground : "#e5e7eb"
                Layout.fillWidth: true
            }

            IconButton {
                th: sheet.th
                glyph: Glyph.close
                onClicked: sheet.closed()
            }
        }

        SettingRow {
            label: "Significant digits"
            hint: "what the result line shows"

            Stepper {
                value: sheet.cfg.precision || 12
                low: 3
                high: 30
                onStepped: function (value) { Bridge.setConfig("precision", value) }
            }
        }

        SettingRow {
            label: "Angle unit"

            Segmented {
                th: sheet.th
                fontScale: sheet.fontScale
                implicitWidth: 150
                options: [
                    { value: "deg", label: "DEG" },
                    { value: "rad", label: "RAD" },
                    { value: "grad", label: "GRAD" }
                ]
                value: sheet.cfg.angle || "deg"
                onPicked: function (mode) { Bridge.setConfig("angle", mode) }
            }
        }

        SettingRow {
            label: "Digit grouping"

            Segmented {
                th: sheet.th
                fontScale: sheet.fontScale
                implicitWidth: 180
                options: [
                    { value: "none", label: "None" },
                    { value: "thin", label: "1 000" },
                    { value: "comma", label: "1,000" }
                ]
                value: sheet.cfg.grouping || "none"
                onPicked: function (mode) { Bridge.setConfig("grouping", mode) }
            }
        }

        SettingRow {
            label: "Keypad"

            Segmented {
                th: sheet.th
                fontScale: sheet.fontScale
                implicitWidth: 190
                options: [
                    { value: "basic", label: "Basic" },
                    { value: "scientific", label: "Sci" },
                    { value: "programmer", label: "Prog" }
                ]
                value: sheet.cfg.keypad || "basic"
                onPicked: function (mode) { Bridge.setConfig("keypad", mode) }
            }
        }

        SettingRow {
            label: "Live result"
            hint: "evaluate while typing"

            Toggle {
                on: sheet.cfg.live !== false
                onToggled: function (on) { Bridge.setConfig("live", on) }
            }
        }

        SettingRow {
            label: "Always on top"

            Toggle {
                on: sheet.cfg.always_on_top === true
                onToggled: function (on) { Bridge.setConfig("always_on_top", on) }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Util.alpha(sheet.th ? sheet.th.foreground : "#ffffff", 0.08)
        }

        RowLayout {
            Layout.fillWidth: true

            Text {
                Layout.fillWidth: true
                text: "hyprtk-calc " + sheet.version
                font.pixelSize: 11 * sheet.fontScale
                color: sheet.th ? sheet.th.dim : "#6e7075"
            }

            ActionLink {
                text: "Clear history"
                onClicked: Bridge.clearHistory()
            }
        }
    }
}
