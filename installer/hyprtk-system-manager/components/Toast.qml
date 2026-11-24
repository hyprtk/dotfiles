// Transient status line in the bar's tooltip/popup language.
import QtQuick
import "../theme"

Rectangle {
    id: toast

    property string message: ""
    property string tone: "info"

    readonly property color tint:
        tone === "danger" ? Theme.danger :
        tone === "warn" ? Theme.warn :
        tone === "ok" ? Theme.ok : Theme.accent

    function show(text, toneName) {
        toast.message = text;
        toast.tone = toneName || "info";
        toast.opacity = 1;
        timer.restart();
    }

    width: Math.min(560, text.implicitWidth + 32)
    height: 34
    radius: Theme.radiusControl
    color: Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b,
                   Theme.panelOpacityStrong)
    border.width: 1
    border.color: Theme.alpha(toast.tint, 0.45)
    opacity: 0
    visible: opacity > 0.01
    z: 950

    Behavior on opacity { NumberAnimation { duration: 160 } }

    Row {
        anchors.centerIn: parent
        spacing: 8
        Rectangle { width: 7; height: 7; radius: 3.5; color: toast.tint; anchors.verticalCenter: parent.verticalCenter }
        Text {
            id: text
            anchors.verticalCenter: parent.verticalCenter
            text: toast.message
            color: Theme.foreground
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            elide: Text.ElideRight
            width: Math.min(implicitWidth, 500)
        }
    }

    Timer {
        id: timer
        interval: 4200
        onTriggered: toast.opacity = 0
    }
}
