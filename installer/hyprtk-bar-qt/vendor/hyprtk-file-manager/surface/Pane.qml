import QtQuick
import QtQuick.Layouts
import Quickshell
import "../theme"
import "../config"
import "../data"
import "../components"

Item {
    id: root

    property string initialPath: Config.startPath
    property bool active: false
    property string watchToken: ""
    readonly property bool debugDrag: Quickshell.env("HYPRTK_FM_DEBUG_DRAG") === "1"
    property bool dropActive: false

    signal activated()
    signal sessionChanged()

    property var tabs: []
    property int activeIndex: 0
    property string path: ""
    property var history: []
    property int historyIndex: -1
    property bool editingPath: false

    property var selected: ({})
    property int cursor: 0
    property int anchor: 0
    property bool filtering: false
    property string filterText: ""
    property string filterQuery: ""
    property string pendingReveal: ""

    readonly property int selectedCount: Object.keys(root.selected).length
    readonly property bool opKeysEnabled:
        root.active && !root.editingPath && !root.filtering
        && !Ui.modalOpen && !Jobs.currentConflict && !menu.opened

    function baseName(value) {
        const trimmed = (value || "").replace(/\/+$/, "");
        const index = trimmed.lastIndexOf("/");
        return index < 0 ? trimmed : (trimmed.slice(index + 1) || "/");
    }

    function join(base, name) {
        return base.endsWith("/") ? base + name : base + "/" + name;
    }

    function parentOf(value) {
        if (value === "/")
            return "/";
        const trimmed = value.replace(/\/+$/, "");
        const index = trimmed.lastIndexOf("/");
        return index <= 0 ? "/" : trimmed.slice(0, index);
    }

    function normalize(value) {
        if (!value)
            return value;
        if (value === "~")
            value = Config.startPath;
        else if (value.indexOf("~/") === 0)
            value = Config.startPath + value.slice(1);
        if (value.length > 1)
            value = value.replace(/\/+$/, "");
        return value;
    }

    function reload() {
        listing.reload();
    }

    function syncTab() {
        if (root.tabs.length === 0) {
            root.tabs = [{ path: root.path, history: root.history.slice(), historyIndex: root.historyIndex }];
            root.activeIndex = 0;
            return;
        }
        const next = root.tabs.slice();
        next[root.activeIndex] = {
            path: root.path,
            history: root.history.slice(),
            historyIndex: root.historyIndex
        };
        root.tabs = next;
    }

    function navigate(value) {
        const target = root.normalize(value);
        if (!target || target === root.path)
            return;
        if (root.history.length === 0) {
            root.history = [target];
            root.historyIndex = 0;
        } else {
            const next = root.history.slice(0, root.historyIndex + 1);
            next.push(target);
            root.history = next;
            root.historyIndex = next.length - 1;
        }
        root.path = target;
        root.selected = ({});
        root.cursor = 0;
        root.anchor = 0;
        root.filtering = false;
        root.filterText = "";
        root.filterQuery = "";
        root.syncTab();
        root.sessionChanged();
    }

    function loadTab(index) {
        if (index < 0 || index >= root.tabs.length)
            return;
        root.activeIndex = index;
        const tab = root.tabs[index];
        root.history = (tab.history || [tab.path]).slice();
        root.historyIndex = (tab.historyIndex === undefined) ? root.history.length - 1 : tab.historyIndex;
        root.path = tab.path;
        root.selected = ({});
        root.cursor = 0;
        root.anchor = 0;
        root.filtering = false;
        root.filterText = "";
        root.filterQuery = "";
        root.sessionChanged();
    }

    function newTab(value) {
        const target = root.normalize(value || root.path || Config.startPath);
        root.syncTab();
        const next = root.tabs.slice();
        next.push({ path: target, history: [target], historyIndex: 0 });
        root.tabs = next;
        root.loadTab(next.length - 1);
    }

    function closeTab(index) {
        if (root.tabs.length <= 1) {
            root.navigate(Config.startPath);
            return;
        }
        const next = root.tabs.slice();
        next.splice(index, 1);
        root.tabs = next;
        root.loadTab(Math.max(0, Math.min(index, next.length - 1)));
    }

    function goBack() {
        if (root.historyIndex > 0) {
            root.historyIndex -= 1;
            root.path = root.history[root.historyIndex];
            root.syncTab();
            root.sessionChanged();
        }
    }

    function goForward() {
        if (root.historyIndex < root.history.length - 1) {
            root.historyIndex += 1;
            root.path = root.history[root.historyIndex];
            root.syncTab();
            root.sessionChanged();
        }
    }

    function goUp() {
        const up = root.parentOf(root.path);
        if (up !== root.path)
            root.navigate(up);
    }

    function openEntry(entry) {
        if (!entry)
            return;
        const full = root.join(root.path, entry.name);
        if (entry.dir)
            root.navigate(full);
        else
            Backend.call("open", { path: full });
    }

    function keyFor(name) {
        return root.join(root.path, name);
    }

    function isSelected(name) {
        return root.selected[root.keyFor(name)] === true;
    }

    function selectIndex(index, mode) {
        const entry = listing.entries[index];
        if (!entry)
            return;
        const key = root.keyFor(entry.name);
        if (mode === "toggle") {
            const next = Object.assign({}, root.selected);
            if (next[key])
                delete next[key];
            else
                next[key] = true;
            root.selected = next;
            root.anchor = index;
        } else if (mode === "range") {
            const next = Object.assign({}, root.selected);
            const from = Math.min(index, root.anchor);
            const to = Math.max(index, root.anchor);
            for (let i = from; i <= to; i++) {
                const item = listing.entries[i];
                if (item)
                    next[root.keyFor(item.name)] = true;
            }
            root.selected = next;
        } else {
            const next = {};
            next[key] = true;
            root.selected = next;
            root.anchor = index;
        }
        root.cursor = index;
    }

    function moveCursor(delta) {
        const max = Math.max(0, listing.entries.length - 1);
        root.cursor = Math.max(0, Math.min(max, root.cursor + delta));
        listView.positionViewAtIndex(root.cursor, ListView.Contain);
        gridView.positionViewAtIndex(root.cursor, GridView.Contain);
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
        return Qt.formatDateTime(new Date(seconds * 1000), "dd MMM yyyy HH:mm");
    }

    function sortLabel() {
        return ({ name: "N", size: "S", mtime: "D", type: "T" })[Config.sortKey] || "N";
    }

    function currentEntry() {
        return listing.entries[root.cursor];
    }

    function selectedPaths() {
        const keys = Object.keys(root.selected);
        if (keys.length > 0)
            return keys;
        const entry = root.currentEntry();
        return entry ? [root.keyFor(entry.name)] : [];
    }

    function selectAll() {
        const next = {};
        for (let i = 0; i < listing.entries.length; i++)
            next[root.keyFor(listing.entries[i].name)] = true;
        root.selected = next;
    }

    function copySelection() {
        const paths = root.selectedPaths();
        if (paths.length > 0)
            Clipboard.copy(paths);
    }

    function cutSelection() {
        const paths = root.selectedPaths();
        if (paths.length > 0)
            Clipboard.cut(paths);
    }

    function pasteClipboard() {
        if (!Clipboard.hasItems)
            return;
        const method = Clipboard.mode === "cut" ? "job.move" : "job.copy";
        Backend.call(method, { sources: Clipboard.paths, dest: root.path });
        if (Clipboard.mode === "cut")
            Clipboard.clear();
    }

    function trashSelection() {
        const paths = root.selectedPaths();
        if (paths.length === 0)
            return;
        Backend.call("job.trash", { paths: paths });
        root.selected = ({});
    }

    function deleteSelection() {
        const paths = root.selectedPaths();
        if (paths.length > 0)
            Ui.askDelete(paths, true);
    }

    function renameSelected() {
        const paths = root.selectedPaths();
        if (paths.length > 1) {
            Ui.askBatchRename(paths);
            return;
        }
        const entry = root.currentEntry();
        if (entry)
            Ui.askRename(root.keyFor(entry.name), entry.name);
    }

    function newFolder() {
        Ui.askNew(root.path, true);
    }

    function newFile() {
        Ui.askNew(root.path, false);
    }

    function undoLast() {
        Jobs.undo();
    }

    function redoLast() {
        Jobs.redo();
    }

    function showProperties() {
        const target = root.cursorPath();
        if (target)
            Ui.askProperties(target);
    }

    function trashPath() {
        const data = Quickshell.env("XDG_DATA_HOME") || (Quickshell.env("HOME") + "/.local/share");
        return data + "/Trash/files";
    }

    function openTrash() {
        root.navigate(root.trashPath());
    }

    function inTrash() {
        return root.path.replace(/\/+$/, "") === root.trashPath().replace(/\/+$/, "");
    }

    function restoreSelection() {
        const paths = root.selectedPaths();
        for (let i = 0; i < paths.length; i++)
            Backend.call("trash_restore", { path: paths[i] });
        root.selected = ({});
        root.refreshSoon();
    }

    function launchTarget() {
        const paths = Object.keys(root.selected);
        if (paths.length === 1) {
            const entry = listing.entries.find(function (item) {
                return root.keyFor(item.name) === paths[0];
            });
            if (entry && entry.dir)
                return paths[0];
        }
        return root.path;
    }

    function openTerminal() {
        Backend.call("terminal", { path: root.launchTarget() });
    }

    function openAsRoot() {
        Backend.call("open_root", { path: root.launchTarget() });
    }

    function openTerminalRoot() {
        Backend.call("terminal_root", { path: root.launchTarget() });
    }

    function addToPlaces() {
        let target = root.path;
        const paths = Object.keys(root.selected);
        if (paths.length === 1) {
            const entry = listing.entries.find(function (item) {
                return root.keyFor(item.name) === paths[0];
            });
            if (entry && entry.dir)
                target = paths[0];
        }
        Backend.call("bookmarks.add", { path: target });
        Ui.refreshPlaces();
    }

    function dragPaths(name) {
        const key = root.keyFor(name);
        return root.selected[key] ? Object.keys(root.selected) : [key];
    }

    function dragUrls(name) {
        return root.dragPaths(name).map(function (path) {
            return "file://" + encodeURI(path);
        });
    }

    function currentView() {
        return Config.viewMode === "list" ? listView : gridView;
    }

    function applyMarquee(a, b, additive) {
        const view = root.currentView();
        if (!view)
            return;
        const left = Math.min(a.x, b.x) + view.contentX;
        const top = Math.min(a.y, b.y) + view.contentY;
        const right = Math.max(a.x, b.x) + view.contentX;
        const bottom = Math.max(a.y, b.y) + view.contentY;
        const next = additive ? Object.assign({}, root.selected) : {};
        if (Config.viewMode === "list") {
            const rowHeight = 28;
            const from = Math.max(0, Math.floor(top / rowHeight));
            const to = Math.min(listing.entries.length - 1, Math.floor(bottom / rowHeight));
            for (let i = from; i <= to; i++) {
                const entry = listing.entries[i];
                if (entry) {
                    next[root.keyFor(entry.name)] = true;
                    root.cursor = i;
                }
            }
        } else {
            const columns = Math.max(1, Math.floor(view.width / view.cellWidth));
            const fromRow = Math.max(0, Math.floor(top / view.cellHeight));
            const toRow = Math.floor(bottom / view.cellHeight);
            const fromCol = Math.max(0, Math.floor(left / view.cellWidth));
            const toCol = Math.floor(right / view.cellWidth);
            for (let row = fromRow; row <= toRow; row++) {
                for (let col = fromCol; col <= toCol; col++) {
                    const index = row * columns + col;
                    if (index < 0 || index >= listing.entries.length)
                        continue;
                    const entry = listing.entries[index];
                    if (entry) {
                        next[root.keyFor(entry.name)] = true;
                        root.cursor = index;
                    }
                }
            }
        }
        root.selected = next;
    }

    function openSelected() {
        const entry = root.currentEntry();
        if (entry)
            root.openEntry(entry);
    }

    function openWithSelected() {
        const paths = root.selectedPaths();
        if (paths.length !== 1)
            return;
        Ui.askOpenWith(paths[0]);
    }

    function buildMenu() {
        const paths = root.selectedPaths();
        const has = paths.length > 0;
        const single = paths.length === 1;
        const entry = root.currentEntry();
        const singleFile = single && entry !== undefined && !entry.dir;
        return [
            { label: "Open", enabled: single, action: function () { root.openSelected(); } },
            { label: "Open With…", enabled: singleFile, action: function () { root.openWithSelected(); } },
            { label: "Rename…", enabled: single, action: function () { root.renameSelected(); } },
            { label: "Copy", enabled: has, action: function () { root.copySelection(); } },
            { label: "Cut", enabled: has, action: function () { root.cutSelection(); } },
            { label: "Paste", enabled: Clipboard.hasItems, action: function () { root.pasteClipboard(); } },
            { label: "New Folder…", enabled: true, action: function () { root.newFolder(); } },
            { label: "New File…", enabled: true, action: function () { root.newFile(); } },
            { label: "Move to Trash", enabled: has, action: function () { root.trashSelection(); } },
            { label: "Delete Permanently…", enabled: has, action: function () { root.deleteSelection(); } },
            { label: "Restore from Trash", enabled: root.inTrash() && has, action: function () { root.restoreSelection(); } },
            { label: "Empty Trash…", enabled: root.inTrash(), action: function () { Ui.askEmptyTrash(); } },
            { label: "Open Trash", enabled: true, action: function () { root.openTrash(); } },
            { label: "Add to Places", enabled: true, action: function () { root.addToPlaces(); } },
            { label: "Select All", enabled: listing.entries.length > 0, action: function () { root.selectAll(); } },
            { label: "Undo", enabled: true, action: function () { root.undoLast(); } },
            { label: "Redo", enabled: true, action: function () { root.redoLast(); } },
            { label: "Properties…", enabled: single, action: function () { root.showProperties(); } },
            { label: "Open Terminal Here", enabled: true, action: function () { root.openTerminal(); } },
            { label: "Open as Root", enabled: true, action: function () { root.openAsRoot(); } },
            { label: "Open Terminal as Root", enabled: true, action: function () { root.openTerminalRoot(); } },
            { label: "Toggle Transfers Tray", enabled: true, action: function () { Config.showTransfers = !Config.showTransfers; } }
        ];
    }

    function showMenu(px, py) {
        menu.items = root.buildMenu();
        menu.openAt(px, py);
    }

    function refreshSoon() {
        refreshTimer.restart();
    }

    function sessionState() {
        return {
            path: root.path,
            activeIndex: root.activeIndex,
            tabs: root.tabs
        };
    }

    function restoreSession(state) {
        if (!state || !state.path)
            return;
        const tabs = (state.tabs && state.tabs.length > 0)
            ? state.tabs
            : [{ path: state.path, history: [state.path], historyIndex: 0 }];
        root.tabs = tabs;
        root.activeIndex = Math.max(0, Math.min(Number(state.activeIndex) || 0, tabs.length - 1));
        const active = tabs[root.activeIndex];
        root.path = (active && active.path) ? active.path : state.path;
        root.history = (active && active.history && active.history.length)
            ? active.history.slice() : [root.path];
        root.historyIndex = (active && typeof active.historyIndex === "number")
            ? active.historyIndex : root.history.length - 1;
        root.selected = ({});
        root.cursor = 0;
        root.anchor = 0;
    }

    function cursorPath() {
        const entry = root.currentEntry();
        return entry ? root.keyFor(entry.name) : "";
    }

    function requestPreview() {
        if (Config.showPreview && root.active)
            Preview.load(root.cursorPath());
    }

    function togglePreview() {
        Config.showPreview = !Config.showPreview;
        if (Config.showPreview)
            root.requestPreview();
        else
            Preview.clear();
    }

    function startFilter() {
        root.filtering = true;
        if (root.filterText.length > 0)
            root.filterQuery = root.filterText;
        Qt.callLater(function () {
            filterField.forceActiveFocus();
            filterField.selectAll();
        });
    }

    function stopFilter() {
        root.filtering = false;
        root.filterText = "";
        root.filterQuery = "";
        root.forceActiveFocus();
    }

    function reveal(target) {
        if (!target)
            return;
        const slash = target.lastIndexOf("/");
        const dir = slash <= 0 ? "/" : target.slice(0, slash);
        root.pendingReveal = target;
        if (dir !== root.path)
            root.navigate(dir);
        else
            root.tryReveal();
    }

    function tryReveal() {
        if (!root.pendingReveal)
            return;
        const index = listing.entries.findIndex(function (entry) {
            return root.keyFor(entry.name) === root.pendingReveal;
        });
        if (index >= 0) {
            root.cursor = index;
            root.selectIndex(index, "single");
            listView.positionViewAtIndex(index, ListView.Contain);
            root.gridView.positionViewAtIndex(index, GridView.Contain);
            root.pendingReveal = "";
            return;
        }
        if (listing.entries.length < listing.total)
            listing.loadMore();
    }

    Keys.onPressed: (event) => {
        if (!root.opKeysEnabled)
            return;
        if (event.key === Qt.Key_Delete) {
            if (event.modifiers & Qt.ShiftModifier)
                root.deleteSelection();
            else
                root.trashSelection();
            event.accepted = true;
        }
    }

    Component.onCompleted: {
        root.history = [root.initialPath];
        root.historyIndex = 0;
        root.path = root.initialPath;
        root.tabs = [{ path: root.initialPath, history: [root.initialPath], historyIndex: 0 }];
        if (root.active)
            root.forceActiveFocus();
    }

    Listing {
        id: listing
        path: root.path
        sortKey: Config.sortKey
        sortDesc: Config.sortDesc
        dirsFirst: Config.dirsFirst
        showHidden: Config.showHidden
        query: root.filterQuery
        onLoaded: {
            if (root.cursor >= listing.entries.length)
                root.cursor = Math.max(0, listing.entries.length - 1);
            root.tryReveal();
            if (Config.showPreview && root.active)
                Preview.load(root.cursorPath());
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: (Config.dualPane && root.active) ? 1 : 0
        border.color: Theme.alpha(Theme.accent, 0.55)
    }

    Timer {
        id: refreshTimer
        interval: 350
        repeat: false
        onTriggered: listing.reload()
    }

    Timer {
        id: filterTimer
        interval: 150
        repeat: false
        onTriggered: root.filterQuery = root.filterText
    }

    onCursorChanged: {
        if (Config.showPreview && root.active)
            Preview.load(root.cursorPath());
    }

    Connections {
        target: Jobs
        function onJobFinished() { root.refreshSoon(); }
    }

    Connections {
        target: Backend
        function onFsEvent(token, dir) {
            if (token === root.watchToken)
                root.refreshSoon();
        }
    }

    onPathChanged: {
        if (root.path)
            Backend.call("watch", { token: root.watchToken, path: root.path });
    }

    MenuPopup {
        id: menu
        x: 0
        y: 0
    }

    MouseArea {
        anchors.fill: parent
        visible: menu.opened
        z: 99
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onClicked: menu.close()
    }

    DropArea {
        anchors.fill: parent
        z: 90
        keys: ["text/uri-list", "application/x-hyprtk-fm-paths"]
        onEntered: (drag) => {
            if (root.debugDrag)
                console.log("fm drop enter", drag.hasUrls, drag.formats);
            if (drag.hasUrls || drag.formats.indexOf("application/x-hyprtk-fm-paths") >= 0)
                root.dropActive = true;
        }
        onExited: root.dropActive = false
        onDropped: (drop) => {
            root.dropActive = false;
            if (root.debugDrag)
                console.log("fm dropped", drop.hasUrls, drop.formats);
            let internalPaths = "";
            try {
                internalPaths = drop.getDataAsString("application/x-hyprtk-fm-paths") || "";
            } catch (e) {
                internalPaths = "";
            }
            let paths = [];
            if (internalPaths.length > 0) {
                paths = internalPaths.split("\n").filter(function (item) { return item.length > 0; });
            } else if (DragState.internal) {
                paths = DragState.paths.slice();
            } else if (drop.hasUrls) {
                for (let i = 0; i < drop.urls.length; i++) {
                    const url = drop.urls[i].toString();
                    if (url.indexOf("file://") === 0)
                        paths.push(decodeURIComponent(url.slice(7)));
                }
            }
            const internal = internalPaths.length > 0 || DragState.internal;
            if (paths.length > 0) {
                Backend.call(internal ? "job.move" : "job.copy", { sources: paths, dest: root.path });
                root.activated();
                const firstName = paths[0].split("/").pop();
                if (firstName)
                    root.pendingReveal = root.join(root.path, firstName);
                root.refreshSoon();
            }
            DragState.clear();
            drop.accept(internal ? Qt.MoveAction : Qt.CopyAction);
        }

        Rectangle {
            anchors.fill: parent
            visible: root.dropActive
            color: Theme.alpha(Theme.accent, 0.08)
            border.width: 2
            border.color: Theme.accent

            Text {
                anchors.centerIn: parent
                text: "Drop here"
                color: Theme.accent
                font.pixelSize: 14
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        acceptedButtons: Qt.LeftButton
        onClicked: {
            root.activated();
            root.selected = ({});
        }
    }

    Rectangle {
        id: tabStrip
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 32
        color: Theme.alpha(Theme.background, 0.65)

        Row {
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            spacing: 2

            Repeater {
                model: root.tabs

                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    height: 28
                    width: Math.min(180, tabLabel.implicitWidth + 42)
                    radius: 7
                    color: index === root.activeIndex ? Theme.surface
                        : (tabHover.hovered ? Theme.alpha(Theme.foreground, 0.06) : "transparent")

                    MouseArea {
                        id: tabHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.loadTab(index);
                            root.activated();
                        }
                    }

                    Text {
                        id: tabLabel
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 42
                        text: root.baseName(modelData.path)
                        color: index === root.activeIndex ? Theme.foreground : Theme.muted
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        visible: root.tabs.length > 1
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18
                        height: 18
                        radius: 9
                        color: closeHover.hovered ? Theme.alpha(Theme.danger, 0.35) : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "×"
                            color: Theme.muted
                            font.pixelSize: 12
                        }

                        MouseArea {
                            id: closeHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.closeTab(index)
                        }
                    }
                }
            }

            IconButton {
                text: "+"
                implicitWidth: 26
                implicitHeight: 26
                onClicked: root.newTab()
            }
        }
    }

    Rectangle {
        id: toolbar
        anchors.top: tabStrip.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 42
        color: Theme.background

        RowLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 4

            PathBar {
                id: pathBar
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                path: root.path
                onNavigate: (target) => {
                    root.activated();
                    root.navigate(target);
                }
                onEditingChanged: {
                    root.editingPath = pathBar.editing;
                    if (!pathBar.editing)
                        root.forceActiveFocus();
                }
            }

            Rectangle {
                visible: root.filtering
                Layout.preferredWidth: 230
                Layout.preferredHeight: 28
                radius: Theme.radius
                color: Theme.alpha(Theme.foreground, 0.06)
                border.width: 1
                border.color: Theme.accent

                TextInput {
                    id: filterField
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.foreground
                    selectionColor: Theme.accent
                    selectedTextColor: Theme.textOnAccent
                    font.pixelSize: Theme.fontSize
                    onTextChanged: {
                        root.filterText = text;
                        filterTimer.restart();
                    }
                    Keys.onEscapePressed: root.stopFilter()
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: filterField.text.length === 0
                    text: "Filter…"
                    color: Theme.alpha(Theme.foreground, 0.35)
                    font.pixelSize: Theme.fontSize
                }
            }

            IconButton {
                text: "⟳"
                onClicked: { root.activated(); root.reload(); }
            }
            IconButton {
                text: root.sortLabel()
                active: true
                onClicked: { root.activated(); Config.cycleSort(); }
            }
            IconButton {
                text: Config.sortDesc ? "↓" : "↑"
                onClicked: { root.activated(); Config.sortDesc = !Config.sortDesc; }
            }
            IconButton {
                text: Config.viewMode === "list" ? "☰" : (Config.viewMode === "grid" ? "▦" : "≣")
                onClicked: { root.activated(); Config.cycleView(); }
            }
            IconButton {
                text: Config.showHidden ? "◉" : "○"
                active: Config.showHidden
                onClicked: { root.activated(); Config.showHidden = !Config.showHidden; }
            }
            IconButton {
                text: "▥"
                active: Config.dualPane
                onClicked: { root.activated(); Config.dualPane = !Config.dualPane; }
            }
            IconButton {
                text: "⌕"
                active: root.filtering
                onClicked: {
                    root.activated();
                    if (root.filtering)
                        root.stopFilter();
                    else
                        root.startFilter();
                }
            }
            IconButton {
                text: "◫"
                active: Config.showPreview
                onClicked: { root.activated(); root.togglePreview(); }
            }
            IconButton {
                text: "⋮"
                onClicked: {
                    root.activated();
                    root.showMenu(8, tabStrip.height + toolbar.height + 4);
                }
            }
        }
    }

    Rectangle {
        id: rootBanner
        visible: Backend.elevated
        anchors.top: toolbar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible ? 26 : 0
        color: Theme.alpha(Theme.danger, 0.16)

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.alpha(Theme.danger, 0.4)
        }

        Text {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            verticalAlignment: Text.AlignVCenter
            text: "Running as root — file operations affect the whole system"
            color: Theme.danger
            font.pixelSize: 11
            font.bold: true
            elide: Text.ElideRight
        }
    }

    Item {
        id: content
        anchors.top: rootBanner.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: statusBar.top
        clip: true

        ListView {
            id: listView
            anchors.fill: parent
            visible: Config.viewMode === "list"
            model: listing.entries
            clip: true
            cacheBuffer: 600
            currentIndex: root.cursor
            boundsBehavior: Flickable.StopAtBounds
            onContentYChanged: {
                if (contentY + height > contentHeight - 700)
                    listing.loadMore();
            }

            delegate: Rectangle {
                id: rowItem
                required property var modelData
                required property int index
                width: listView.width
                height: 28
                Item {
                    id: dragProxy
                    width: 1
                    height: 1
                }
                color: root.isSelected(modelData.name)
                    ? Theme.alpha(Theme.accent, 0.22)
                    : (index === root.cursor && root.active ? Theme.alpha(Theme.accent2, 0.10) : "transparent")

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18
                        height: 18
                        sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
                        source: Quickshell.iconPath(modelData.icon, "text-x-generic")
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 300
                        text: modelData.name
                        color: Theme.foreground
                        font.pixelSize: Theme.fontSize
                        elide: Text.ElideMiddle
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 90
                        horizontalAlignment: Text.AlignRight
                        text: modelData.dir ? "" : root.humanSize(modelData.size)
                        color: Theme.muted
                        font.pixelSize: Theme.fontSize - 1
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 150
                        horizontalAlignment: Text.AlignRight
                        text: root.fmtDate(modelData.mtime)
                        color: Theme.muted
                        font.pixelSize: Theme.fontSize - 1
                    }
                }

                MouseArea {
                    id: dragMouse
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    preventStealing: true
                    drag.target: dragProxy
                    Drag.active: dragMouse.drag.active
                    Drag.dragType: Drag.Automatic
                    Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
                    Drag.mimeData: ({
                        "text/uri-list": root.dragUrls(modelData.name).join("\r\n"),
                        "application/x-hyprtk-fm-paths": root.dragPaths(modelData.name).join("\n")
                    })
                    Drag.hotSpot: Qt.point(10, 10)
                    Drag.onActiveChanged: {
                        if (root.debugDrag)
                            console.log("fm drag", Drag.active, root.dragPaths(modelData.name).join(","));
                        if (Drag.active) {
                            DragState.begin(root.watchToken, root.dragPaths(modelData.name));
                            if (!root.isSelected(modelData.name))
                                root.selectIndex(index, "single");
                        } else {
                            DragState.clearSoon();
                        }
                    }
                    onPressed: (mouse) => {
                        if (mouse.button === Qt.LeftButton)
                            root.activated();
                    }
                    onClicked: (mouse) => {
                        if (mouse.button === Qt.RightButton) {
                            if (!root.isSelected(modelData.name))
                                root.selectIndex(index, "single");
                            const point = mapToItem(root, mouse.x, mouse.y);
                            root.showMenu(point.x, point.y);
                            return;
                        }
                        root.activated();
                        const mode = (mouse.modifiers & Qt.ControlModifier) ? "toggle"
                            : (mouse.modifiers & Qt.ShiftModifier) ? "range" : "single";
                        root.selectIndex(index, mode);
                    }
                    onDoubleClicked: root.openEntry(modelData)
                }
            }
        }

        GridView {
            id: gridView
            anchors.fill: parent
            visible: Config.viewMode !== "list"
            model: listing.entries
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: Config.viewMode === "compact" ? Math.max(150, content.width / 4) : 120
            cellHeight: Config.viewMode === "compact" ? 30 : 96
            currentIndex: root.cursor
            onContentYChanged: {
                if (contentY + height > contentHeight - 700)
                    listing.loadMore();
            }

            delegate: Rectangle {
                id: rowItem
                required property var modelData
                required property int index
                width: gridView.cellWidth
                height: gridView.cellHeight
                Item {
                    id: dragProxy
                    width: 1
                    height: 1
                }
                radius: 8
                color: root.isSelected(modelData.name)
                    ? Theme.alpha(Theme.accent, 0.22)
                    : (index === root.cursor && root.active ? Theme.alpha(Theme.accent2, 0.10) : "transparent")

                Row {
                    visible: Config.viewMode === "compact"
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    spacing: 8

                    Image {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16
                        height: 16
                        sourceSize: Qt.size(Theme.iconSource, Theme.iconSource)
                        source: Quickshell.iconPath(modelData.icon, "text-x-generic")
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 24
                        text: modelData.name
                        color: Theme.foreground
                        font.pixelSize: Theme.fontSize - 1
                        elide: Text.ElideMiddle
                    }
                }

                Column {
                    visible: Config.viewMode === "grid"
                    anchors.centerIn: parent
                    spacing: 6

                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Config.iconSize * 2.2
                        height: Config.iconSize * 2.2
                        sourceSize: Qt.size(Math.max(Theme.iconSource, Math.ceil(Config.iconSize * 2.2)),
                                            Math.max(Theme.iconSource, Math.ceil(Config.iconSize * 2.2)))
                        source: Quickshell.iconPath(modelData.icon, "text-x-generic")
                    }

                    Text {
                        width: gridView.cellWidth - 12
                        text: modelData.name
                        color: Theme.foreground
                        font.pixelSize: Theme.fontSize - 1
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideMiddle
                    }
                }

                MouseArea {
                    id: dragMouse
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    preventStealing: true
                    drag.target: dragProxy
                    Drag.active: dragMouse.drag.active
                    Drag.dragType: Drag.Automatic
                    Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
                    Drag.mimeData: ({
                        "text/uri-list": root.dragUrls(modelData.name).join("\r\n"),
                        "application/x-hyprtk-fm-paths": root.dragPaths(modelData.name).join("\n")
                    })
                    Drag.hotSpot: Qt.point(10, 10)
                    Drag.onActiveChanged: {
                        if (root.debugDrag)
                            console.log("fm drag", Drag.active, root.dragPaths(modelData.name).join(","));
                        if (Drag.active) {
                            DragState.begin(root.watchToken, root.dragPaths(modelData.name));
                            if (!root.isSelected(modelData.name))
                                root.selectIndex(index, "single");
                        } else {
                            DragState.clearSoon();
                        }
                    }
                    onPressed: (mouse) => {
                        if (mouse.button === Qt.LeftButton)
                            root.activated();
                    }
                    onClicked: (mouse) => {
                        if (mouse.button === Qt.RightButton) {
                            if (!root.isSelected(modelData.name))
                                root.selectIndex(index, "single");
                            const point = mapToItem(root, mouse.x, mouse.y);
                            root.showMenu(point.x, point.y);
                            return;
                        }
                        root.activated();
                        const mode = (mouse.modifiers & Qt.ControlModifier) ? "toggle"
                            : (mouse.modifiers & Qt.ShiftModifier) ? "range" : "single";
                        root.selectIndex(index, mode);
                    }
                    onDoubleClicked: root.openEntry(modelData)
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: !listing.loading && listing.entries.length === 0
            text: listing.error ? listing.error : "Empty folder"
            color: listing.error ? Theme.danger : Theme.muted
            font.pixelSize: Theme.fontSize + 1
        }

        MouseArea {
            id: marqueeArea
            anchors.fill: parent
            z: 20
            acceptedButtons: Qt.LeftButton | Qt.RightButton

            property bool active: false
            property bool moved: false
            property bool additive: false
            property point start
            property point current

            onPressed: (mouse) => {
                const view = root.currentView();
                const index = view ? view.indexAt(mouse.x + view.contentX, mouse.y + view.contentY) : -1;
                if (mouse.button === Qt.RightButton) {
                    if (index >= 0) {
                        mouse.accepted = false;
                        return;
                    }
                    root.activated();
                    root.selected = ({});
                    const point = mapToItem(root, mouse.x, mouse.y);
                    root.showMenu(point.x, point.y);
                    mouse.accepted = true;
                    return;
                }
                if (index >= 0 && !(mouse.modifiers & Qt.ShiftModifier)) {
                    mouse.accepted = false;
                    return;
                }
                root.activated();
                active = true;
                moved = false;
                additive = !!(mouse.modifiers & Qt.ControlModifier);
                start = Qt.point(mouse.x, mouse.y);
                current = start;
                if (!additive)
                    root.selected = ({});
                if (view)
                    view.interactive = false;
            }

            onPositionChanged: (mouse) => {
                if (!active)
                    return;
                current = Qt.point(mouse.x, mouse.y);
                if (Math.abs(current.x - start.x) > 3 || Math.abs(current.y - start.y) > 3)
                    moved = true;
                if (moved)
                    root.applyMarquee(start, current, additive);
            }

            onReleased: (mouse) => {
                if (!active)
                    return;
                active = false;
                const view = root.currentView();
                if (view)
                    view.interactive = true;
                if (moved)
                    root.applyMarquee(start, current, additive);
                else if (!additive)
                    root.selected = ({});
            }

            onCanceled: {
                active = false;
                const view = root.currentView();
                if (view)
                    view.interactive = true;
            }
        }

        Rectangle {
            visible: marqueeArea.active
            x: Math.min(marqueeArea.start.x, marqueeArea.current.x)
            y: Math.min(marqueeArea.start.y, marqueeArea.current.y)
            width: Math.abs(marqueeArea.current.x - marqueeArea.start.x)
            height: Math.abs(marqueeArea.current.y - marqueeArea.start.y)
            color: Theme.alpha(Theme.accent, 0.12)
            border.width: 1
            border.color: Theme.accent
            z: 21
        }
    }

    Rectangle {
        id: statusBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 24
        color: Theme.alpha(Theme.background, 0.75)

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: listing.error
                ? listing.error
                : (listing.total + " items" + (root.selectedCount > 0 ? " · " + root.selectedCount + " selected" : ""))
            color: listing.error ? Theme.danger : Theme.muted
            font.pixelSize: 11
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(parent.width * 0.55, implicitWidth)
            horizontalAlignment: Text.AlignRight
            text: root.path
            color: Theme.muted
            font.pixelSize: 11
            elide: Text.ElideMiddle
        }
    }

    Shortcut {
        sequence: "Ctrl+L"
        enabled: root.opKeysEnabled
        onActivated: pathBar.startEdit()
    }
    Shortcut {
        sequence: "Backspace"
        enabled: root.opKeysEnabled
        onActivated: root.goUp()
    }
    Shortcut {
        sequence: "Alt+Left"
        enabled: root.opKeysEnabled
        onActivated: root.goBack()
    }
    Shortcut {
        sequence: "Alt+Right"
        enabled: root.opKeysEnabled
        onActivated: root.goForward()
    }
    Shortcut {
        sequence: "F5"
        enabled: root.opKeysEnabled
        onActivated: root.reload()
    }
    Shortcut {
        sequence: "Ctrl+H"
        enabled: root.opKeysEnabled
        onActivated: Config.showHidden = !Config.showHidden
    }
    Shortcut {
        sequence: "Ctrl+T"
        enabled: root.opKeysEnabled
        onActivated: root.newTab()
    }
    Shortcut {
        sequence: "Ctrl+W"
        enabled: root.opKeysEnabled
        onActivated: root.closeTab(root.activeIndex)
    }
    Shortcut {
        sequence: "Up"
        enabled: root.opKeysEnabled
        onActivated: root.moveCursor(-1)
    }
    Shortcut {
        sequence: "Down"
        enabled: root.opKeysEnabled
        onActivated: root.moveCursor(1)
    }
    Shortcut {
        sequence: "Home"
        enabled: root.opKeysEnabled
        onActivated: root.moveCursor(-listing.entries.length)
    }
    Shortcut {
        sequence: "End"
        enabled: root.opKeysEnabled
        onActivated: root.moveCursor(listing.entries.length)
    }
    Shortcut {
        sequence: "Return"
        enabled: root.opKeysEnabled
        onActivated: root.openEntry(listing.entries[root.cursor])
    }
    Shortcut {
        sequence: "Space"
        enabled: root.opKeysEnabled
        onActivated: root.togglePreview()
    }
    Shortcut {
        sequence: "Ctrl+Space"
        enabled: root.opKeysEnabled
        onActivated: root.selectIndex(root.cursor, "toggle")
    }
    Shortcut {
        sequence: "Ctrl+F"
        enabled: root.opKeysEnabled
        onActivated: root.startFilter()
    }
    Shortcut {
        sequence: "Ctrl+C"
        enabled: root.opKeysEnabled
        onActivated: root.copySelection()
    }
    Shortcut {
        sequence: "Ctrl+X"
        enabled: root.opKeysEnabled
        onActivated: root.cutSelection()
    }
    Shortcut {
        sequence: "Ctrl+V"
        enabled: root.opKeysEnabled
        onActivated: root.pasteClipboard()
    }
    Shortcut {
        sequence: "Ctrl+A"
        enabled: root.opKeysEnabled
        onActivated: root.selectAll()
    }

    Shortcut {
        sequence: "F2"
        enabled: root.opKeysEnabled
        onActivated: root.renameSelected()
    }
    Shortcut {
        sequence: "Ctrl+Shift+N"
        enabled: root.opKeysEnabled
        onActivated: root.newFolder()
    }
    Shortcut {
        sequence: "Ctrl+Alt+N"
        enabled: root.opKeysEnabled
        onActivated: root.newFile()
    }
    Shortcut {
        sequence: "Ctrl+Shift+E"
        enabled: root.opKeysEnabled && root.inTrash()
        onActivated: Ui.askEmptyTrash()
    }
    Shortcut {
        sequence: "Ctrl+Z"
        enabled: root.opKeysEnabled
        onActivated: root.undoLast()
    }
    Shortcut {
        sequence: "Ctrl+Shift+Z"
        enabled: root.opKeysEnabled
        onActivated: root.redoLast()
    }
    Shortcut {
        sequence: "Alt+Return"
        enabled: root.opKeysEnabled
        onActivated: root.showProperties()
    }
}
