import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property string targetPath: ""
    property string mime: ""
    property var apps: []
    property bool loading: false
    property string error: ""
    property int pendingLoadId: -1
    property int pendingLaunchId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 238
    focus: visible

    function open(path) {
        root.targetPath = path || "";
        root.mime = "";
        root.apps = [];
        root.error = "";
        root.loading = true;
        root.pendingLoadId = -1;
        root.pendingLaunchId = -1;
        root.visible = true;
        root.pendingLoadId = Backend.call("open_with.apps", { path: root.targetPath });
        Qt.callLater(function () { appList.forceActiveFocus(); });
    }

    function dismiss() {
        root.visible = false;
        root.pendingLoadId = -1;
        root.pendingLaunchId = -1;
        root.error = "";
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    function cancel() {
        root.dismiss();
    }

    function launchCurrent() {
        const app = root.apps[appList.currentIndex];
        if (!app)
            return;
        root.error = "";
        root.pendingLaunchId = Backend.call("open_with.launch", {
            path: root.targetPath,
            app: app.id
        });
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === root.pendingLoadId) {
                root.pendingLoadId = -1;
                root.loading = false;
                root.mime = (result && result.mime) || "";
                root.apps = (result && result.apps) || [];
                appList.currentIndex = 0;
                Qt.callLater(function () { appList.forceActiveFocus(); });
            } else if (id === root.pendingLaunchId) {
                root.pendingLaunchId = -1;
                root.dismiss();
            }
        }
        function onFailure(id, message) {
            if (id === root.pendingLoadId) {
                root.pendingLoadId = -1;
                root.loading = false;
                root.error = message;
            } else if (id === root.pendingLaunchId) {
                root.pendingLaunchId = -1;
                root.error = message;
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 470
        height: 430
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 8

            Text {
                text: "Open With"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: root.targetPath
                color: Theme.accent
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }

            Text {
                width: parent.width
                text: root.mime.length > 0 ? root.mime : " "
                color: Theme.muted
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            Rectangle {
                width: parent.width
                height: 268
                radius: 8
                color: Theme.alpha(Theme.foreground, 0.04)
                border.width: 1
                border.color: Theme.alpha(Theme.foreground, 0.1)
                clip: true

                ListView {
                    id: appList
                    anchors.fill: parent
                    anchors.margins: 4
                    model: root.apps
                    spacing: 2
                    boundsBehavior: Flickable.StopAtBounds
                    focus: true
                    keyNavigationEnabled: false

                    Keys.onUpPressed: {
                        if (appList.currentIndex > 0)
                            appList.currentIndex -= 1;
                    }
                    Keys.onDownPressed: {
                        if (appList.currentIndex < root.apps.length - 1)
                            appList.currentIndex += 1;
                    }
                    Keys.onReturnPressed: root.launchCurrent()
                    Keys.onEnterPressed: root.launchCurrent()
                    Keys.onEscapePressed: root.cancel()

                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: appList.width
                        height: 38
                        radius: 6
                        color: ListView.isCurrentItem
                            ? Theme.alpha(Theme.accent, 0.25)
                            : (appHover.hovered ? Theme.alpha(Theme.foreground, 0.08) : "transparent")

                        MouseArea {
                            id: appHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: appList.currentIndex = index
                            onClicked: {
                                appList.currentIndex = index;
                                root.launchCurrent();
                            }
                        }

                        Image {
                            id: appIcon
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            width: 22
                            height: 22
                            sourceSize: Qt.size(22, 22)
                            source: Quickshell.iconPath(modelData.icon || "application-x-executable",
                                                         "application-x-executable")
                        }

                        Text {
                            anchors.left: appIcon.right
                            anchors.leftMargin: 10
                            anchors.right: defaultBadge.left
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name
                            color: Theme.foreground
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            id: defaultBadge
                            anchors.right: parent.right
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            visible: modelData.default === true
                            width: defaultText.implicitWidth + 12
                            height: 18
                            radius: 9
                            color: Theme.alpha(Theme.accent, 0.3)

                            Text {
                                id: defaultText
                                anchors.centerIn: parent
                                text: "Default"
                                color: Theme.foreground
                                font.pixelSize: 9
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.loading
                    text: "Loading applications…"
                    color: Theme.muted
                    font.pixelSize: 12
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 4
                    visible: !root.loading && root.apps.length === 0

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.error.length > 0 ? root.error : "No applications found"
                        color: root.error.length > 0 ? Theme.danger : Theme.muted
                        font.pixelSize: 12
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: root.error.length === 0
                        text: "Install python-gobject to discover applications"
                        color: Theme.muted
                        font.pixelSize: 10
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Cancel"
                    onClicked: root.cancel()
                }

                DialogButton {
                    text: "Open"
                    primary: true
                    onClicked: root.launchCurrent()
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.cancel()
    }
}
