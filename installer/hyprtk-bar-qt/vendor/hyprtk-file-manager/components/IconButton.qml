import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property bool active: false
    property bool available: true

    signal clicked()

    implicitWidth: 30
    implicitHeight: 28
    radius: 6

    color: root.active ? Theme.alpha(Theme.accent, 0.28)
        : (hover.hovered && root.available ? Theme.alpha(Theme.accent2, 0.16) : "transparent")
    opacity: root.available ? 1.0 : 0.4

    Text {
        anchors.centerIn: parent
        text: root.text
        color: root.active ? Theme.foreground : Theme.muted
        font.pixelSize: 14
    }

    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (root.available) root.clicked()
    }
}
