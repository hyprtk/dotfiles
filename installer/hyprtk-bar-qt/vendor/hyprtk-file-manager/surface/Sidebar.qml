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
    property int sharesId: -1
    property int networkMountId: -1
    property int deviceMountId: -1
    property int deviceEjectId: -1
    property var shareCredentials: ({})
    property string pendingSharesHost: ""
    property var pendingSharesAuth: null
    property var pendingPrompt: null
    property string lastNetworkUri: ""
    property var collapsedHosts: ({})

    property var pane: null

    readonly property bool canGoBack: root.pane !== null && root.pane.historyIndex > 0
    readonly property bool canGoForward: root.pane !== null
        && root.pane.historyIndex < root.pane.history.length - 1
    readonly property bool canGoUp: root.pane !== null && root.pane.path !== "/"

    color: Theme.alpha(Theme.surface, 0.45)

    function goHome() {
        root.navigate(Quickshell.env("HOME") || "/");
    }

    function reload() {
        Backend.call("places", {});
    }

    function removePlace(path) {
        Backend.call("bookmarks.remove", { path: path });
        root.reload();
    }

    function orderedPlaces(list) {
        const items = (list || []).slice();
        const order = Config.placesOrder || [];
        if (order.length === 0)
            return items;
        const rank = {};
        for (let i = 0; i < order.length; i++)
            rank[order[i]] = i;
        return items.sort(function (a, b) {
            const ra = rank[a.path] !== undefined ? rank[a.path] : Number.MAX_SAFE_INTEGER;
            const rb = rank[b.path] !== undefined ? rank[b.path] : Number.MAX_SAFE_INTEGER;
            return ra - rb;
        });
    }

    function movePlace(item, delta) {
        const list = root.orderedPlaces(root.groups.places || []);
        const index = list.findIndex(function (place) { return place.path === item.path; });
        const target = index + delta;
        if (index < 0 || target < 0 || target >= list.length)
            return;
        const moved = list.splice(index, 1)[0];
        list.splice(target, 0, moved);
        Config.placesOrder = list.map(function (place) { return place.path; });
        root.groups = Object.assign({}, root.groups, { places: list });
        Config.save();
    }

    function scanNetwork() {
        if (root.networkScanning)
            return;
        root.networkScanning = true;
        root.networkError = "";
        root.scanId = Backend.call("network.scan", {});
    }

    function uriHost(uri) {
        const rest = String(uri || "").replace(/^[a-z][a-z0-9+.-]*:\/\//i, "");
        return rest.split("/")[0].split("@").pop();
    }

    function hostLabel(host) {
        const devices = root.networkDevices || [];
        for (let i = 0; i < devices.length; i++) {
            if (devices[i].host === host)
                return devices[i].name || host;
        }
        return host;
    }

    function uriHasShare(uri) {
        const rest = String(uri || "").replace(/^[a-z][a-z0-9+.-]*:\/\//i, "");
        const slash = rest.indexOf("/");
        return slash >= 0 && rest.slice(slash + 1).length > 0;
    }

    function cachedCredentials(uri) {
        const host = root.uriHost(uri);
        return host && root.shareCredentials[host] ? root.shareCredentials[host] : null;
    }

    function rememberCredentials(uri, username, password, domain, anonymous) {
        const host = root.uriHost(uri);
        if (!host)
            return;
        const updated = Object.assign({}, root.shareCredentials);
        updated[host] = {
            username: username || "",
            password: password || "",
            domain: domain || "",
            anonymous: !!anonymous
        };
        root.shareCredentials = updated;
    }

    function forgetCredentials(uri) {
        const host = root.uriHost(uri);
        if (!host || !root.shareCredentials[host])
            return;
        const updated = Object.assign({}, root.shareCredentials);
        delete updated[host];
        root.shareCredentials = updated;
    }

    function requestShare(uri, name) {
        if (!uri)
            return;
        const cached = root.cachedCredentials(uri);
        if (cached) {
            if (root.uriHasShare(uri))
                root.mountShare(uri, cached.username, cached.password, cached.domain, cached.anonymous);
            else
                root.listShares(uri, cached);
            return;
        }
        if (String(uri).toLowerCase().indexOf("smb://") === 0)
            root.pendingPrompt = { uri: uri, name: name || uri };
        const empty = { username: "", password: "", domain: "", anonymous: false };
        if (root.uriHasShare(uri))
            root.mountShare(uri, "", "", "", false);
        else
            root.listShares(uri, empty);
    }

    function hostCollapsed(host) {
        return !!root.collapsedHosts[host];
    }

    function setHostCollapsed(host, collapsed) {
        if (!host)
            return;
        const updated = Object.assign({}, root.collapsedHosts);
        if (collapsed)
            updated[host] = true;
        else
            delete updated[host];
        root.collapsedHosts = updated;
    }

    function toggleHost(device) {
        if (!device)
            return;
        if (!root.hostCollapsed(device.host)) {
            if (device.shares && device.shares.length > 0) {
                root.setHostCollapsed(device.host, true);
                return;
            }
        } else {
            root.setHostCollapsed(device.host, false);
            if (device.shares && device.shares.length > 0)
                return;
        }
        const scheme = (device.servicesList || []).indexOf("nfs") >= 0
            && (device.servicesList || []).indexOf("smb") < 0 ? "nfs" : "smb";
        root.requestShare(scheme + "://" + device.host + "/", device.name || device.host);
    }

    function listShares(uri, credentials) {
        if (!uri || root.busyUri || root.sharesId >= 0)
            return;
        root.busyUri = uri;
        root.lastNetworkUri = uri;
        root.networkError = "";
        root.pendingSharesHost = root.uriHost(uri);
        root.pendingSharesAuth = credentials || { username: "", password: "", domain: "", anonymous: false };
        root.sharesId = Backend.call("network.shares", {
            uri: uri,
            username: root.pendingSharesAuth.username || "",
            password: root.pendingSharesAuth.password || "",
            domain: root.pendingSharesAuth.domain || ""
        });
    }

    function applyShares(host, shares) {
        const list = (root.networkDevices || []).slice();
        for (let i = 0; i < list.length; i++) {
            if (list[i].host === host) {
                list[i] = Object.assign({}, list[i], { shares: shares || [] });
            }
        }
        root.networkDevices = list;
    }

    function mountShare(uri, username, password, domain, anonymous) {
        if (!uri || root.busyUri)
            return;
        root.busyUri = uri;
        root.lastNetworkUri = uri;
        root.networkError = "";
        root.networkMountId = Backend.call("network.mount", {
            uri: uri,
            username: username || "",
            password: password || "",
            domain: domain || "",
            anonymous: !!anonymous
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
                shares: device.shares || [],
                icon: device.icon || "network-server"
            });
            if (root.hostCollapsed(device.host))
                continue;
            const shares = device.shares || [];
            for (let j = 0; j < shares.length; j++)
                out.push({ kind: "share", name: shares[j].name, uri: shares[j].uri, icon: "folder-remote" });
        }
        return out;
    }

    function shareMenuItems(item) {
        const items = [
            { label: "Open", action: function () { root.requestShare(item.uri, item.name); } },
            { label: "Add to Places", action: function () {
                Backend.call("bookmarks.add", { path: item.uri, label: item.name });
                root.reload();
            } }
        ];
        return items;
    }

    function placeMenuItems(item) {
        const list = root.orderedPlaces(root.groups.places || []);
        const index = list.findIndex(function (place) { return place.path === item.path; });
        const items = [{ label: "Open", action: function () {
            if (item.uri)
                root.requestShare(item.path, item.name);
            else
                root.navigate(item.path);
        } }];
        if (item.name === "Trash")
            items.push({ label: "Empty Trash…", action: function () { root.emptyTrashRequested(); } });
        items.push({ separator: true });
        items.push({ label: "Move Up", enabled: index > 0, action: function () { root.movePlace(item, -1); } });
        items.push({ label: "Move Down", enabled: index >= 0 && index < list.length - 1,
                     action: function () { root.movePlace(item, 1); } });
        if (item.custom)
            items.push({ label: "Remove from Places", action: function () { root.removePlace(item.path); } });
        return items;
    }

    Component.onCompleted: root.reload()

    Connections {
        target: Config
        function onPlacesOrderChanged() {
            if (root.groups.places)
                root.groups = Object.assign({}, root.groups, { places: root.orderedPlaces(root.groups.places) });
        }
    }

    Timer {
        interval: 700
        running: true
        repeat: false
        onTriggered: root.scanNetwork()
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (!result)
                return;
            if (result.kind === "places") {
                root.groups = Object.assign({}, result, { places: root.orderedPlaces(result.places) });
                return;
            }
            if (result.kind === "network") {
                const previous = {};
                (root.networkDevices || []).forEach(function (device) {
                    if (device.shares && device.shares.length)
                        previous[device.host] = device.shares;
                });
                root.networkDevices = (result.devices || []).map(function (device) {
                    return previous[device.host]
                        ? Object.assign({}, device, { shares: previous[device.host] })
                        : device;
                });
                root.networkScannedAt = result.scanned_at || 0;
                root.networkScanning = false;
                root.networkError = "";
                root.scanId = -1;
                return;
            }
            if (result.kind === "network_shares") {
                const credentials = root.pendingSharesAuth;
                root.sharesId = -1;
                root.busyUri = "";
                root.pendingSharesAuth = null;
                root.pendingPrompt = null;
                root.applyShares(result.host, result.shares || []);
                root.setHostCollapsed(result.host, false);
                const shares = result.shares || [];
                if (shares.length === 1 && credentials) {
                    root.mountShare(shares[0].uri, credentials.username, credentials.password,
                                    credentials.domain, credentials.anonymous);
                } else if (shares.length === 0) {
                    root.networkError = "No shares found on " + root.hostLabel(result.host);
                }
                return;
            }
            if (result.kind === "network_mount") {
                root.networkMountId = -1;
                root.busyUri = "";
                root.pendingPrompt = null;
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
            } else if (id === root.sharesId) {
                root.sharesId = -1;
                root.busyUri = "";
                root.pendingSharesAuth = null;
                root.forgetCredentials(root.lastNetworkUri);
                if (root.pendingPrompt) {
                    const prompt = root.pendingPrompt;
                    root.pendingPrompt = null;
                    root.networkError = "";
                    Ui.askNetworkAuth(prompt.uri, prompt.name);
                } else {
                    root.networkError = message;
                }
            } else if (id === root.networkMountId) {
                root.networkMountId = -1;
                root.busyUri = "";
                root.forgetCredentials(root.lastNetworkUri);
                if (root.pendingPrompt) {
                    const prompt = root.pendingPrompt;
                    root.pendingPrompt = null;
                    root.networkError = "";
                    Ui.askNetworkAuth(prompt.uri, prompt.name);
                } else {
                    root.networkError = message;
                }
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
        function onNetworkAuthAccepted(uri, username, password, domain, anonymous) {
            root.rememberCredentials(uri, username, password, domain, anonymous);
            if (root.uriHasShare(uri))
                root.mountShare(uri, username, password, domain, anonymous);
            else
                root.listShares(uri, { username: username, password: password,
                                       domain: domain, anonymous: anonymous });
        }
    }

    Row {
        id: navRow
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 10
        height: 30
        spacing: 2

        IconButton {
            text: Glyph.back
            hint: "Back (Alt+Left)"
            available: root.canGoBack
            onClicked: if (root.pane) root.pane.goBack()
        }

        IconButton {
            text: Glyph.forward
            hint: "Forward (Alt+Right)"
            available: root.canGoForward
            onClicked: if (root.pane) root.pane.goForward()
        }

        IconButton {
            text: Glyph.up
            hint: "Parent folder (Backspace)"
            available: root.canGoUp
            onClicked: if (root.pane) root.pane.goUp()
        }

        IconButton {
            text: Glyph.home
            hint: "Home"
            available: root.pane !== null
            onClicked: root.goHome()
        }

        IconButton {
            text: Glyph.settings
            hint: "Settings (Ctrl+,)"
            onClicked: Ui.askSettings()
        }
    }

    Flickable {
        anchors.top: navRow.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
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
                font.pixelSize: Theme.fontSize
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
                            sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
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
                            if (modelData.uri)
                                root.requestShare(modelData.path, modelData.name);
                            else
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
                font.pixelSize: Theme.fontSize
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
                            sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
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
                            sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
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

                Text {
                    id: networkTitle
                    anchors.left: parent.left
                    anchors.right: networkRefresh.left
                    anchors.rightMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: 16
                    text: root.networkScanning ? "Network · scanning…" : "Network"
                    color: Theme.accent
                    font.pixelSize: Theme.fontSize
                    font.bold: true
                    elide: Text.ElideRight
                }

                Text {
                    id: networkRefresh
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    text: Glyph.refresh
                    color: Theme.accent
                    font.family: Glyph.family
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    opacity: root.networkScanning ? 0.45 : 1.0
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
                            sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
                            source: Quickshell.iconPath(modelData.icon || "network-server", "network-server")
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: modelData.kind === "host"
                                && modelData.shares && modelData.shares.length > 0
                            text: root.hostCollapsed(modelData.host)
                                ? Glyph.chevronRight : Glyph.chevronDown
                            color: Theme.muted
                            font.family: Glyph.family
                            font.pixelSize: 9
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 30 - (modelData.kind === "host" ? 44 : 0)
                                - (modelData.kind === "host" && modelData.shares
                                   && modelData.shares.length > 0 ? 14 : 0)
                            text: modelData.name
                            color: modelData.kind === "host" ? Theme.muted : Theme.foreground
                            font.pixelSize: Theme.fontSize
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
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        enabled: modelData.kind === "share"
                            ? !root.busyUri
                            : (modelData.servicesList && modelData.servicesList.length > 0)
                        cursorShape: Qt.PointingHandCursor
                        onClicked: (mouse) => {
                            if (modelData.kind === "share") {
                                if (mouse.button === Qt.RightButton) {
                                    shareMenu.items = root.shareMenuItems(modelData);
                                    const point = mapToItem(root, mouse.x, mouse.y);
                                    shareMenu.openAt(point.x, point.y);
                                    return;
                                }
                                root.requestShare(modelData.uri, modelData.name);
                            } else {
                                root.toggleHost(modelData);
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

    MenuPopup {
        id: shareMenu
    }
}
