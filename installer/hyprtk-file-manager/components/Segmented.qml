import QtQuick
import "../theme"

Row {
    id: root

    property var options: []
    property string current: ""

    signal selected(string value)

    spacing: 4

    Repeater {
        model: root.options

        delegate: Rectangle {
            required property var modelData

            width: Math.max(52, label.implicitWidth + 20)
            height: 26
            radius: 6
            color: modelData.value === root.current
                ? Theme.alpha(Theme.accent, 0.3)
                : (segHover.hovered ? Theme.alpha(Theme.foreground, 0.08) : "transparent")
            border.width: 1
            border.color: modelData.value === root.current
                ? Theme.accent : Theme.alpha(Theme.foreground, 0.12)

            Text {
                id: label
                anchors.centerIn: parent
                text: modelData.label
                color: Theme.foreground
                font.pixelSize: 11
            }

            MouseArea {
                id: segHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.selected(modelData.value)
            }
        }
    }
}
