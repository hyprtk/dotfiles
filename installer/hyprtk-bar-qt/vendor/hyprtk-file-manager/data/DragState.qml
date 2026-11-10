pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property bool internal: false
    property string sourcePane: ""
    property var paths: []

    Timer {
        id: resetTimer
        interval: 400
        repeat: false
        onTriggered: root.clear()
    }

    function begin(source, list) {
        root.internal = true;
        root.sourcePane = source;
        root.paths = list.slice();
        resetTimer.stop();
    }

    function clearSoon() {
        resetTimer.restart();
    }

    function clear() {
        root.internal = false;
        root.sourcePane = "";
        root.paths = [];
    }
}
