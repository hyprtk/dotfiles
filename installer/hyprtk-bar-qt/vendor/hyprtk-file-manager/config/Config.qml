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

    function cycleSort() {
        const order = ["name", "size", "mtime", "type"];
        const index = order.indexOf(root.sortKey);
        root.sortKey = order[(index + 1) % order.length];
    }

    function values() {
        return {
            viewMode: root.viewMode,
            showHidden: root.showHidden,
            showFilter: root.showFilter,
            iconSize: root.iconSize,
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
        if (Array.isArray(values.hiddenMenuItems))
            root.hiddenMenuItems = values.hiddenMenuItems.filter(function (key) {
                return typeof key === "string";
            });
        if (Array.isArray(values.menuOrder))
            root.menuOrder = values.menuOrder.filter(function (key) {
                return typeof key === "string";
            });
        if (Array.isArray(values.placesOrder))
            root.placesOrder = values.placesOrder.filter(function (key) {
                return typeof key === "string";
            });
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
