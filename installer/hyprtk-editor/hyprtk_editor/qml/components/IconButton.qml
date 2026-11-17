import QtQuick
import "../theme"
import "../theme/util.js" as Util

Rectangle {
    id: root

    property string glyph: ""
    property string hint: ""
    property bool active: false
    property int size: 28
    signal clicked()

    readonly property var th: Bridge.palette

    implicitWidth: size
    implicitHeight: size
    radius: 6
    color: root.active
        ? Util.alpha(root.th.accent, 0.26)
        : (hover.containsMouse ? Util.alpha(root.th.accent2, 0.14) : "transparent")
    opacity: enabled ? 1.0 : 0.4

    Text {
        anchors.centerIn: parent
        text: root.glyph
        color: root.active ? root.th.accent : root.th.muted
        font.family: Glyph.family
        font.pixelSize: Glyph.size
    }

    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Rectangle {
        id: tip
        visible: hover.containsMouse && root.hint.length > 0
        anchors.top: parent.bottom
        anchors.topMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        width: tipText.implicitWidth + 14
        height: tipText.implicitHeight + 8
        radius: 5
        color: Util.alpha(root.th.surfaceAlt, 0.98)
        border.width: 1
        border.color: Util.alpha(root.th.border, 0.7)
        z: 50
        Text {
            id: tipText
            anchors.centerIn: parent
            text: root.hint
            color: root.th.foreground
            font.pixelSize: 11
        }
    }
}
