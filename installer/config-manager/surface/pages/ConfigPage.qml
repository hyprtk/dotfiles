// Module settings page: schema options plus editable file contents.
// Flat rows in the bar-qt style; every discovered item edits in place.
import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: page
    property string pageId: ""
    property var model: ({})
    property var schemaData: ({})
    property var pending: ({})
    property var monitorData: []
    signal change(string path, var value, string kind)
    signal itemChange(string key, var descriptor)

    property string newEnvKey: ""
    property string newEnvValue: ""
    property string newBindKeys: ""
    property string newBindAction: 'hl.dsp.exec_cmd("")'
    property string newRequire: ""
    property int addSeq: 0

    readonly property var meta: {
        const pages = (schemaData && schemaData.pages) || [];
        return pages.find(p => p.id === pageId) || ({ options: [], items: [] });
    }
    readonly property var items: meta.items || []
    readonly property var envItems: items.filter(i => i.kind === "env")
    readonly property var execItems: items.filter(i => i.kind === "exec")
    readonly property var bindItems: items.filter(i => i.kind === "bind")
    readonly property var monitorItems: items.filter(i => i.kind === "monitor")
    readonly property var ruleItems: items.filter(i => i.kind === "rule")
    readonly property var requireItems: items.filter(i => i.kind === "require")

    function valueFor(path) {
        if (pending && pending.hasOwnProperty(path))
            return pending[path].value;
        let node = model ? model.config : null;
        for (const part of path.split(".")) {
            if (node === null || node === undefined || typeof node !== "object")
                return undefined;
            node = node[part];
        }
        return node;
    }

    function pend(key) {
        return (pending && pending.hasOwnProperty(key)) ? pending[key] : null;
    }
    function isPending(prefix) {
        for (const k of Object.keys(pending || {}))
            if (k === prefix || k.indexOf(prefix + ":") === 0)
                return true;
        return false;
    }

    function envValue(item) {
        const p = page.pend("env:" + item.key);
        return p ? p.value : item.value;
    }
    function stageEnv(key, value, add) {
        if (!key)
            return;
        page.itemChange("env:" + key, {
            type: "env", key: key, value: value,
            module: add ? page.meta.file : undefined
        });
    }
    function addEnv() {
        if (!page.newEnvKey)
            return;
        page.stageEnv(page.newEnvKey, page.newEnvValue, true);
        page.newEnvKey = "";
        page.newEnvValue = "";
    }

    function execValue(item) {
        const p = page.pend("exec:" + item.file + ":" + item.line);
        return p ? p.command : item.command;
    }
    function stageExec(item, command) {
        page.itemChange("exec:" + item.file + ":" + item.line, {
            type: "exec", file: item.file, line: item.line, command: command
        });
    }

    function bindDescriptor(item) {
        return page.pend("bind:" + item.file + ":" + item.line) || item;
    }
    function stageBind(item, keys, action) {
        page.itemChange("bind:" + item.file + ":" + item.line, {
            type: "bind", file: item.file, line: item.line,
            keys: keys, action: action
        });
    }
    function addBind() {
        if (!page.newBindKeys || !page.newBindAction)
            return;
        page.itemChange("bind-add:" + (++page.addSeq), {
            type: "bind", file: page.meta.file, line: 0,
            keys: page.newBindKeys, action: page.newBindAction
        });
        page.newBindKeys = "";
        page.newBindAction = 'hl.dsp.exec_cmd("")';
    }

    function fieldKey(file, line, field) {
        return "field:" + file + ":" + line + ":" + field.path;
    }
    function fieldValue(file, line, field) {
        const p = page.pend(page.fieldKey(file, line, field));
        return p ? p.value : field.value;
    }
    function stageField(file, line, field, value, call) {
        page.itemChange(page.fieldKey(file, line, field), {
            type: "call_field", file: file, line: line, call: call,
            path: field.path, value: value, valueType: field.type
        });
    }
    function cardFields(item) {
        const call = item.kind === "monitor" ? "monitor" : item.ruleKind;
        return (item.fields || []).map(field => ({
            file: item.file, line: item.line, call: call, field: field
        }));
    }

    // ── live monitor data (hyprctl, same source as nwg-displays) ───────
    function monitorList() {
        return page.monitorData || [];
    }
    function monitorByName(name) {
        for (const mon of page.monitorList())
            if (mon.name === name)
                return mon;
        return null;
    }
    function itemFieldValue(item, path) {
        const p = page.pend("field:" + item.file + ":" + item.line + ":" + path);
        if (p)
            return p.value;
        const field = (item.fields || []).find(f => f.path === path);
        return field ? field.value : "";
    }
    function stageItemField(item, path, value, type) {
        page.stageField(item.file, item.line, { path: path, type: type || "str" }, value, "monitor");
    }

    function outputValues(item) {
        const values = [""];
        for (const mon of page.monitorList())
            if (values.indexOf(mon.name) < 0)
                values.push(mon.name);
        const current = String(page.itemFieldValue(item, "output") || "");
        if (current && values.indexOf(current) < 0)
            values.push(current);
        return values;
    }
    function outputLabels(item) {
        return page.outputValues(item).map(value => {
            if (value === "")
                return "auto (all outputs)";
            const mon = page.monitorByName(value);
            if (!mon)
                return value + " (configured)";
            const desc = mon.description ? " — " + mon.description : "";
            return value + desc + (mon.active ? "" : " (inactive)");
        });
    }
    function outputIndex(item) {
        const index = page.outputValues(item).indexOf(String(page.itemFieldValue(item, "output") || ""));
        return index < 0 ? 0 : index;
    }
    function stageOutput(item, index) {
        page.stageItemField(item, "output", page.outputValues(item)[index], "str");
    }

    function selectedMonitor(item) {
        const name = String(page.itemFieldValue(item, "output") || "");
        if (name)
            return page.monitorByName(name);
        const list = page.monitorList();
        for (const mon of list)
            if (mon.active)
                return mon;
        return list.length > 0 ? list[0] : null;
    }
    function sameMode(a, b) {
        const re = /^(\d+)x(\d+)@([0-9.]+)$/;
        const ma = re.exec(String(a));
        const mb = re.exec(String(b));
        if (!ma || !mb)
            return String(a) === String(b);
        return ma[1] === mb[1] && ma[2] === mb[2]
               && Math.abs(parseFloat(ma[3]) - parseFloat(mb[3])) < 0.01;
    }
    function modeValues(item) {
        const values = ["preferred"];
        const mon = page.selectedMonitor(item);
        if (mon) {
            for (const mode of mon.modes || []) {
                let duplicate = false;
                for (const value of values)
                    if (page.sameMode(value, mode.value)) { duplicate = true; break; }
                if (!duplicate)
                    values.push(mode.value);
            }
        }
        const current = String(page.itemFieldValue(item, "mode") || "");
        if (current) {
            let duplicate = false;
            for (const value of values)
                if (page.sameMode(value, current)) { duplicate = true; break; }
            if (!duplicate)
                values.push(current);
        }
        return values;
    }
    function modeLabels(item) {
        const mon = page.selectedMonitor(item);
        return page.modeValues(item).map(value => {
            if (value === "preferred")
                return "preferred";
            const mode = mon ? (mon.modes || []).find(m => page.sameMode(m.value, value)) : null;
            return mode ? mode.label : value;
        });
    }
    function modeIndex(item) {
        const current = String(page.itemFieldValue(item, "mode") || "");
        const values = page.modeValues(item);
        for (let i = 0; i < values.length; i++)
            if (page.sameMode(values[i], current))
                return i;
        return 0;
    }
    function stageMode(item, index) {
        page.stageItemField(item, "mode", page.modeValues(item)[index], "str");
    }

    function requireValue(item) {
        const p = page.pend("require:" + item.line);
        return p || item;
    }
    function stageRequire(item, module, active) {
        page.itemChange("require:" + item.line, {
            type: "require_toggle", line: item.line, module: module, active: active
        });
    }
    function addRequire() {
        if (!page.newRequire)
            return;
        page.itemChange("require-add:" + (++page.addSeq), {
            type: "require_add", module: page.newRequire
        });
        page.newRequire = "";
    }

    component FieldRow: RowLayout {
        id: fieldRow
        property var field: ({})
        property var current
        signal changed(var value)
        spacing: 8

        Text {
            Layout.preferredWidth: 130
            Layout.alignment: Qt.AlignVCenter
            text: fieldRow.field.label || fieldRow.field.path
            color: Theme.foreground
            font.pixelSize: Theme.scaled(11)
            elide: Text.ElideRight
        }
        TCheckBox {
            visible: fieldRow.field.type === "bool"
            checked: fieldRow.current === true
            onToggled: v => fieldRow.changed(v)
        }
        TSpinBox {
            visible: fieldRow.field.type === "int" || fieldRow.field.type === "float"
            Layout.preferredWidth: 120
            from: -1000
            to: 10000
            step: fieldRow.field.type === "float" ? 0.05 : 1
            decimals: fieldRow.field.type === "float" ? 2 : 0
            value: Number(fieldRow.current) || 0
            onModified: v => fieldRow.changed(v)
        }
        TTextField {
            visible: fieldRow.field.type === "str"
            Layout.preferredWidth: 240
            text: fieldRow.current === undefined || fieldRow.current === null ? "" : String(fieldRow.current)
            onEdited: v => fieldRow.changed(v)
        }
        Item { Layout.fillWidth: true }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: col.implicitHeight + 8
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: col
            width: parent.width
            spacing: 8

            // page meta + file badges
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    Layout.fillWidth: true
                    text: page.meta.description || ""
                    color: Theme.dim
                    font.pixelSize: Theme.scaled(11)
                    elide: Text.ElideRight
                }
                Rectangle {
                    visible: !!page.meta.file
                    implicitWidth: fileLabel.implicitWidth + 14
                    implicitHeight: 20
                    radius: 6
                    color: Theme.alpha(Theme.background, 0.6)
                    border.color: Theme.border
                    Text {
                        id: fileLabel
                        anchors.centerIn: parent
                        text: page.meta.file || ""
                        color: Theme.dim
                        font.pixelSize: Theme.scaled(10)
                    }
                }
                Rectangle {
                    visible: page.meta.file !== undefined && page.meta.file !== null
                    implicitWidth: activeLabel.implicitWidth + 14
                    implicitHeight: 20
                    radius: 6
                    color: page.meta.active ? Theme.alpha(Theme.accent2, 0.15)
                                            : Theme.alpha(Theme.background, 0.6)
                    border.color: page.meta.active ? Theme.alpha(Theme.accent2, 0.5) : Theme.border
                    Text {
                        id: activeLabel
                        anchors.centerIn: parent
                        text: page.meta.active ? "loaded" : "inactive"
                        color: page.meta.active ? Theme.accent2 : Theme.dim
                        font.pixelSize: Theme.scaled(10)
                    }
                }
            }

            Repeater {
                model: page.meta.options || []
                delegate: OptionRow {
                    Layout.fillWidth: true
                    opt: modelData
                    value: page.valueFor(modelData.path)
                    pending: (page.pending || {}).hasOwnProperty(modelData.path)
                    onChanged: v => page.change(modelData.path, v, modelData.type)
                }
            }

            // ── environment variables ───────────────────────────────
            Text {
                visible: page.envItems.length > 0
                text: "Environment variables"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            Repeater {
                model: page.envItems
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        Layout.preferredWidth: 220
                        Layout.alignment: Qt.AlignVCenter
                        text: modelData.key
                        color: page.isPending("env:" + modelData.key) ? Theme.accent2 : Theme.foreground
                        font.pixelSize: Theme.scaled(12)
                        elide: Text.ElideRight
                    }
                    TTextField {
                        Layout.preferredWidth: 240
                        text: String(page.envValue(modelData))
                        onEdited: v => page.stageEnv(modelData.key, v, false)
                    }
                    Item { Layout.fillWidth: true }
                }
            }
            RowLayout {
                visible: page.envItems.length > 0
                Layout.fillWidth: true
                spacing: 8
                TTextField {
                    Layout.preferredWidth: 220
                    placeholderText: "KEY"
                    text: page.newEnvKey
                    onEdited: v => page.newEnvKey = v
                }
                TTextField {
                    Layout.preferredWidth: 240
                    placeholderText: "value"
                    text: page.newEnvValue
                    onEdited: v => page.newEnvValue = v
                }
                TButton { text: "Add variable"; onClicked: page.addEnv() }
                Item { Layout.fillWidth: true }
            }

            // ── autostart commands ──────────────────────────────────
            Text {
                visible: page.execItems.length > 0
                text: "Autostart commands"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            Repeater {
                model: page.execItems
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        Layout.preferredWidth: 170
                        Layout.alignment: Qt.AlignVCenter
                        text: modelData.label
                        color: page.isPending("exec:" + modelData.file + ":" + modelData.line)
                               ? Theme.accent2 : Theme.dim
                        font.pixelSize: Theme.scaled(11)
                    }
                    TTextField {
                        Layout.fillWidth: true
                        text: String(page.execValue(modelData))
                        onEdited: v => page.stageExec(modelData, v)
                    }
                }
            }

            // ── key bindings ────────────────────────────────────────
            Text {
                visible: page.bindItems.length > 0
                text: "Key bindings"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            RowLayout {
                visible: page.bindItems.length > 0
                Layout.fillWidth: true
                spacing: 8
                Text { Layout.preferredWidth: 200; text: "Keys"; color: Theme.dim; font.pixelSize: Theme.scaled(10) }
                Text { Layout.fillWidth: true; text: "Dispatcher (Lua expression)"; color: Theme.dim; font.pixelSize: Theme.scaled(10) }
            }
            Repeater {
                model: page.bindItems
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    readonly property var desc: page.bindDescriptor(modelData)
                    TTextField {
                        Layout.preferredWidth: 200
                        text: String(desc.keys)
                        onEdited: v => page.stageBind(modelData, v, page.bindDescriptor(modelData).action)
                    }
                    TTextField {
                        Layout.fillWidth: true
                        text: String(desc.action)
                        onEdited: v => page.stageBind(modelData, page.bindDescriptor(modelData).keys, v)
                    }
                }
            }
            RowLayout {
                visible: page.bindItems.length > 0
                Layout.fillWidth: true
                spacing: 8
                TTextField {
                    Layout.preferredWidth: 200
                    placeholderText: "Keys (e.g. SUPER + T)"
                    text: page.newBindKeys
                    onEdited: v => page.newBindKeys = v
                }
                TTextField {
                    Layout.fillWidth: true
                    text: page.newBindAction
                    onEdited: v => page.newBindAction = v
                }
                TButton { text: "Add binding"; onClicked: page.addBind() }
            }

            // ── monitors ────────────────────────────────────────────
            Text {
                visible: page.monitorItems.length > 0
                text: "Monitors"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            Repeater {
                model: page.monitorItems
                delegate: Rectangle {
                    id: monCard
                    property var item: modelData
                    Layout.fillWidth: true
                    implicitHeight: monCol.implicitHeight + 20
                    radius: 10
                    color: Theme.card
                    border.color: page.isPending("field:" + item.file + ":" + item.line)
                                  ? Theme.alpha(Theme.accent2, 0.55) : Theme.border
                    ColumnLayout {
                        id: monCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        Text {
                            text: "Monitor · " + monCard.item.label
                            color: Theme.foreground
                            font.pixelSize: Theme.scaled(12)
                            font.bold: true
                        }
                        RowLayout {
                            visible: page.monitorData.length > 0
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                Layout.preferredWidth: 130
                                text: "Output"
                                color: Theme.foreground
                                font.pixelSize: Theme.scaled(11)
                            }
                            TComboBox {
                                Layout.fillWidth: true
                                model: page.outputLabels(monCard.item)
                                currentIndex: page.outputIndex(monCard.item)
                                onActivated: i => page.stageOutput(monCard.item, i)
                            }
                        }
                        RowLayout {
                            visible: page.monitorData.length > 0
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                Layout.preferredWidth: 130
                                text: "Mode"
                                color: Theme.foreground
                                font.pixelSize: Theme.scaled(11)
                            }
                            TComboBox {
                                Layout.fillWidth: true
                                model: page.modeLabels(monCard.item)
                                currentIndex: page.modeIndex(monCard.item)
                                onActivated: i => page.stageMode(monCard.item, i)
                            }
                        }
                        Repeater {
                            model: page.monitorData.length > 0
                                   ? page.cardFields(monCard.item).filter(f => f.field.path !== "output" && f.field.path !== "mode")
                                   : page.cardFields(monCard.item)
                            delegate: FieldRow {
                                Layout.fillWidth: true
                                field: modelData.field
                                current: page.fieldValue(modelData.file, modelData.line, modelData.field)
                                onChanged: v => page.stageField(modelData.file, modelData.line,
                                                                modelData.field, v, modelData.call)
                            }
                        }
                    }
                }
            }

            // ── rules ───────────────────────────────────────────────
            Text {
                visible: page.ruleItems.length > 0
                text: "Rules"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            Repeater {
                model: page.ruleItems
                delegate: Rectangle {
                    id: ruleCard
                    property var item: modelData
                    Layout.fillWidth: true
                    implicitHeight: ruleCol.implicitHeight + 20
                    radius: 10
                    color: Theme.card
                    border.color: page.isPending("field:" + item.file + ":" + item.line)
                                  ? Theme.alpha(Theme.accent2, 0.55) : Theme.border
                    ColumnLayout {
                        id: ruleCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: ruleCard.item.label
                                color: Theme.foreground
                                font.pixelSize: Theme.scaled(12)
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            Text {
                                text: ruleCard.item.ruleKind
                                color: Theme.dim
                                font.pixelSize: Theme.scaled(10)
                            }
                        }
                        Repeater {
                            model: page.cardFields(ruleCard.item)
                            delegate: FieldRow {
                                Layout.fillWidth: true
                                field: modelData.field
                                current: page.fieldValue(modelData.file, modelData.line, modelData.field)
                                onChanged: v => page.stageField(modelData.file, modelData.line,
                                                                modelData.field, v, modelData.call)
                            }
                        }
                    }
                }
            }

            // ── load order ──────────────────────────────────────────
            Text {
                visible: page.requireItems.length > 0
                text: "Load order"
                color: Theme.accent
                font.pixelSize: Theme.scaled(12)
                font.bold: true
                Layout.topMargin: 4
            }
            Repeater {
                model: page.requireItems
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    readonly property var desc: page.requireValue(modelData)
                    TTextField {
                        Layout.preferredWidth: 240
                        text: String(desc.module)
                        onEdited: v => page.stageRequire(modelData, v, page.requireValue(modelData).active)
                    }
                    TCheckBox {
                        checked: page.requireValue(modelData).active === true
                        onToggled: v => page.stageRequire(modelData, page.requireValue(modelData).module, v)
                    }
                    Text {
                        text: page.requireValue(modelData).active ? "active" : "off"
                        color: page.isPending("require:" + modelData.line) ? Theme.accent2 : Theme.dim
                        font.pixelSize: Theme.scaled(10)
                    }
                    Item { Layout.fillWidth: true }
                }
            }
            RowLayout {
                visible: page.requireItems.length > 0
                Layout.fillWidth: true
                spacing: 8
                TTextField {
                    Layout.preferredWidth: 240
                    placeholderText: "module name"
                    text: page.newRequire
                    onEdited: v => page.newRequire = v
                }
                TButton { text: "Add module"; onClicked: page.addRequire() }
                Item { Layout.fillWidth: true }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
