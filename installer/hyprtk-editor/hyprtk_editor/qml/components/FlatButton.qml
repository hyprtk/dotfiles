import QtQuick
import "../theme"
import "../theme/util.js" as Util

Rectangle {
    id: root

    property string text: ""
    property bool active: false
    property bool danger: false
    property string hint: ""
    signal clicked()

    readonly property var th: Bridge.palette

    implicitWidth: label.implicitWidth + 22
    implicitHeight: 28
    radius: 6
    color: root.active
        ? Util.alpha(root.th.accent, 0.24)
        : (hover.containsMouse ? Util.alpha(root.th.surfaceAlt, 0.7) : "transparent")
    opacity: enabled ? 1.0 : 0.42
    border.width: root.active ? 1 : 0
    border.color: Util.alpha(root.th.accent, 0.5)

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.danger ? root.th.danger
            : (root.active ? root.th.accent : root.th.foreground)
        font.pixelSize: 12
        font.weight: root.active ? 600 : 400
    }

    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
