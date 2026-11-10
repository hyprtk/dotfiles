import QtQuick
import Quickshell
import "../theme"
import "../config"
import "../data"
import "../components"

Rectangle {
    id: root

    signal navigate(string path)
    signal emptyTrashRequested()

    property string currentPath: ""
    property var groups: ({ places: [], devices: [] })
    property var networkDevices: []
    property bool networkScanning: false
    property string networkError: ""
    property double networkScannedAt: 0
    property string deviceBusy: ""
    property string deviceError: ""
    property string busyUri: ""
    property int scanId: -1
    property int networkMountId: -1
    property int deviceMountId: -1
    property int deviceEjectId: -1

    color: Theme.alpha(Theme.surface, 0.45)

    function reload() {
        Backend.call("places", {});
    }

    function removePlace(path) {
        Backend.call("bookmarks.remove", { path: path });
        root.reload();
    }

    function scanNetwork() {
        if (root.networkScanning)
            return;
        root.networkScanning = true;
        root.networkError = "";
        root.scanId = Backend.call("network.scan", {});
    }

    function requestShare(uri, name) {
        if (!uri)
            return;
        Ui.askNetworkAuth(uri, name || uri);
    }

    function mountShare(uri, username, password, domain) {
        if (!uri || root.busyUri)
            return;
        root.busyUri = uri;
        root.networkError = "";
        root.networkMountId = Backend.call("network.mount", {
            uri: uri,
            username: username || "",
            password: password || "",
            domain: domain || ""
        });
    }

    function mountDevice(device) {
        if (!device || root.deviceBusy)
            return;
        root.deviceBusy = device;
        root.deviceError = "";
        root.deviceMountId = Backend.call("devices.mount", { device: device });
    }

    function ejectDevice(device) {
        if (!device || root.deviceBusy)
            return;
        root.deviceBusy = device;
        root.deviceError = "";
        root.deviceEjectId = Backend.call("devices.eject", { device: device });
    }

    function deviceMenuItems(item) {
        const items = [];
        if (item.mounted && item.path)
            items.push({ label: "Open", action: function () { root.navigate(item.path); } });
        else
            items.push({ label: "Mount", enabled: !!item.device, action: function () { root.mountDevice(item.device); } });
        if (item.mounted && item.external)
            items.push({ label: "Eject Media", action: function () { root.ejectDevice(item.device); } });
        return items;
    }

    function flatNetwork() {
        const out = [];
        const list = root.networkDevices || [];
        for (let i = 0; i < list.length; i++) {
            const device = list[i];
            out.push({
                kind: "host",
                name: device.name || device.host,
                host: device.host,
                services: (device.services || []).join(" · "),
                servicesList: device.services || [],
                icon: device.icon || "network-server"
            });
            const shares = device.shares || [];
            for (let j = 0; j < shares.length; j++)
                out.push({ kind: "share", name: shares[j].name, uri: shares[j].uri, icon: "folder-remote" });
        }
        return out;
    }

    function placeMenuItems(item) {
        const items = [{ label: "Open", action: function () { root.navigate(item.path); } }];
        if (item.name === "Trash")
            items.push({ label: "Empty Trash…", action: function () { root.emptyTrashRequested(); } });
        if (item.custom)
            items.push({ label: "Remove from Places", action: function () { root.removePlace(item.path); } });
        return items;
    }

    Component.onCompleted: root.reload()

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (!result)
                return;
            if (result.kind === "places") {
                root.groups = result;
                return;
            }
            if (result.kind === "network") {
                root.networkDevices = result.devices || [];
                root.networkScannedAt = result.scanned_at || 0;
                root.networkScanning = false;
                root.networkError = "";
                root.scanId = -1;
                return;
            }
            if (result.kind === "network_mount") {
                root.networkMountId = -1;
                root.busyUri = "";
                root.navigate(result.path);
                return;
            }
            if (result.kind === "device_mount") {
                root.deviceMountId = -1;
                root.deviceBusy = "";
                root.navigate(result.path);
                root.reload();
                return;
            }
            if (result.kind === "device_eject") {
                root.deviceEjectId = -1;
                root.deviceBusy = "";
                if (result.path && root.currentPath.indexOf(result.path) === 0)
                    root.navigate(Config.startPath);
                root.reload();
                return;
            }
        }
        function onFailure(id, message) {
            if (id === root.scanId) {
                root.scanId = -1;
                root.networkScanning = false;
                root.networkError = message;
            } else if (id === root.networkMountId) {
                root.networkMountId = -1;
                root.busyUri = "";
                root.networkError = message;
            } else if (id === root.deviceMountId) {
                root.deviceMountId = -1;
                root.deviceBusy = "";
                root.deviceError = message;
            } else if (id === root.deviceEjectId) {
                root.deviceEjectId = -1;
                root.deviceBusy = "";
                root.deviceError = message;
            }
        }
    }

    Connections {
        target: Ui
        function onPlacesChanged() { root.reload(); }
        function onNetworkScanRequested() { root.scanNetwork(); }
        function onNetworkAuthAccepted(uri, username, password, domain) {
            root.mountShare(uri, username, password, domain);
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

            Text {
                width: parent.width
                height: 26
                leftPadding: 16
                verticalAlignment: Text.AlignVCenter
                text: "Places"
                color: Theme.accent
                font.pixelSize: 10
                font.bold: true
            }

            Repeater {
                model: root.groups.places || []

                delegate: Rectangle {
                    required property var modelData
                    width: sections.width
                    height: 30
                    radius: 6
                    color: (root.currentPath === modelData.path)
                        ? Theme.alpha(Theme.accent, 0.18)
                        : (placeHover.hovered ? Theme.alpha(Theme.accent2, 0.10) : "transparent")

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
                        id: placeHover
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (mouse) => {
                            if (mouse.button === Qt.RightButton) {
                                placeMenu.items = root.placeMenuItems(modelData);
                                const point = mapToItem(root, mouse.x, mouse.y);
                                placeMenu.openAt(point.x, point.y);
                                return;
                            }
                            root.navigate(modelData.path);
                        }
                    }
                }
            }

            Text {
                width: parent.width
                leftPadding: 16
                topPadding: 12
                bottomPadding: 4
                text: "Devices"
                color: Theme.accent
                font.pixelSize: 10
                font.bold: true
            }

            Repeater {
                model: root.groups.devices || []

                delegate: Rectangle {
                    required property var modelData
                    width: sections.width
                    height: 30
                    radius: 6
                    opacity: modelData.mounted ? 1.0 : 0.78
                    color: (modelData.mounted && root.currentPath === modelData.path)
                        ? Theme.alpha(Theme.accent, 0.18)
                        : (deviceHover.hovered ? Theme.alpha(Theme.accent2, 0.10) : "transparent")

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
                            source: Quickshell.iconPath(modelData.icon || "drive-harddisk", "drive-harddisk")
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - (modelData.mounted ? (modelData.external ? 44 : 24) : 72)
                            text: modelData.name
                            color: Theme.foreground
                            font.pixelSize: Theme.fontSize
                            elide: Text.ElideRight
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !modelData.mounted
                            width: 40
                            horizontalAlignment: Text.AlignRight
                            text: root.deviceBusy === modelData.device ? "…" : "mount"
                            color: Theme.accent2
                            font.pixelSize: 9
                        }
                    }

                    MouseArea {
                        id: deviceHover
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (mouse) => {
                            if (mouse.button === Qt.RightButton) {
                                deviceMenu.items = root.deviceMenuItems(modelData);
                                const point = mapToItem(root, mouse.x, mouse.y);
                                deviceMenu.openAt(point.x, point.y);
                                return;
                            }
                            if (modelData.mounted)
                                root.navigate(modelData.path);
                            else
                                root.mountDevice(modelData.device);
                        }
                    }

                    Item {
                        visible: modelData.mounted && modelData.external
                        width: 18
                        height: parent.height
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        opacity: root.deviceBusy === modelData.device
                            ? 0.35 : (deviceEjectHover.hovered ? 1.0 : 0.72)

                        Image {
                            anchors.centerIn: parent
                            width: 14
                            height: 14
                            sourceSize: Qt.size(14, 14)
                            source: Quickshell.iconPath("media-eject", "media-eject")
                        }

                        MouseArea {
                            id: deviceEjectHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.deviceBusy !== modelData.device)
                                    root.ejectDevice(modelData.device);
                            }
                        }
                    }
                }
            }

            Text {
                visible: (root.groups.devices || []).length === 0 && (root.groups.places || []).length > 0
                x: 16
                width: parent.width - 28
                text: "No external devices"
                color: Theme.muted
                font.pixelSize: 9
            }

            Text {
                visible: root.deviceError.length > 0
                x: 16
                width: parent.width - 28
                text: root.deviceError
                color: Theme.danger
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            Item {
                width: sections.width
                height: 26

                Row {
                    anchors.fill: parent

                    Text {
                        width: parent.width - 60
                        leftPadding: 16
                        text: root.networkScanning ? "Network · scanning…" : "Network"
                        color: Theme.accent
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Text {
                        width: 28
                        text: "⟳"
                        color: Theme.accent
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.scanNetwork()
                }
            }

            Text {
                visible: root.networkError.length > 0
                x: 16
                width: parent.width - 28
                text: root.networkError
                color: Theme.danger
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: root.flatNetwork()

                delegate: Rectangle {
                    required property var modelData
                    width: sections.width
                    height: modelData.kind === "host" ? 28 : 26
                    radius: 6
                    color: (modelData.kind === "share" && shareHover.hovered)
                        ? Theme.alpha(Theme.accent2, 0.10) : "transparent"

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: modelData.kind === "share" ? 30 : 16
                        anchors.rightMargin: 8
                        spacing: 6

                        Image {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 15
                            height: 15
                            sourceSize: Qt.size(15, 15)
                            source: Quickshell.iconPath(modelData.icon || "network-server", "network-server")
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 30 - (modelData.kind === "host" ? 44 : 0)
                            text: modelData.name
                            color: modelData.kind === "host" ? Theme.muted : Theme.foreground
                            font.pixelSize: modelData.kind === "host" ? 10 : Theme.fontSize - 1
                            elide: Text.ElideRight
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: modelData.kind === "host"
                            width: 40
                            horizontalAlignment: Text.AlignRight
                            text: (root.busyUri.length > 0 && modelData.host && root.busyUri.indexOf(modelData.host) >= 0)
                                ? "…" : (modelData.services || "")
                            color: Theme.alpha(Theme.foreground, 0.45)
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: modelData.kind === "share" && root.busyUri === modelData.uri
                            width: 14
                            text: "…"
                            color: Theme.accent
                            font.pixelSize: 10
                        }
                    }

                    MouseArea {
                        id: shareHover
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: modelData.kind === "share"
                            ? !root.busyUri
                            : (modelData.servicesList && modelData.servicesList.length > 0)
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.kind === "share") {
                                root.requestShare(modelData.uri, modelData.name);
                            } else if (modelData.servicesList.indexOf("smb") >= 0) {
                                root.requestShare("smb://" + modelData.host + "/", modelData.name || modelData.host);
                            } else if (modelData.servicesList.indexOf("nfs") >= 0) {
                                root.requestShare("nfs://" + modelData.host + "/", modelData.name || modelData.host);
                            }
                        }
                    }
                }
            }

            Text {
                visible: !root.networkScanning && root.networkScannedAt > 0 && root.flatNetwork().length === 0
                x: 16
                width: parent.width - 28
                topPadding: 2
                text: "No storage devices found"
                color: Theme.muted
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            Item {
                width: 1
                height: 12
            }
        }
    }

    MenuPopup {
        id: placeMenu
    }

    MenuPopup {
        id: deviceMenu
    }
}
