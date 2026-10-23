// Themed push button (matches hyprtk-bar-qt's button surfaces).
import QtQuick
import "../theme"

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property bool enabled: true
    signal clicked()

    implicitWidth: label.implicitWidth + 28
    implicitHeight: Theme.controlHeight
    radius: 8
    color: !enabled ? Theme.alpha(Theme.dim, 0.08)
         : primary ? (pressedArea.pressed ? Theme.accent : Theme.alpha(Theme.accent, 0.85))
         : pressedArea.pressed ? Theme.alpha(Theme.accent, Theme.pressedAlpha)
         : hover.hovered ? Theme.alpha(Theme.accent2, 0.28)
         : Theme.alpha(Theme.accent2, 0.14)
    border.width: 1
    border.color: primary ? "transparent" : Theme.alpha(Theme.accent2, enabled ? 0.35 : 0.15)
    opacity: enabled ? 1 : 0.6

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.primary ? Theme.textOnAccent : Theme.foreground
        font.pixelSize: Theme.scaled(12)
        font.bold: root.primary
    }
    HoverHandler { id: hover }
    MouseArea {
        id: pressedArea
        anchors.fill: parent
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
