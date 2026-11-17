import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "components"
import "theme/util.js" as Util

Rectangle {
    id: root

    property var actions: []
    property var filtered: []
    property int index: 0

    readonly property var th: Bridge.palette

    signal closed()

    anchors.fill: parent
    z: 450
    visible: false
    color: Util.alpha(root.th.background, 0.55)

    function open(list) {
        root.actions = list || [];
        root.visible = true;
        field.text = "";
        root.reindex();
        field.forceActiveFocus();
    }

    function close() {
        root.visible = false;
        root.closed();
    }

    function reindex() {
        var q = field.text.toLowerCase();
        var out = [];
        for (var i = 0; i < root.actions.length; i++) {
            var action = root.actions[i];
            if (q.length === 0 || action.label.toLowerCase().indexOf(q) >= 0
                || (action.keywords && action.keywords.toLowerCase().indexOf(q) >= 0))
                out.push(action);
        }
        root.filtered = out.slice(0, 60);
        root.index = root.filtered.length > 0 ? 0 : -1;
        list.currentIndex = root.index;
    }

    function run(index) {
        if (index < 0 || index >= root.filtered.length)
            return;
        var action = root.filtered[index];
        root.close();
        if (typeof action.run === "function")
            action.run();
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: card
        width: Math.min(600, root.width - 80)
        height: Math.min(430, root.height - 120)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 90
        radius: 10
        color: root.th.surface
        border.width: 1
        border.color: Util.alpha(root.th.accent, 0.45)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            TextField {
                id: field
                Layout.fillWidth: true
                height: 36
                ContextMenu.menu: EditorMenu { editor: field }
                color: root.th.foreground
                selectionColor: Util.alpha(root.th.accent, 0.4)
                selectedTextColor: root.th.foreground
                font.pixelSize: 14
                leftPadding: 10
                placeholderText: "Type a command…"
                placeholderTextColor: Util.alpha(root.th.muted, 0.75)
                background: Rectangle {
                    radius: 6
                    color: Util.alpha(root.th.background, 0.8)
                    border.width: 1
                    border.color: Util.alpha(root.th.accent, 0.5)
                }
                onTextChanged: root.reindex()
                onAccepted: root.run(root.index)
                Keys.onPressed: function (event) {
                    if (event.key === Qt.Key_Escape) {
                        root.close();
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Down) {
                        root.index = Math.min(root.filtered.length - 1, root.index + 1);
                        list.currentIndex = root.index;
                        list.positionViewAtIndex(root.index, ListView.Contain);
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Up) {
                        root.index = Math.max(0, root.index - 1);
                        list.currentIndex = root.index;
                        list.positionViewAtIndex(root.index, ListView.Contain);
                        event.accepted = true;
                    }
                }
            }

            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 2
                model: root.filtered
                currentIndex: root.index
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    width: list.width
                    height: 34
                    radius: 6
                    color: index === root.index
                        ? Util.alpha(root.th.accent, 0.22)
                        : (rowMouse.containsMouse ? Util.alpha(root.th.surfaceAlt, 0.6) : "transparent")

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: index === root.index ? root.th.accent : root.th.foreground
                        font.pixelSize: 12
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.hint || ""
                        color: root.th.muted
                        font.pixelSize: 10
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: { root.index = index; root.run(index); }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.filtered.length + " command(s)   ·   ↑↓ move   ·   Enter run   ·   Esc close"
                color: Util.alpha(root.th.muted, 0.8)
                font.pixelSize: 10
                horizontalAlignment: Text.AlignRight
            }
        }
    }
}
