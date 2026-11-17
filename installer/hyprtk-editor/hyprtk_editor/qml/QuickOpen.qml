import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "components"
import "theme/util.js" as Util

// Quick open (Ctrl+P): recents, the current folder, and the documents that are
// already open. Ranking is Bridge.rankFiles (search.fuzzy_score), so the order
// is testable without a display.
Rectangle {
    id: root

    // Raw candidates: {path, name, folder, source}.
    property var all: []
    // Decorated rows for the card: {label, detail, hint, path}.
    property var filtered: []

    readonly property var th: Bridge.palette

    signal chosen(string path)

    anchors.fill: parent
    z: 440
    visible: false
    color: Util.alpha(root.th.background, 0.55)

    function decorate(rows) {
        var out = [];
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            var hint = "";
            if (row.source === "recent")
                hint = "recent";
            else if (row.source === "open")
                hint = "open";
            out.push({
                label: row.name || row.path,
                detail: row.folder || "",
                hint: hint,
                path: row.path
            });
        }
        return out;
    }

    function open(list) {
        root.all = list || [];
        root.visible = true;
        root.reindex("");
        card.reset();
    }

    function close() {
        root.visible = false;
    }

    function reindex(text) {
        root.filtered = root.decorate(Bridge.rankFiles(root.all, text));
    }

    function activate(index) {
        if (index < 0 || index >= root.filtered.length)
            return;
        var path = root.filtered[index].path;
        root.close();
        if (path)
            root.chosen(path);
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
        width: Math.min(620, root.width - 80)
        height: Math.min(430, root.height - 120)
        placeholder: "Open a file — name or path"
        items: root.filtered
        footer: root.filtered.length + " file(s)   ·   ↑↓ move   ·   Enter open   ·   Esc close"
        emptyText: "No file matches"
        onEdited: function (text) { root.reindex(text); }
        onChosen: function (index) { root.activate(index); }
        onDismissed: root.close()
    }
}
