// Displays: one card per monitor, live apply plus a persistent managed block.
import QtQuick
import "../../theme"
import "../../components"

Flickable {
    id: page

    property var model: ({})
    property string panelId: "displays"
    property var pending: ({})

    signal change(string panelId, string key, var value)
    signal invoke(string panelId, var action)
    signal browse(string panelId, string key, string mode, string value)

    contentWidth: width
    contentHeight: content.height
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    property var monitors: model.monitors || []
    property var transforms: model.transforms || []
    property string configFile: model.configFile || ""
    property bool managed: !!model.managed

    readonly property var scaleChoices: [
        {value: "0.75", label: "0.75×"}, {value: "1", label: "1.00×"},
        {value: "1.25", label: "1.25×"}, {value: "1.5", label: "1.50×"},
        {value: "1.75", label: "1.75×"}, {value: "2", label: "2.00×"},
        {value: "2.5", label: "2.50×"}, {value: "3", label: "3.00×"},
    ]

    ListModel { id: layout }

    function loadLayout() {
        layout.clear();
        for (const mon of page.monitors) {
            layout.append({
                name: mon.name,
                description: mon.description,
                mode: mon.currentMode || "preferred",
                modes: JSON.stringify(mon.modes || []),
                scale: String(mon.scale || 1),
                transform: String(mon.transform || 0),
                x: mon.x,
                y: mon.y,
                disabled: mon.disabled,
                width: mon.width,
                height: mon.height,
                refreshRate: mon.refreshRate,
            });
        }
    }

    onMonitorsChanged: loadLayout()
    Component.onCompleted: loadLayout()

    function modeChoices(modes) {
        const out = [{value: "preferred", label: "Preferred"}];
        const list = modes || [];
        for (let i = 0; i < list.length; i++) {
            const mode = list[i];
            if (mode && mode.value !== undefined)
                out.push({value: String(mode.value), label: String(mode.label || mode.value)});
        }
        return out;
    }
    function layoutEntry(index) {
        const item = layout.get(index);
        if (!item)
            return null;
        return {
            name: item.name,
            mode: item.mode,
            scale: parseFloat(item.scale) || 1,
            transform: parseInt(item.transform) || 0,
            x: item.x || 0,
            y: item.y || 0,
            disabled: !!item.disabled,
        };
    }
    function applyMonitor(index) {
        const entry = layoutEntry(index);
        if (!entry)
            return;
        page.invoke("displays", {
            action: "displays.apply",
            args: entry,
        });
    }
    function persistAll() {
        const monitors = [];
        for (let i = 0; i < layout.count; i++) {
            const entry = layoutEntry(i);
            if (entry)
                monitors.push(entry);
        }
        page.invoke("displays", {
            action: "displays.persist",
            args: { monitors: monitors },
        });
    }
    function applyAll() {
        for (let i = 0; i < layout.count; i++)
            applyMonitor(i);
    }

    Item {
        id: content
        width: page.width
        height: column.implicitHeight + 40

        Column {
            id: column
            x: 16
            y: 20
            width: parent.width - 32
            spacing: 10

            Repeater {
                model: layout
                delegate: SectionCard {
                    id: card
                    width: column.width
                    title: model.name
                    description: (model.description || "Monitor") + " · " +
                                 (model.disabled ? "disabled"
                                  : model.width + "×" + model.height + " @ " +
                                    Number(model.refreshRate).toFixed(2) + " Hz")

                    SettingRow {
                        label: "Enabled"
                        help: "Turn this output on or off."
                        ToggleSwitch {
                            checked: !model.disabled
                            onToggled: (v) => layout.setProperty(index, "disabled", !v)
                        }
                    }
                    SettingRow {
                        label: "Resolution and refresh rate"
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 260
                            value: model.mode
                            choices: page.modeChoices(JSON.parse(model.modes || "[]"))
                            onSelected: (v) => layout.setProperty(index, "mode", v)
                        }
                    }
                    SettingRow {
                        label: "Scale"
                        help: "1.00× is native; use 1.25× or 1.50× for HiDPI."
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 140
                            value: model.scale
                            choices: page.scaleChoices
                            onSelected: (v) => layout.setProperty(index, "scale", v)
                        }
                    }
                    SettingRow {
                        label: "Rotation"
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 200
                            value: model.transform
                            choices: page.transforms
                            onSelected: (v) => layout.setProperty(index, "transform", v)
                        }
                    }
                    SettingRow {
                        label: "Position"
                        help: "Top-left corner in the global layout, in pixels."
                        visible: !model.disabled
                        Row {
                            spacing: 6
                            Stepper {
                                value: model.x
                                from: 0
                                to: 16384
                                onMoved: (v) => layout.setProperty(index, "x", Math.round(v))
                            }
                            Stepper {
                                value: model.y
                                from: 0
                                to: 16384
                                onMoved: (v) => layout.setProperty(index, "y", Math.round(v))
                            }
                        }
                    }
                    Row {
                        width: parent.width
                        spacing: 8
                        topPadding: 6
                        Item { width: parent.width - buttons.width - 8; height: 1 }
                        Row {
                            id: buttons
                            spacing: 8
                            TButton {
                                text: "Apply this monitor"
                                enabled: !model.disabled
                                onClicked: page.applyMonitor(index)
                            }
                        }
                    }
                }
            }

            SectionCard {
                width: column.width
                title: "Layout"
                description: "Changes apply immediately. Save them to keep the layout across reboots."
                Row {
                    width: parent.width
                    spacing: 8
                    TButton { text: "Apply all"; primary: true; onClicked: page.applyAll() }
                    TButton { text: "Make persistent"; onClicked: page.persistAll() }
                    TButton {
                        text: "Reset"
                        onClicked: page.loadLayout()
                    }
                }
                Text {
                    topPadding: 4
                    width: parent.width
                    text: page.managed
                        ? "A managed block is present in " + page.configFile
                        : "No managed block yet — “Make persistent” adds one to " + page.configFile
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(1)
                    wrapMode: Text.WordWrap
                }
            }

            SectionCard {
                width: column.width
                title: "Notes"
                description: ""
                RowView {
                    width: parent.width
                    rowData: ({ type: "note", tone: "info",
                        text: "The compositor's monitor rules are written only between the " +
                              "hyprtk-system-manager markers; the rest of monitors.lua is untouched." })
                    panelId: page.panelId
                }
            }
        }
    }
}
