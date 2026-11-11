import QtQuick
import "../theme"

Row {
    id: root

    property int value: 0
    property int from: 12
    property int to: 64
    property int step: 2

    signal changed(int value)

    spacing: 6

    IconButton {
        text: "−"
        available: root.value > root.from
        onClicked: root.changed(Math.max(root.from, root.value - root.step))
    }

    Text {
        anchors.verticalCenter: parent.verticalCenter
        width: 30
        horizontalAlignment: Text.AlignHCenter
        text: root.value
        color: Theme.foreground
        font.pixelSize: 12
    }

    IconButton {
        text: "+"
        available: root.value < root.to
        onClicked: root.changed(Math.min(root.to, root.value + root.step))
    }
}
