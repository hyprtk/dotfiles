pragma Singleton

import QtQuick
import Quickshell
import "."

Singleton {
    id: root

    property string path: ""
    property var data: ({})
    property bool loading: false
    property int pendingId: -1

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            root.loading = false;
            root.data = result || ({});
        }
        function onFailure(id, message) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            root.loading = false;
            root.data = { kind: "binary", error: message, meta: {} };
        }
    }

    function load(target) {
        if (!target) {
            root.clear();
            return;
        }
        if (target === root.path && root.data && root.data.kind)
            return;
        root.path = target;
        root.loading = true;
        root.pendingId = Backend.call("preview", { path: target });
    }

    function clear() {
        root.path = "";
        root.data = ({});
        root.loading = false;
        root.pendingId = -1;
    }
}
