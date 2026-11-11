import QtQuick
import "../theme"

Rectangle {
    id: root

    property bool checked: false

    signal toggled(bool value)

    implicitWidth: 40
    implicitHeight: 22
    radius: 11
    color: root.checked ? Theme.alpha(Theme.accent, 0.65) : Theme.alpha(Theme.foreground, 0.12)
    border.width: 1
    border.color: root.checked ? Theme.accent : Theme.alpha(Theme.foreground, 0.18)

    Rectangle {
        width: 16
        height: 16
        radius: 8
        y: 2
        x: root.checked ? root.width - width - 2 : 2
        color: root.checked ? Theme.foreground : Theme.muted

        Behavior on x {
            NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }
}
