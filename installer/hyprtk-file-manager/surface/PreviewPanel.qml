import QtQuick
import Quickshell
import "../theme"
import "../config"
import "../data"

Rectangle {
    id: root

    color: Theme.alpha(Theme.surface, 0.35)

    readonly property var info: Preview.data || ({})
    readonly property var meta: root.info.meta || ({})

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
        return Qt.formatDateTime(new Date(seconds * 1000), "dd MMM HH:mm");
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

    Column {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Row {
            width: parent.width
            height: 22

            Text {
                width: parent.width - 22
                text: root.meta.name || "Preview"
                color: Theme.foreground
                font.pixelSize: 12
                font.bold: true
                elide: Text.ElideMiddle
            }

            Text {
                width: 20
                text: "×"
                color: Theme.muted
                font.pixelSize: 14
                horizontalAlignment: Text.AlignRight

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Config.showPreview = false
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 82

            Image {
                anchors.fill: parent
                visible: root.info.kind === "image" || root.info.kind === "video" || root.info.kind === "pdf"
                source: root.info.thumb ? "file://" + root.info.thumb : ""
                sourceSize: Qt.size(width, height)
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: true
            }

            Flickable {
                anchors.fill: parent
                visible: root.info.kind === "text"
                clip: true
                contentWidth: width
                contentHeight: textPreview.height
                boundsBehavior: Flickable.StopAtBounds

                Text {
                    id: textPreview
                    width: parent.width
                    text: root.info.text || ""
                    color: Theme.foreground
                    font.family: "monospace"
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
                }
            }

            Column {
                anchors.centerIn: parent
                spacing: 8
                visible: root.info.kind === "dir" || root.info.kind === "binary" || !root.info.kind

                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 48
                    height: 48
                    sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
                    source: Quickshell.iconPath(root.meta.icon || (root.info.kind === "dir" ? "folder" : "text-x-generic"), "text-x-generic")
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.info.kind === "dir" ? "Folder"
                        : (root.info.kind === "binary" ? "No preview" : "")
                    color: Theme.muted
                    font.pixelSize: 11
                }
            }
        }

        Column {
            width: parent.width
            spacing: 2

            Text {
                width: parent.width
                text: root.meta.mime || ""
                color: Theme.muted
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            Text {
                text: root.humanSize(root.meta.size) + "  ·  " + root.fmtDate(root.meta.mtime)
                color: Theme.muted
                font.pixelSize: 10
            }

            Text {
                text: root.permString(root.meta.mode)
                color: Theme.muted
                font.pixelSize: 10
                font.family: "monospace"
            }
        }
    }
}
