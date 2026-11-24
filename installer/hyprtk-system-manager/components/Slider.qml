// Slider matching hyprtk-bar-qt/components/TSlider: a dim track, accent fill
// and a 16px accent handle with a background-coloured ring.
import QtQuick
import "../theme"

Item {
    id: root

    property real value: 0
    property real from: 0
    property real to: 100
    property real step: 1
    signal moved(real value)

    implicitWidth: 220
    implicitHeight: 24

    readonly property real ratio:
        (root.to - root.from) !== 0
            ? Math.max(0, Math.min(1, (root.value - root.from) / (root.to - root.from)))
            : 0

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: 4
        radius: 2
        color: Theme.alpha(Theme.dim, 0.30)
    }
    Rectangle {
        anchors.verticalCenter: track.verticalCenter
        width: root.ratio * track.width
        height: 4
        radius: 2
        color: Theme.accent
    }
    Rectangle {
        id: handle
        width: 16
        height: 16
        radius: 8
        color: mouse.pressed ? Theme.accent2 : Theme.accent
        border.width: 2
        border.color: Theme.alpha(Theme.background, 0.9)
        y: (root.height - height) / 2
        x: Math.max(0, Math.min(root.width - width, root.ratio * (root.width - width)))
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        function setFromX(px) {
            const span = root.width - handle.width;
            if (span <= 0)
                return;
            const ratio = Math.max(0, Math.min(1, (px - handle.width / 2) / span));
            let next = root.from + ratio * (root.to - root.from);
            if (root.step > 0)
                next = Math.round(next / root.step) * root.step;
            next = Math.max(root.from, Math.min(root.to, next));
            root.moved(next);
        }
        onPressed: (event) => setFromX(event.x)
        onPositionChanged: (event) => { if (pressed) setFromX(event.x); }
    }
}
