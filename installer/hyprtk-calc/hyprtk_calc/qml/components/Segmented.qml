import QtQuick
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// A small segmented control: one selected value, a signal on change. Used for
// the mode tabs and for the settings rows, so both read the same.
Item {
    id: seg

    property var th: null
    property var options: []          // [{ value, label }]
    property string value: ""
    property real fontScale: 1.0

    signal picked(string value)

    implicitHeight: 30 * fontScale
    implicitWidth: row.implicitWidth

    Rectangle {
        anchors.fill: parent
        radius: 9
        color: seg.th ? seg.th.key_alt : "#141620"
        border.width: 1
        border.color: Util.alpha(seg.th ? seg.th.foreground : "#ffffff", 0.07)
    }

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.margins: 3
        spacing: 3

        Repeater {
            model: seg.options

            delegate: Item {
                id: cell

                required property var modelData

                Layout.fillWidth: true
                Layout.fillHeight: true

                Rectangle {
                    anchors.fill: parent
                    radius: 7
                    color: seg.value === cell.modelData.value
                           ? Util.alpha(seg.th ? seg.th.accent : "#c084fc", 0.9)
                           : (hover.containsMouse
                              ? Util.alpha(seg.th ? seg.th.foreground : "#ffffff", 0.08)
                              : "transparent")
                    Behavior on color { ColorAnimation { duration: 110 } }
                }

                Text {
                    anchors.centerIn: parent
                    text: cell.modelData.label
                    font.pixelSize: 11.5 * seg.fontScale
                    font.weight: seg.value === cell.modelData.value ? Font.DemiBold : Font.Normal
                    color: seg.value === cell.modelData.value
                           ? (seg.th ? seg.th.text_on_accent : "#11111b")
                           : (seg.th ? seg.th.muted : "#a6adc8")
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (seg.value !== cell.modelData.value) {
                            seg.value = cell.modelData.value;
                            seg.picked(cell.modelData.value);
                        }
                    }
                }
            }
        }
    }
}
