// Themed toggle switch (accent fill, bar palette).
import QtQuick
import "../theme"

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: 44
    implicitHeight: 24
    radius: 12
    color: checked ? Theme.accent : Theme.alpha(Theme.background, 0.6)
    border.width: 1
    border.color: checked ? Theme.accent : Theme.alpha(Theme.accent2, 0.5)

    Rectangle {
        width: 18
        height: 18
        radius: 9
        y: (root.height - height) / 2
        x: root.checked ? root.width - width - 3 : 3
        color: root.checked ? Theme.textOnAccent : Theme.dim
        Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: { root.checked = !root.checked; root.toggled(root.checked); }
    }
}
