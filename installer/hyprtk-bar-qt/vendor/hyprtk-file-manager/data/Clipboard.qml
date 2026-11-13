pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    // Cache of the shared (Wayland) clipboard selection. The system clipboard
    // is the source of truth; this only mirrors it for the UI.
    property string mode: ""
    property var paths: []

    readonly property bool hasItems: root.paths.length > 0

    property var _callbacks: ({})

    function _apply(result) {
        if (!result || result.kind !== "clipboard" || result.paths === undefined)
            return;
        root.mode = result.mode || "";
        root.paths = result.paths || [];
    }

    function load(callback) {
        const id = Backend.call("clipboard.get", {});
        if (callback)
            root._callbacks[id] = callback;
    }

    function refresh() {
        root.load(null);
    }

    function copy(list) {
        const items = (list || []).slice();
        root.mode = "copy";
        root.paths = items;
        Backend.call("clipboard.set", { paths: items, cut: false });
    }

    function cut(list) {
        const items = (list || []).slice();
        root.mode = "cut";
        root.paths = items;
        Backend.call("clipboard.set", { paths: items, cut: true });
    }

    function clear() {
        root.mode = "";
        root.paths = [];
        Backend.call("clipboard.clear", {});
    }

    Component.onCompleted: root.refresh()

    Connections {
        target: Backend
        function onResponse(id, result) {
            root._apply(result);
            const callback = root._callbacks[id];
            if (callback) {
                delete root._callbacks[id];
                callback(result || ({ kind: "clipboard", mode: root.mode, paths: root.paths }));
            }
        }
        function onFailure(id, message) {
            const callback = root._callbacks[id];
            if (callback) {
                delete root._callbacks[id];
                callback({ kind: "clipboard", mode: root.mode, paths: root.paths });
            }
        }
    }
}
