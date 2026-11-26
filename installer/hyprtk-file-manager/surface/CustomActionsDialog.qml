// User-defined actions from ~/.config/hyprtk-file-manager/actions/*.json.
import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property var paths: []
    property var actions: []
    property string actionsDir: ""
    property string status: ""
    property int listId: -1
    property int runId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 241
    focus: visible

    function open(paths) {
        root.paths = Array.prototype.slice.call(paths || [], 0);
        root.status = "";
        root.visible = true;
        root.listId = Backend.call("actions.list", {});
    }

    function run(action) {
        root.runId = Backend.call("actions.run", {
            id: action.id,
            paths: root.paths,
            dir: root.paths.length > 0
                ? root.paths[0].substring(0, root.paths[0].lastIndexOf("/"))
                : "",
        });
    }

    function dismiss() {
        root.visible = false;
        root.listId = -1;
        root.runId = -1;
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === root.listId) {
                root.listId = -1;
                root.actions = (result && result.actions) || [];
                root.actionsDir = (result && result.dir) || "";
            } else if (id === root.runId) {
                root.runId = -1;
                root.status = "Started " + ((result && result.id) || "the action");
            }
        }
        function onFailure(id, message) {
            if (id === root.listId || id === root.runId) {
                root.listId = -1;
                root.runId = -1;
                root.status = message;
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45
        MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(640, parent.width - 80)
        height: Math.min(500, parent.height - 80)
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            Text {
                text: "Custom actions — " + root.paths.length + " selected"
                color: Theme.accent
                font.pixelSize: Theme.size(4)
                font.bold: true
            }

            ListView {
                width: parent.width
                height: parent.height - 120
                clip: true
                model: root.actions
                spacing: 2

                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 44
                    radius: 5
                    color: area.containsMouse ? Theme.rowHover : "transparent"

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            text: modelData.name
                            color: Theme.foreground
                            font.pixelSize: Theme.size(2)
                        }
                        Text {
                            text: modelData.description || modelData.command
                            color: Theme.dim
                            font.pixelSize: Theme.size(0)
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.run(modelData)
                    }
                }
            }

            Text {
                width: parent.width
                text: root.actions.length === 0 && root.listId < 0
                    ? "No actions yet. Drop a JSON file in " + root.actionsDir +
                      ' — e.g. {"name": "Optimise PNGs", "command": "optipng -quiet \\"$@\\""}'
                    : root.status
                color: Theme.dim
                font.pixelSize: Theme.size(1)
                wrapMode: Text.WordWrap
            }

            DialogButton { text: "Close"; onClicked: root.dismiss() }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
