// Read-only diff of one file against the repository's HEAD (untracked files
// show as added content). Nothing here writes to the repository.
import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property string targetPath: ""
    property string text: ""
    property string note: ""
    property bool loading: false
    property bool truncated: false
    property int diffId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 242
    focus: visible

    function open(path) {
        root.targetPath = path || "";
        root.text = "";
        root.note = "";
        root.truncated = false;
        root.loading = true;
        root.visible = true;
        root.diffId = Backend.call("git.diff", { path: root.targetPath });
    }

    function dismiss() {
        root.visible = false;
        root.diffId = -1;
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root.diffId)
                return;
            root.diffId = -1;
            root.loading = false;
            root.text = (result && result.text) || "";
            root.note = (result && result.note) || "";
            root.truncated = !!(result && result.truncated);
        }
        function onFailure(id, message) {
            if (id !== root.diffId)
                return;
            root.diffId = -1;
            root.loading = false;
            root.note = message;
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
        width: Math.min(900, parent.width - 80)
        height: Math.min(640, parent.height - 80)
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            Text {
                width: parent.width
                text: "Diff — " + root.targetPath.split("/").pop()
                color: Theme.accent
                font.pixelSize: Theme.size(4)
                font.bold: true
                elide: Text.ElideMiddle
            }

            Rectangle {
                width: parent.width
                height: parent.height - 92
                radius: 6
                color: Theme.alpha(Theme.background, 0.6)
                border.width: 1
                border.color: Theme.alpha(Theme.foreground, 0.10)
                clip: true

                Flickable {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    contentWidth: Math.max(width, diffText.implicitWidth)
                    contentHeight: Math.max(height, diffText.implicitHeight)

                    TextEdit {
                        id: diffText
                        width: Math.max(parent.width, implicitWidth)
                        text: root.loading ? "Loading…" : (root.text || root.note)
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.NoWrap
                        color: Theme.foreground
                        font.pixelSize: Theme.size(1)
                    }
                }
            }

            Row {
                spacing: 8
                Text {
                    text: root.truncated ? "diff truncated" : ""
                    color: Theme.warn
                    font.pixelSize: Theme.size(1)
                }
                DialogButton { text: "Close"; onClicked: root.dismiss() }
            }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
