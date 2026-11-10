pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property string mode: ""
    property var paths: []

    readonly property bool hasItems: root.paths.length > 0

    function copy(list) {
        root.mode = "copy";
        root.paths = list.slice();
    }

    function cut(list) {
        root.mode = "cut";
        root.paths = list.slice();
    }

    function clear() {
        root.mode = "";
        root.paths = [];
    }
}
