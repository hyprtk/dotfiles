import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "components"
import "theme/util.js" as Util

// Command palette (Ctrl+K). The card itself lives in components/PickerCard.qml
// so the quick-open picker cannot drift from it.
Rectangle {
    id: root

    property var actions: []
    property var filtered: []

    readonly property var th: Bridge.palette

    signal closed()

    anchors.fill: parent
    z: 450
    visible: false
    color: Util.alpha(root.th.background, 0.55)

    function open(list) {
        root.actions = list || [];
        root.visible = true;
        root.reindex("");
        card.reset();
    }

    function close() {
        root.visible = false;
        root.closed();
    }

    function reindex(text) {
        var needle = String(text || "").toLowerCase();
        var out = [];
        for (var i = 0; i < root.actions.length; i++) {
            var action = root.actions[i];
            if (needle.length === 0 || action.label.toLowerCase().indexOf(needle) >= 0
                || (action.keywords && action.keywords.toLowerCase().indexOf(needle) >= 0))
                out.push(action);
        }
        root.filtered = out.slice(0, 60);
    }

    function run(index) {
        if (index < 0 || index >= root.filtered.length)
            return;
        var action = root.filtered[index];
        root.close();
        if (typeof action.run === "function")
            action.run();
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    PickerCard {
        id: card
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 90
        width: Math.min(600, root.width - 80)
        height: Math.min(430, root.height - 120)
        placeholder: "Type a command…"
        items: root.filtered
        footer: root.filtered.length + " command(s)   ·   ↑↓ move   ·   Enter run   ·   Esc close"
        emptyText: "No matching command"
        onEdited: function (text) { root.reindex(text); }
        onChosen: function (index) { root.run(index); }
        onDismissed: root.close()
    }
}
