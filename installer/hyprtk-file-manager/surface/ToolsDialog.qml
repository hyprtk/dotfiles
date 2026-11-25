// Folder tools: disk-usage treemap, duplicate finder and folder comparison.
import QtQuick
import Quickshell
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    property string mode: "usage"
    property string rootPath: ""
    property string otherPath: ""
    property var usageItems: []
    property var groups: []
    property var comparison: ({})
    property string status: ""
    property int requestId: -1

    signal closed()

    anchors.fill: parent
    visible: false
    z: 243
    focus: visible

    function openUsage(path) {
        root.mode = "usage";
        root.rootPath = path;
        root.usageItems = [];
        root.status = "";
        root.visible = true;
        root.requestId = Backend.call("tools.usage", { path: path });
    }

    function openDuplicates(path) {
        root.mode = "duplicates";
        root.rootPath = path;
        root.groups = [];
        root.status = "Hashing files…";
        root.visible = true;
        root.requestId = Backend.call("tools.duplicates", { path: path });
    }

    function openCompare(left, right) {
        root.mode = "compare";
        root.rootPath = left;
        root.otherPath = right;
        root.comparison = ({});
        root.status = "Comparing…";
        root.visible = true;
        root.requestId = Backend.call("tools.compare", { left: left, right: right });
    }

    function dismiss() {
        root.visible = false;
        root.requestId = -1;
        Ui.close();
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    function humanSize(bytes) {
        if (!bytes || bytes <= 0)
            return "0 B";
        const units = ["B", "K", "M", "G", "T"];
        let value = bytes;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
            value /= 1024;
            unit += 1;
        }
        return (unit === 0 ? value : value.toFixed(1)) + " " + units[unit];
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root.requestId)
                return;
            root.requestId = -1;
            if (root.mode === "usage") {
                root.usageItems = (result && result.items) || [];
                treemap.requestPaint();
                root.status = root.humanSize((result && result.total) || 0) + " in " +
                              root.usageItems.length + " entries";
            } else if (root.mode === "duplicates") {
                root.groups = (result && result.groups) || [];
                root.status = root.groups.length + " duplicate group(s), " +
                              root.humanSize((result && result.wasted) || 0) + " wasted";
            } else {
                root.comparison = result || ({});
                const counts = (result && result.counts) || ({});
                root.status = (counts.only_left || 0) + " only left · " +
                              (counts.only_right || 0) + " only right · " +
                              (counts.differing || 0) + " differ · " +
                              (counts.same || 0) + " same";
            }
        }
        function onFailure(id, message) {
            if (id !== root.requestId)
                return;
            root.requestId = -1;
            root.status = message;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45
        MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(880, parent.width - 80)
        height: Math.min(660, parent.height - 80)
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            Text {
                text: root.mode === "usage" ? "Disk usage — " + root.rootPath
                    : root.mode === "duplicates" ? "Duplicates — " + root.rootPath
                    : "Compare — " + root.rootPath + " ↔ " + root.otherPath
                color: Theme.accent
                font.pixelSize: Theme.size(4)
                font.bold: true
                elide: Text.ElideMiddle
                width: parent.width
            }

            Canvas {
                id: treemap
                visible: root.mode === "usage"
                width: parent.width
                height: parent.height - 100

                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    ctx.fillStyle = Theme.background;
                    ctx.fillRect(0, 0, width, height);

                    const items = root.usageItems;
                    if (items.length === 0)
                        return;

                    let x = 0, y = 0, w = width, h = height;
                    const total = items.reduce((sum, item) => sum + item.size, 0) || 1;
                    const scale = (w * h) / total;
                    const pending = items.map(item => ({ name: item.name, size: item.size,
                                                         area: item.size * scale, rect: null }));

                    function worst(row, side) {
                        if (row.length === 0)
                            return Infinity;
                        const sum = row.reduce((a, b) => a + b.area, 0);
                        const max = Math.max.apply(null, row.map(i => i.area));
                        const min = Math.min.apply(null, row.map(i => i.area));
                        return Math.max((side * side * max) / (sum * sum),
                                        (sum * sum) / (side * side * min));
                    }

                    const placed = [];
                    while (pending.length > 0) {
                        const horizontal = w >= h;
                        const side = Math.min(w, h);
                        const current = [];
                        while (pending.length > 0) {
                            const candidate = current.concat([pending[0]]);
                            if (current.length > 0 && worst(candidate, side) > worst(current, side))
                                break;
                            current.push(pending.shift());
                        }
                        const sum = current.reduce((a, b) => a + b.area, 0) || 1;
                        if (horizontal) {
                            const rowHeight = sum / w;
                            let cursor = x;
                            for (const item of current) {
                                const cellWidth = item.area / rowHeight;
                                item.rect = [cursor, y, cellWidth, rowHeight];
                                cursor += cellWidth;
                            }
                            y += rowHeight;
                            h -= rowHeight;
                        } else {
                            const rowWidth = sum / h;
                            let cursor = y;
                            for (const item of current) {
                                const cellHeight = item.area / rowWidth;
                                item.rect = [x, cursor, rowWidth, cellHeight];
                                cursor += cellHeight;
                            }
                            x += rowWidth;
                            w -= rowWidth;
                        }
                        for (const item of current)
                            placed.push(item);
                    }

                    const palette = ["#fd4fb6", "#02dede", "#5fb8f5", "#f5c15f",
                                     "#7bd88f", "#c084fc"];
                    for (let i = 0; i < placed.length; i++) {
                        const item = placed[i];
                        const rect = item.rect;
                        if (!rect)
                            continue;
                        ctx.globalAlpha = 0.78;
                        ctx.fillStyle = palette[i % palette.length];
                        ctx.fillRect(rect[0] + 1, rect[1] + 1,
                                     Math.max(0, rect[2] - 2), Math.max(0, rect[3] - 2));
                        ctx.globalAlpha = 1;
                        if (rect[2] > 76 && rect[3] > 18) {
                            ctx.fillStyle = "#0b0b12";
                            ctx.font = "11px sans-serif";
                            const label = item.name.slice(0, Math.max(3, Math.floor(rect[2] / 7)));
                            ctx.fillText(label, rect[0] + 5, rect[1] + 14);
                        }
                    }
                }
            ListView {
                visible: root.mode === "duplicates"
                width: parent.width
                height: parent.height - 100
                clip: true
                model: root.groups
                spacing: 6

                delegate: Column {
                    required property var modelData
                    width: ListView.view.width
                    spacing: 2
                    Text {
                        text: root.humanSize(modelData.size) + " · " +
                              modelData.paths.length + " copies"
                        color: Theme.accent2
                        font.pixelSize: Theme.size(2)
                        font.bold: true
                    }
                    Repeater {
                        model: modelData.paths
                        delegate: Text {
                            required property var modelData
                            text: modelData
                            color: Theme.dim
                            font.pixelSize: Theme.size(1)
                            elide: Text.ElideMiddle
                            width: ListView.view.width
                        }
                    }
                }
            }

            Flickable {
                visible: root.mode === "compare"
                width: parent.width
                height: parent.height - 100
                clip: true
                contentHeight: compareColumn.implicitHeight

                Column {
                    id: compareColumn
                    width: parent.width
                    spacing: 4
                    Text {
                        text: "Only in the left folder"
                        color: Theme.accent2
                        font.pixelSize: Theme.size(2)
                    }
                    Repeater {
                        model: (root.comparison && root.comparison.only_left) || []
                        delegate: Text {
                            required property var modelData
                            text: modelData
                            color: Theme.dim
                            font.pixelSize: Theme.size(1)
                        }
                    }
                    Text {
                        text: "Only in the right folder"
                        color: Theme.accent2
                        font.pixelSize: Theme.size(2)
                    }
                    Repeater {
                        model: (root.comparison && root.comparison.only_right) || []
                        delegate: Text {
                            required property var modelData
                            text: modelData
                            color: Theme.dim
                            font.pixelSize: Theme.size(1)
                        }
                    }
                    Text {
                        text: "Different contents"
                        color: Theme.accent2
                        font.pixelSize: Theme.size(2)
                    }
                    Repeater {
                        model: (root.comparison && root.comparison.differing) || []
                        delegate: Text {
                            required property var modelData
                            text: modelData
                            color: Theme.dim
                            font.pixelSize: Theme.size(1)
                        }
                    }
                }
            }

            Text {
                width: parent.width
                text: root.status
                color: Theme.dim
                font.pixelSize: Theme.size(1)
                elide: Text.ElideRight
            }

            Row {
                spacing: 8
                TButton { text: "Close"; onClicked: root.dismiss() }
            }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
