import QtQuick
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 228
    focus: visible

    property string path: ""
    property var info: ({})
    property int statId: -1
    property int checksumId: -1
    property int chmodId: -1
    property string checksumText: ""
    property string status: ""

    signal closed()

    function open(target) {
        root.path = target;
        root.info = ({});
        root.checksumText = "";
        root.status = "";
        root.visible = true;
        root.statId = Backend.call("stat", { path: target });
        root.forceActiveFocus();
        focusTimer.restart();
    }

    function close() {
        root.visible = false;
        Ui.close();
        root.closed();
    }

    function humanSize(bytes) {
        if (!bytes || bytes <= 0)
            return "0 B";
        const units = ["B", "K", "M", "G", "T", "P"];
        let value = bytes;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit += 1;
        }
        return (unit === 0 ? value : value.toFixed(1)) + " " + units[unit];
    }

    function fmtDate(seconds) {
        if (!seconds)
            return "";
        return Qt.formatDateTime(new Date(seconds * 1000), "dd MMM yyyy HH:mm:ss");
    }

    function permString(mode) {
        if (!mode)
            return "";
        const chars = "rwxrwxrwx";
        let out = "";
        for (let i = 0; i < 9; i++)
            out += (mode & (1 << (8 - i))) ? chars[i] : "-";
        return out;
    }

    function applyChmod() {
        if (!root.path)
            return;
        root.status = "";
        root.chmodId = Backend.call("chmod", { path: root.path, mode: modeField.text });
    }

    function makeExecutable() {
        if (!root.path || !root.info.mode)
            return;
        const mode = (root.info.mode & 4095) | 73;
        root.status = "";
        root.chmodId = Backend.call("chmod", { path: root.path, mode: mode });
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === root.statId) {
                root.statId = -1;
                root.info = result || ({});
                modeField.text = root.info.mode_octal || "";
                if (root.info.type && root.info.type !== "dir")
                    root.checksumId = Backend.call("checksum", { path: root.path, algo: "sha256" });
            } else if (id === root.checksumId) {
                root.checksumId = -1;
                root.checksumText = result && result.hex ? result.hex : "";
            } else if (id === root.chmodId) {
                root.chmodId = -1;
                if (result && result.mode_octal) {
                    root.info = Object.assign({}, root.info, {
                        mode: result.mode,
                        mode_octal: result.mode_octal
                    });
                    modeField.text = result.mode_octal;
                    root.status = "Permissions applied";
                }
            }
        }
        function onFailure(id, message) {
            if (id === root.statId) {
                root.statId = -1;
                root.status = message;
            } else if (id === root.checksumId) {
                root.checksumId = -1;
                root.checksumText = "failed";
            } else if (id === root.chmodId) {
                root.chmodId = -1;
                root.status = message;
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 580
        height: 600
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 8

            Text {
                text: "Properties"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: root.info.name || ""
                color: Theme.accent
                font.pixelSize: 13
                elide: Text.ElideMiddle
            }

            Text {
                width: parent.width
                text: root.info.path || ""
                color: Theme.muted
                font.pixelSize: 10
                elide: Text.ElideMiddle
            }

            Row {
                width: parent.width
                spacing: 12

                Column {
                    width: (parent.width - 12) / 2
                    spacing: 2

                    Text { text: "Type"; color: Theme.muted; font.pixelSize: 10 }
                    Text { text: root.info.type || ""; color: Theme.foreground; font.pixelSize: 11 }
                    Text { text: "Size"; color: Theme.muted; font.pixelSize: 10 }
                    Text { text: root.humanSize(root.info.size); color: Theme.foreground; font.pixelSize: 11 }
                    Text { text: "Owner"; color: Theme.muted; font.pixelSize: 10 }
                    Text { text: (root.info.owner || "") + " : " + (root.info.group || ""); color: Theme.foreground; font.pixelSize: 11 }
                }

                Column {
                    width: (parent.width - 12) / 2
                    spacing: 2

                    Text { text: "Modified"; color: Theme.muted; font.pixelSize: 10 }
                    Text { text: root.fmtDate(root.info.mtime); color: Theme.foreground; font.pixelSize: 11 }
                    Text { text: "Inode / links"; color: Theme.muted; font.pixelSize: 10 }
                    Text { text: (root.info.inode || "") + "  /  " + (root.info.nlink || ""); color: Theme.foreground; font.pixelSize: 11 }
                    Text { text: "Permissions"; color: Theme.muted; font.pixelSize: 10 }
                    Text {
                        text: root.permString(root.info.mode) + "  (" + (root.info.mode_octal || "") + ")"
                        color: Theme.foreground
                        font.pixelSize: 11
                        font.family: "monospace"
                    }
                }
            }

            Row {
                spacing: 12
                width: parent.width

                LabeledField {
                    id: modeField
                    width: 150
                    label: "Octal mode"
                    placeholder: "0644"
                    onAccepted: root.applyChmod()
                }

                DialogButton {
                    anchors.bottom: parent.bottom
                    text: "Apply"
                    primary: true
                    onClicked: root.applyChmod()
                }

                DialogButton {
                    anchors.bottom: parent.bottom
                    visible: root.info.type === "file"
                    text: "Make executable"
                    onClicked: root.makeExecutable()
                }
            }

            Text {
                width: parent.width
                visible: root.status.length > 0
                text: root.status
                color: Theme.accent2
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Text {
                text: "SHA-256"
                color: Theme.muted
                font.pixelSize: 10
            }

            Text {
                width: parent.width
                text: root.checksumId >= 0 ? "computing…" : (root.checksumText || "—")
                color: Theme.foreground
                font.pixelSize: 10
                font.family: "monospace"
                wrapMode: Text.WrapAnywhere
            }

            Item {
                width: 1
                height: 4
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Close"
                    primary: true
                    onClicked: root.close()
                }
            }
        }
    }

    Timer {
        id: focusTimer
        interval: 300
        repeat: false
        onTriggered: {
            modeField.input.forceActiveFocus();
            modeField.input.selectAll();
        }
    }

    Shortcut {
        sequence: "Ctrl+E"
        enabled: root.visible
        onActivated: root.makeExecutable()
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.close()
    }
}
