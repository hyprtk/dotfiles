pragma Singleton

import QtQuick
import Quickshell
import "../data"

Singleton {
    id: root

    readonly property string startPath:
        Quickshell.env("HYPRTK_FM_START") || Quickshell.env("HOME") || "/"

    property string viewMode: {
        const value = Quickshell.env("HYPRTK_FM_VIEW") || "list";
        return ["list", "grid", "compact"].indexOf(value) >= 0 ? value : "list";
    }
    property bool showHidden: false
    property bool showFilter: true
    property int iconSize: 20
    property int sidebarIconSize: 16
    property string sortKey: "name"
    property bool sortDesc: false
    property bool dirsFirst: true
    property bool dualPane: Quickshell.env("HYPRTK_FM_DUAL") === "1"
    property bool showPreview: false
    property bool showTransfers: true
    property bool thumbnails: true
    property var hiddenMenuItems: []
    property var menuOrder: []
    property var placesOrder: []

    property bool _loaded: false
    property int _loadId: -1

    function cycleView() {
        const order = ["list", "grid", "compact"];
        const index = order.indexOf(root.viewMode);
        root.viewMode = order[(index + 1) % order.length];
    }

    // Ctrl+wheel icon step (12–64), shared by the list and grid delegates.
    function stepIconSize(delta) {
        const step = delta > 0 ? 4 : -4;
        root.iconSize = Math.max(12, Math.min(64, root.iconSize + step));
    }

    function cycleSort() {
        const order = ["name", "size", "mtime", "type"];
        const index = order.indexOf(root.sortKey);
        root.sortKey = order[(index + 1) % order.length];
    }

    // Arrays that come back from the backend arrive as QVariant lists, which
    // `Array.isArray()` rejects, so normalise them into real arrays of strings.
    // Returns null when the value is not a list (nothing to apply).
    function _stringList(value) {
        if (!value || typeof value.length !== "number")
            return null;
        const items = Array.prototype.slice.call(value, 0);
        const out = [];
        for (let i = 0; i < items.length; i++) {
            if (typeof items[i] === "string")
                out.push(items[i]);
        }
        return out;
    }

    function values() {
        return {
            viewMode: root.viewMode,
            showHidden: root.showHidden,
            showFilter: root.showFilter,
            iconSize: root.iconSize,
            sidebarIconSize: root.sidebarIconSize,
            sortKey: root.sortKey,
            sortDesc: root.sortDesc,
            dirsFirst: root.dirsFirst,
            dualPane: root.dualPane,
            showPreview: root.showPreview,
            showTransfers: root.showTransfers,
            thumbnails: root.thumbnails,
            hiddenMenuItems: root.hiddenMenuItems,
            menuOrder: root.menuOrder,
            placesOrder: root.placesOrder
        };
    }

    function apply(values) {
        if (!values)
            return;
        root._loaded = false;
        if (["list", "grid", "compact"].indexOf(values.viewMode) >= 0)
            root.viewMode = values.viewMode;
        if (typeof values.showHidden === "boolean")
            root.showHidden = values.showHidden;
        if (typeof values.showFilter === "boolean")
            root.showFilter = values.showFilter;
        if (typeof values.iconSize === "number")
            root.iconSize = Math.max(12, Math.min(64, values.iconSize));
        if (typeof values.sidebarIconSize === "number")
            root.sidebarIconSize = Math.max(12, Math.min(32, values.sidebarIconSize));
        if (["name", "size", "mtime", "type"].indexOf(values.sortKey) >= 0)
            root.sortKey = values.sortKey;
        if (typeof values.sortDesc === "boolean")
            root.sortDesc = values.sortDesc;
        if (typeof values.dirsFirst === "boolean")
            root.dirsFirst = values.dirsFirst;
        if (typeof values.dualPane === "boolean")
            root.dualPane = values.dualPane;
        if (typeof values.showPreview === "boolean")
            root.showPreview = values.showPreview;
        if (typeof values.showTransfers === "boolean")
            root.showTransfers = values.showTransfers;
        if (typeof values.thumbnails === "boolean")
            root.thumbnails = values.thumbnails;
        const hiddenMenuItems = root._stringList(values.hiddenMenuItems);
        if (hiddenMenuItems !== null)
            root.hiddenMenuItems = hiddenMenuItems;
        const menuOrder = root._stringList(values.menuOrder);
        if (menuOrder !== null)
            root.menuOrder = menuOrder;
        const placesOrder = root._stringList(values.placesOrder);
        if (placesOrder !== null)
            root.placesOrder = placesOrder;
        root._loaded = true;
    }

    function save() {
        if (root._loaded)
            Backend.call("config.set", { values: root.values() });
    }

    function scheduleSave() {
        if (root._loaded)
            saveTimer.restart();
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root._loadId)
                return;
            root._loadId = -1;
            root.apply(result && result.values ? result.values : ({}));
            root._loaded = true;
            loadTimeout.stop();
        }
    }

    Timer {
        id: saveTimer
        interval: 350
        repeat: false
        onTriggered: root.save()
    }

    Timer {
        id: loadTimeout
        interval: 2500
        repeat: false
        running: true
        onTriggered: root._loaded = true
    }

    Component.onCompleted: root._loadId = Backend.call("config.get", {})

    onViewModeChanged: root.scheduleSave()
    onShowHiddenChanged: root.scheduleSave()
    onShowFilterChanged: root.scheduleSave()
    onIconSizeChanged: root.scheduleSave()
    onSidebarIconSizeChanged: root.scheduleSave()
    onSortKeyChanged: root.scheduleSave()
    onSortDescChanged: root.scheduleSave()
    onDirsFirstChanged: root.scheduleSave()
    onDualPaneChanged: root.scheduleSave()
    onShowPreviewChanged: root.scheduleSave()
    onShowTransfersChanged: root.scheduleSave()
    onThumbnailsChanged: root.scheduleSave()
    onHiddenMenuItemsChanged: root.scheduleSave()
    onMenuOrderChanged: root.scheduleSave()
    onPlacesOrderChanged: root.scheduleSave()
}
