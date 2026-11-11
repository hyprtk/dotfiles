import QtQuick
import "../theme"

Item {
    id: root

    property string label: ""
    property string hint: ""

    default property alias content: slot.data

    implicitHeight: root.hint.length > 0 ? 46 : 34

    Column {
        anchors.left: parent.left
        anchors.right: slot.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1

        Text {
            text: root.label
            color: Theme.foreground
            font.pixelSize: 12
        }

        Text {
            visible: root.hint.length > 0
            width: parent.width
            text: root.hint
            color: Theme.muted
            font.pixelSize: 10
            elide: Text.ElideRight
        }
    }

    Row {
        id: slot
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
    }
}
