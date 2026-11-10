import QtQuick
import Quickshell
import "../theme"
import "../data"

Rectangle {
    id: root

    signal navigate(string path)
    signal emptyTrashRequested()

    property string currentPath: ""
    property var groups: ({ places: [], bookmarks: [], drives: [] })

    color: Theme.alpha(Theme.surface, 0.45)

    function load() {
        Backend.call("places", {});
    }

    Component.onCompleted: root.load()

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (result && result.kind === "places")
                root.groups = result;
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.topMargin: 14
        anchors.bottomMargin: 14
        contentHeight: sections.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: sections
            width: root.width
            spacing: 2

            Repeater {
                model: [
                    { title: "Places", key: "places" },
                    { title: "Bookmarks", key: "bookmarks" },
                    { title: "Drives", key: "drives" }
                ]

                delegate: Column {
                    required property var modelData
                    width: sections.width
                    spacing: 2

                    Text {
                        x: 16
                        width: parent.width - 16
                        topPadding: 10
                        bottomPadding: 4
                        text: modelData.title
                        color: Theme.accent
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Repeater {
                        model: root.groups[modelData.key] || []

                        delegate: Rectangle {
                            required property var modelData
                            width: sections.width
                            height: 30
                            radius: 6
                            color: (root.currentPath === modelData.path)
                                ? Theme.alpha(Theme.accent, 0.18)
                                : (itemHover.hovered ? Theme.alpha(Theme.accent2, 0.10) : "transparent")

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 8
                                spacing: 8

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 16
                                    height: 16
                                    sourceSize: Qt.size(16, 16)
                                    source: Quickshell.iconPath(modelData.icon || "folder", "folder")
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 24
                                    text: modelData.name
                                    color: Theme.foreground
                                    font.pixelSize: Theme.fontSize
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: itemHover
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                cursorShape: Qt.PointingHandCursor
                                onClicked: (mouse) => {
                                    if (mouse.button === Qt.RightButton) {
                                        const items = [
                                            { label: "Open", action: function () { root.navigate(modelData.path); } }
                                        ];
                                        if (modelData.name === "Trash")
                                            items.push({ label: "Empty Trash…", action: function () { root.emptyTrashRequested(); } });
                                        placeMenu.items = items;
                                        const point = mapToItem(root, mouse.x, mouse.y);
                                        placeMenu.openAt(point.x, point.y);
                                        return;
                                    }
                                    root.navigate(modelData.path);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    MenuPopup {
        id: placeMenu
    }

}
