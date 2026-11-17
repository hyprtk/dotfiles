import QtQuick
import "../theme/util.js" as Util

Rectangle {
    id: root

    property string message: ""
    property string level: "info"

    readonly property var th: Bridge.palette

    width: Math.min(parent ? parent.width - 80 : 520, textLabel.implicitWidth + 36)
    height: 38
    radius: 8
    visible: opacity > 0
    opacity: 0
    z: 500
    color: Util.alpha(root.th.surfaceAlt, 0.98)
    border.width: 1
    border.color: root.level === "error"
        ? Util.alpha(root.th.danger, 0.8)
        : Util.alpha(root.th.accent, 0.55)

    function show(text, kind) {
        root.message = text;
        root.level = kind || "info";
        root.opacity = 1;
        hideTimer.restart();
    }

    Text {
        id: textLabel
        anchors.centerIn: parent
        width: Math.min(implicitWidth, root.width - 30)
        text: root.message
        color: root.level === "error" ? root.th.danger : root.th.foreground
        font.pixelSize: 12
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
    }

    Behavior on opacity { NumberAnimation { duration: 140 } }

    Timer {
        id: hideTimer
        interval: 3200
        onTriggered: root.opacity = 0
    }
}
