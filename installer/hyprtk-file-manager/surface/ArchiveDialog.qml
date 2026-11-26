// Archive browser: list an archive, walk into its directories and extract.
// Extraction never trusts member names — the backend refuses absolute paths,
// ".." segments and links (see backend/hyprtk_file_manager/archive.py).
import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property string archivePath: ""
    property string inner: ""
    property var entries: []
    property bool loading: false
    property string status: ""
    property int listId: -1
    property int extractId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 236
    focus: visible

    function open(path) {
        root.archivePath = path || "";
        root.inner = "";
        root.entries = [];
        root.status = "";
        root.visible = true;
        root.reload();
    }

    function reload() {
        if (root.archivePath.length === 0)
            return;
        root.loading = true;
        root.listId = Backend.call("archive.list", { path: root.archivePath, inner: root.inner });
    }

    function extract(target) {
        root.status = "Extracting…";
        root.extractId = Backend.call("archive.extract", {
            path: root.archivePath,
            inner: target || "",
        });
    }

    function dismiss() {
        root.visible = false;
        root.listId = -1;
        root.extractId = -1;
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    function down(name) {
        root.inner = name;
        root.reload();
    }

    function up() {
        const cut = root.inner.lastIndexOf("/");
        root.inner = cut > 0 ? root.inner.substring(0, cut) : "";
        root.reload();
    }

    function humanSize(bytes) {
        if (!bytes || bytes <= 0)
            return "";
        const units = ["B", "K", "M", "G", "T"];
        let value = bytes;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit += 1;
        }
        return (unit === 0 ? value : value.toFixed(1)) + " " + units[unit];
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === root.listId) {
                root.listId = -1;
                root.loading = false;
                root.entries = (result && result.entries) || [];
                list.currentIndex = 0;
            } else if (id === root.extractId) {
                root.extractId = -1;
                const count = (result && result.extracted) ? result.extracted.length : 0;
                root.status = count + " file(s) extracted to " +
                              ((result && result.destination) || "the archive folder");
            }
        }
        function onFailure(id, message) {
            if (id === root.listId) {
                root.listId = -1;
                root.loading = false;
                root.status = message;
            } else if (id === root.extractId) {
                root.extractId = -1;
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
        width: Math.min(680, parent.width - 80)
        height: Math.min(520, parent.height - 80)
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10

            Text {
                width: parent.width
                text: "Archive — " + root.archivePath.split("/").pop()
                color: Theme.accent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(4)
                font.bold: true
                elide: Text.ElideMiddle
            }

            Text {
                width: parent.width
                visible: root.inner.length > 0
                text: "/" + root.inner
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                elide: Text.ElideMiddle
            }

            ListView {
                id: list
                width: parent.width
                height: parent.height - 150
                clip: true
                model: root.entries
                spacing: 2

                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: list.width
                    height: 30
                    radius: 5
                    color: ListView.isCurrentItem ? Theme.alpha(Theme.accent, 0.18)
                         : (rowArea.containsMouse ? Theme.rowHover : "transparent")

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 120
                        text: (modelData.dir ? "▸ " : "  ") + modelData.name
                        color: Theme.foreground
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.size(2)
                        elide: Text.ElideMiddle
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.dir ? "folder" : root.humanSize(modelData.size)
                        color: Theme.dim
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.size(1)
                    }
                    MouseArea {
                        id: rowArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            list.currentIndex = index;
                            if (modelData.dir)
                                root.down(modelData.path);
                        }
                        onDoubleClicked: {
                            if (!modelData.dir)
                                root.extract(modelData.path);
                        }
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 8
                DialogButton {
                    text: "Up"
                    enabled: root.inner.length > 0
                    onClicked: root.up()
                }
                DialogButton {
                    text: "Extract all here"
                    primary: true
                    enabled: !root.loading && root.extractId < 0
                    onClicked: root.extract("")
                }
                DialogButton {
                    text: "Extract selected"
                    enabled: !root.loading && root.extractId < 0 && list.count > 0 &&
                             list.currentIndex >= 0
                    onClicked: {
                        const entry = root.entries[list.currentIndex];
                        if (entry)
                            root.extract(entry.path);
                    }
                }
                DialogButton { text: "Close"; onClicked: root.dismiss() }
            }

            Text {
                width: parent.width
                text: root.loading ? "Reading the archive…" : root.status
                color: root.status.indexOf("refus") >= 0 ? Theme.danger : Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                elide: Text.ElideRight
            }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
