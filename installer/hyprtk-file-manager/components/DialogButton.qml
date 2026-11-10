import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property bool primary: false
    property bool danger: false

    signal clicked()

    implicitWidth: 96
    implicitHeight: 30
    radius: 6
    color: root.primary ? Theme.alpha(Theme.accent, 0.35)
        : (root.danger ? Theme.alpha(Theme.danger, 0.28) : Theme.alpha(Theme.foreground, 0.08))

    Text {
        anchors.centerIn: parent
        text: root.text
        color: Theme.foreground
        font.pixelSize: 11
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
