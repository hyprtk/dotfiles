import QtQuick
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string hint: ""
    property bool active: false
    property bool available: true
    property int iconSize: Glyph.size
    property bool showTip: false

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
        font.family: Glyph.family
        font.pixelSize: root.iconSize
    }

    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: if (root.hint.length > 0) tipTimer.restart()
        onExited: {
            tipTimer.stop();
            root.showTip = false;
        }
        onClicked: if (root.available) root.clicked()
    }

    Timer {
        id: tipTimer
        interval: 450
        onTriggered: root.showTip = true
    }

    Rectangle {
        id: tip
        visible: root.showTip
        anchors.top: parent.bottom
        anchors.topMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        width: tipLabel.implicitWidth + 14
        height: tipLabel.implicitHeight + 8
        radius: 5
        color: Theme.alpha(Theme.surfaceAlt, 0.97)
        border.width: 1
        border.color: Theme.alpha(Theme.accent, 0.4)
        z: 200

        Text {
            id: tipLabel
            anchors.centerIn: parent
            text: root.hint
            color: Theme.foreground
            font.pixelSize: 10
        }
    }
}
