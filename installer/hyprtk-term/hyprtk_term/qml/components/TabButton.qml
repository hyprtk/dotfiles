import QtQuick
import "../theme"
import "../theme/util.js" as Util

// One tab in the strip: dot, title, close affordance. The strip itself lives in
// Main.qml because it also owns the "+" button and the empty-space drag area.
Rectangle {
    id: tab

    property var theme
    property string monoFamily: "monospace"
    property string label: "Terminal"
    property bool active: false
    property bool alerted: false
    signal activated()
    signal closed()

    height: 28
    width: Math.max(104, Math.min(240, titleText.implicitWidth + 58))
    radius: 7
    color: active ? Util.alpha(theme.surface_alt, 0.95)
                  : (mouse.containsMouse ? Util.alpha(theme.surface, 0.85) : "transparent")
    border.width: active ? 1 : 0
    border.color: Util.alpha(theme.border, 0.55)

    Behavior on color { ColorAnimation { duration: 90 } }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 6
        spacing: 7

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Glyph.dot
            font.family: Glyph.family
            font.pixelSize: 7
            color: tab.alerted ? theme.warning : (tab.active ? theme.accent : Util.alpha(theme.muted, 0.7))
        }

        Text {
            id: titleText
            anchors.verticalCenter: parent.verticalCenter
            width: tab.width - 64
            text: Util.shortTitle(tab.label)
            elide: Text.ElideRight
            font.family: tab.monoFamily
            font.pixelSize: 11
            color: tab.active ? theme.foreground : Util.alpha(theme.foreground, 0.72)
        }
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 7
        anchors.verticalCenter: parent.verticalCenter
        text: Glyph.close
        font.family: Glyph.family
        font.pixelSize: 9
        color: closeArea.containsMouse ? theme.danger : Util.alpha(theme.muted, 0.85)
        opacity: tab.active || closeArea.containsMouse ? 1 : 0
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        hoverEnabled: true
        onClicked: function (e) {
            if (e.button === Qt.MiddleButton)
                tab.closed();
            else
                tab.activated();
        }
    }

    MouseArea {
        id: closeArea
        width: 18
        height: 18
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        hoverEnabled: true
        onClicked: tab.closed()
    }
}
