import QtQuick
import "../data"

Item {
    id: root

    property string path: ""
    property string sortKey: "name"
    property bool sortDesc: false
    property bool dirsFirst: true
    property bool showHidden: false
    property string query: ""
    property int pageSize: 300

    property var entries: []
    property int total: 0
    property bool loading: false
    property string error: ""
    property int pendingId: -1
    property int pendingOffset: 0

    signal loaded()

    function reload() {
        if (!root.path)
            return;
        root.entries = [];
        root.total = 0;
        root.error = "";
        root.loading = false;
        root.pendingId = -1;
        root.fetch(0);
    }

    function fetch(offset) {
        if (!root.path || root.loading)
            return;
        root.loading = true;
        root.pendingOffset = offset;
        root.pendingId = Backend.call("list", {
            path: root.path,
            offset: offset,
            limit: root.pageSize,
            sort: root.sortKey,
            desc: root.sortDesc,
            dirsFirst: root.dirsFirst,
            hidden: root.showHidden,
            query: root.query
        });
    }

    function loadMore() {
        if (root.loading || root.entries.length >= root.total)
            return;
        root.fetch(root.entries.length);
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            root.loading = false;
            if (!result || result.kind !== "list")
                return;
            if (root.pendingOffset === 0)
                root.entries = result.entries;
            else
                root.entries = root.entries.concat(result.entries);
            root.total = result.total;
            root.loaded();
        }
        function onFailure(id, message) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            root.loading = false;
            root.error = message;
        }
    }

    onPathChanged: reload()
    onSortKeyChanged: reload()
    onSortDescChanged: reload()
    onDirsFirstChanged: reload()
    onShowHiddenChanged: reload()
    onQueryChanged: reload()
}
