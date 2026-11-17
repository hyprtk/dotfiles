import QtQuick
import "../theme/util.js" as Util

Rectangle {
    id: root

    property bool checked: false
    signal toggled()

    readonly property var th: Bridge.palette

    implicitWidth: 38
    implicitHeight: 21
    radius: 11
    color: root.checked ? Util.alpha(root.th.accent, 0.9) : Util.alpha(root.th.surfaceAlt, 0.9)
    border.width: 1
    border.color: root.checked ? Util.alpha(root.th.accent, 0.9) : Util.alpha(root.th.border, 0.8)
    opacity: enabled ? 1.0 : 0.45

    Rectangle {
        width: 15
        height: 15
        radius: 8
        y: 3
        x: root.checked ? root.width - width - 3 : 3
        color: root.th.foreground
        Behavior on x { NumberAnimation { duration: 110; easing.type: Easing.OutQuad } }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled()
    }
}
