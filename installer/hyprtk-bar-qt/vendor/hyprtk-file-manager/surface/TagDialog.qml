// Tag / colour label editor for one or more paths.
import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property var paths: []
    property string tagsText: ""
    property string color: ""
    property string status: ""
    property int setId: -1
    property int loadId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 240
    focus: visible

    readonly property var colors: ["", "#fd4fb6", "#02dede", "#5fb8f5",
                                   "#f5c15f", "#7bd88f", "#c084fc"]

    function open(list) {
        root.paths = Array.prototype.slice.call(list || [], 0);
        root.tagsText = "";
        root.color = "";
        root.status = "";
        root.visible = true;
        if (root.paths.length === 1) {
            root.loadId = Backend.call("tags.for_paths", { paths: root.paths });
        }
        Qt.callLater(function () { tagField.forceActiveFocus(); });
    }

    function apply() {
        const tags = root.tagsText.split(",").map(function (item) {
            return item.trim();
        }).filter(function (item) { return item.length > 0; });
        root.setId = Backend.call("tags.set", {
            paths: root.paths,
            tags: tags,
            color: root.color,
        });
    }

    function dismiss() {
        root.visible = false;
        root.setId = -1;
        root.loadId = -1;
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === root.loadId) {
                root.loadId = -1;
                const entry = (result && result.paths) ? result.paths[root.paths[0]] : null;
                if (entry) {
                    root.tagsText = (entry.tags || []).join(", ");
                    root.color = entry.color || "";
                }
            } else if (id === root.setId) {
                root.setId = -1;
                root.dismiss();
            }
        }
        function onFailure(id, message) {
            if (id === root.loadId || id === root.setId) {
                root.loadId = -1;
                root.setId = -1;
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
        width: Math.min(480, parent.width - 80)
        implicitHeight: content.implicitHeight + 36
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            id: content
            width: parent.width - 36
            x: 18
            y: 18
            spacing: 10

            Text {
                text: "Tags" + (root.paths.length > 1 ? " — " + root.paths.length + " items" : "")
                color: Theme.accent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(4)
                font.bold: true
            }

            Text {
                width: parent.width
                text: "Comma-separated. A tag filters the listing and survives restarts."
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                wrapMode: Text.WordWrap
            }

            LabeledField {
                id: tagField
                width: parent.width
                placeholder: "work, holiday, to-review"
                text: root.tagsText
                onTextChanged: root.tagsText = text
                onAccepted: root.apply()
            }

            Row {
                spacing: 6
                Repeater {
                    model: root.colors
                    delegate: Rectangle {
                        required property var modelData
                        width: 24; height: 24; radius: 12
                        color: modelData === "" ? Theme.controlFill : modelData
                        border.width: root.color === modelData ? 2 : 1
                        border.color: root.color === modelData ? Theme.accent
                                                                : Theme.controlBorder
                        Text {
                            anchors.centerIn: parent
                            visible: modelData === ""
                            text: "×"
                            color: Theme.dim
                            font.pixelSize: 12
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.color = modelData
                        }
                    }
                }
            }

            Row {
                spacing: 8
                DialogButton { text: "Apply"; primary: true; onClicked: root.apply() }
                DialogButton { text: "Cancel"; onClicked: root.dismiss() }
            }

            Text {
                width: parent.width
                text: root.status
                visible: root.status.length > 0
                color: Theme.danger
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                wrapMode: Text.WordWrap
            }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
