import QtQuick
import "../theme"

Item {
    id: root

    property var items: []
    property bool opened: false

    visible: opened
    z: 100
    width: 190
    height: column.height + 10

    function openAt(px, py) {
        root.x = Math.max(4, Math.min(px, root.parent.width - root.width - 4));
        root.y = Math.max(4, Math.min(py, root.parent.height - root.height - 4));
        root.opened = true;
    }

    function close() {
        root.opened = false;
    }

    Rectangle {
        anchors.fill: parent
        radius: 8
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)
    }

    Column {
        id: column
        x: 5
        y: 5
        width: parent.width - 10

        Repeater {
            model: root.items

            delegate: Rectangle {
                required property var modelData
                width: column.width
                height: 28
                radius: 5
                opacity: modelData.enabled === false ? 0.4 : 1
                color: itemHover.hovered && modelData.enabled !== false
                    ? Theme.alpha(Theme.accent, 0.2) : "transparent"

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: Theme.foreground
                    font.pixelSize: 12
                }

                MouseArea {
                    id: itemHover
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: modelData.enabled !== false
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.close();
                        if (modelData.action)
                            modelData.action();
                    }
                }
            }
        }
    }
}
