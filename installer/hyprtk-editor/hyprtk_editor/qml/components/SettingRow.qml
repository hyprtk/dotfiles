import QtQuick
import QtQuick.Layouts
import "../theme/util.js" as Util

Rectangle {
    id: root

    property string label: ""
    property string hint: ""
    default property alias content: slot.data

    readonly property var th: Bridge.palette

    implicitHeight: Math.max(42, textColumn.implicitHeight + 14)
    color: "transparent"
    radius: 6

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Column {
            id: textColumn
            Layout.fillWidth: true
            spacing: 2
            Text {
                text: root.label
                color: root.th.foreground
                font.pixelSize: 12
            }
            Text {
                visible: root.hint.length > 0
                text: root.hint
                color: Util.alpha(root.th.muted, 0.85)
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                width: textColumn.width
            }
        }

        RowLayout {
            id: slot
            Layout.alignment: Qt.AlignVCenter
            spacing: 6
        }
    }
}
