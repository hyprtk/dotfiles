// Renders one form row of any type. Keeps its own copy of the value so typing
// never fights the model, and emits `change` for the pending-changes store.
import QtQuick
import "../theme"

Item {
    id: root

    property var rowData: ({})
    property string panelId: ""
    property var pending: ({})
    property var current: null

    signal change(string key, var value)
    signal invoke(var action)
    signal browse(string key, string kind, string value)

    width: parent ? parent.width : 0
    implicitHeight: item.visible ? item.implicitHeight
                 : actionRow.visible ? actionRow.implicitHeight
                 : block.visible ? block.implicitHeight
                 : note.visible ? note.implicitHeight
                 : kv.visible ? kv.implicitHeight : 0
    readonly property string kind: root.rowData.type || ""

    Component.onCompleted: root.current = root.initial()

    function initial() {
        const key = root.rowData.key;
        if (key === undefined || key === null)
            return root.rowData.value;
        const mapKey = root.panelId + "::" + key;
        if (root.pending && Object.prototype.hasOwnProperty.call(root.pending, mapKey))
            return root.pending[mapKey];
        return root.rowData.value;
    }
    function commit(value) {
        root.current = value;
        if (root.rowData.key)
            root.change(root.rowData.key, value);
    }

    // ── standard single-control row ─────────────────────────────────
    SettingRow {
        id: item
        visible: root.kind !== "action" && root.kind !== "list" &&
                 root.kind !== "note" && root.kind !== "kv"
        label: root.rowData.label || ""
        help: root.rowData.help || ""
        value: root.kind === "info" ? (root.rowData.value || "") : ""
        mono: !!root.rowData.mono
        copyValue: !!root.rowData.copy

        ToggleSwitch {
            visible: root.kind === "toggle"
            anchors.verticalCenter: parent.verticalCenter
            checked: !!root.current
            onToggled: (v) => root.commit(v)
        }

        Dropdown {
            visible: root.kind === "choice"
            preferredWidth: 240
            value: root.current === undefined || root.current === null ? "" : String(root.current)
            choices: root.rowData.choices || []
            onSelected: (v) => root.commit(v)
        }

        TTextField {
            visible: root.kind === "text"
            preferredWidth: 240
            text: root.current === undefined || root.current === null ? "" : String(root.current)
            onEdited: (v) => root.commit(v)
            onCommitted: (v) => root.commit(v)
        }

        Stepper {
            visible: root.kind === "number"
            value: Number(root.current || 0)
            from: root.rowData.min !== undefined ? root.rowData.min : 0
            to: root.rowData.max !== undefined ? root.rowData.max : 1000
            step: root.rowData.step !== undefined ? root.rowData.step : 1
            unit: root.rowData.unit || ""
            decimals: root.rowData.step !== undefined && root.rowData.step < 1 ? 2 : 0
            onMoved: (v) => root.commit(v)
        }

        Slider {
            visible: root.kind === "slider"
            value: Number(root.current || 0)
            from: root.rowData.min !== undefined ? root.rowData.min : 0
            to: root.rowData.max !== undefined ? root.rowData.max : 100
            step: root.rowData.step !== undefined ? root.rowData.step : 1
            onMoved: (v) => root.commit(v)
        }

        ColorField {
            visible: root.kind === "color"
            value: root.current === undefined || root.current === null ? "" : String(root.current)
            onEdited: (v) => root.commit(v)
        }

        PathField {
            visible: root.kind === "path"
            preferredWidth: 320
            text: root.current === undefined || root.current === null ? "" : String(root.current)
            onEdited: (v) => root.commit(v)
            onBrowseRequested: root.browse(root.rowData.key, root.rowData.mode || "file",
                                           root.current === undefined ? "" : String(root.current))
        }
    }

    // ── action row ──────────────────────────────────────────────────
    Row {
        id: actionRow
        visible: root.kind === "action"
        width: parent.width
        spacing: 12
        topPadding: 6
        bottomPadding: 6

        TButton {
            text: root.rowData.label || "Run"
            primary: root.rowData.variant === "primary"
            danger: root.rowData.variant === "danger"
            onClicked: root.invoke(root.rowData)
        }
        Text {
            visible: (root.rowData.help || "").length > 0
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 190
            text: root.rowData.help || ""
            color: Theme.textFaint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            wrapMode: Text.WordWrap
        }
    }

    // ── lists ───────────────────────────────────────────────────────
    ListBlock {
        id: block
        visible: root.kind === "list"
        items: root.rowData.items || []
        onInvoke: (action) => root.invoke(action)
    }

    // ── notes ───────────────────────────────────────────────────────
    Rectangle {
        id: note
        visible: root.kind === "note"
        width: parent.width
        implicitHeight: noteText.implicitHeight + 18
        radius: Theme.radiusCard
        color: Theme.cardFill
        border.width: 1
        border.color: Theme.alpha(tint, 0.30)

        readonly property color tint:
            root.rowData.tone === "danger" ? Theme.danger :
            root.rowData.tone === "warn" ? Theme.warn :
            root.rowData.tone === "ok" ? Theme.ok : Theme.info

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 9
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Glyph {
                glyph: root.rowData.tone === "danger" ? "\uf00d"
                     : root.rowData.tone === "warn" ? "\uf05a"
                     : root.rowData.tone === "ok" ? "\uf00c" : "\uf05a"
                pixelSize: Theme.size(1)
                color: note.tint
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                id: noteText
                width: parent.width - 24
                text: root.rowData.text || ""
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                wrapMode: Text.WordWrap
                lineHeight: 1.3
            }
        }
    }

    // ── key/value chips ─────────────────────────────────────────────
    Flow {
        id: kv
        visible: root.kind === "kv"
        width: parent.width
        spacing: 6

        Repeater {
            model: root.rowData.items || []
            delegate: Rectangle {
                required property var modelData
                height: 22
                width: chipText.implicitWidth + 16
                radius: Theme.radiusControl
                color: Theme.alpha(Theme.accent2, 0.12)
                border.width: 1
                border.color: Theme.alpha(Theme.accent2, 0.22)
                Text {
                    id: chipText
                    anchors.centerIn: parent
                    text: (modelData.label || "") +
                          (modelData.value ? "  " + modelData.value : "")
                    color: Theme.dim
                    font.family: Theme.monoFamily
                    font.pixelSize: 10
                }
            }
        }
    }
}
