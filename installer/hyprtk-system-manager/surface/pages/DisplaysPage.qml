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

    readonly property var bitDepthChoices: [
        {value: "auto", label: "Auto"},
        {value: "8", label: "8-bit"},
        {value: "10", label: "10-bit"},
    ]

    readonly property var cmChoices: [
        {value: "auto", label: "Auto"},
        {value: "srgb", label: "sRGB"},
        {value: "hdr", label: "HDR"},
        {value: "wide", label: "Wide gamut"},
        {value: "edid", label: "EDID"},
    ]

    readonly property var vrrChoices: [
        {value: "0", label: "Off"},
        {value: "1", label: "Always on"},
        {value: "2", label: "Fullscreen only"},
    ]

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
                vrr: String(mon.vrr || 0),
                mirror: mon.mirror || "",
                // The compositor reports the current buffer format, so a 10-bit
                // scanout is visible; anything else starts at the default.
                bitdepth: String(mon.format || "").indexOf("2101010") >= 0 ? "10" : "auto",
                cm: "auto",
                format: mon.format || "",
                currentCm: mon.currentCm || "",
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
    function mirrorChoices(current) {
        const out = [{value: "", label: "None"}];
        for (const mon of page.monitors) {
            if (mon.name !== current)
                out.push({value: mon.name, label: mon.name});
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
            vrr: parseInt(item.vrr) || 0,
            mirror: item.mirror || "",
            bitdepth: item.bitdepth || "auto",
            cm: item.cm || "auto",
            x: item.x || 0,
            y: item.y || 0,
            disabled: !!item.disabled,
        };
    }
    function applyMonitor(index) {
        // A live change is only possible through the config on this Hyprland
        // (keyword requests are unsupported), so applying writes the block.
        page.persistAll();
    }
    function collectLayout() {
        const monitors = [];
        for (let i = 0; i < layout.count; i++) {
            const entry = layoutEntry(i);
            if (entry)
                monitors.push(entry);
        }
        return monitors;
    }
    function persistAll() {
        page.invoke("displays", {
            action: "displays.persist",
            args: { monitors: page.collectLayout() },
        });
    }
    function saveProfile(name) {
        if (!name || name.trim().length === 0)
            return;
        page.invoke("displays", {
            action: "displays.profile_save",
            args: { name: name.trim(), monitors: page.collectLayout() },
        });
    }
    readonly property var profileItems: {
        const out = [];
        for (const item of (page.model.profiles || [])) {
            out.push({
                title: item.name,
                subtitle: (item.created || "") + " · " + item.count + " monitor(s)",
                badges: [],
                actions: [
                    { label: "Apply", action: "displays.profile_apply",
                      args: { name: item.name } },
                    { label: "Delete", action: "displays.profile_delete",
                      args: { name: item.name }, danger: true, confirm: item.name,
                      message: "Delete the display profile? The current layout stays." },
                ],
            });
        }
        return out;
    }
    function applyAll() {
        page.persistAll();
    }

    readonly property real canvasScale: {
        let totalW = 0;
        let maxH = 1;
        for (let i = 0; i < layout.count; i++) {
            const item = layout.get(i);
            if (!item || item.disabled)
                continue;
            totalW += item.width;
            maxH = Math.max(maxH, item.height);
        }
        const available = Math.max(240, canvasItem.width - 24);
        return Math.min(0.18, available / Math.max(1, totalW),
                        (canvasItem.height - 24) / Math.max(1, maxH));
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

            SectionCard {
                width: column.width
                title: "Arrangement"
                description: "Drag a monitor to set its position. The values snap to 8 px and the cards below follow."

                Item {
                    id: canvasItem
                    width: parent.width
                    height: 190

                    Rectangle {
                        anchors.fill: parent
                        radius: 8
                        color: Theme.alpha(Theme.background, 0.35)
                        border.width: 1
                        border.color: Theme.cardBorder
                    }

                    Repeater {
                        model: layout
                        delegate: Rectangle {
                            id: monRect
                            readonly property real baseX: 12 + model.x * page.canvasScale
                            readonly property real baseY: 12 + model.y * page.canvasScale
                            property real dragDX: 0
                            property real dragDY: 0

                            visible: !model.disabled
                            x: monRect.baseX + monRect.dragDX
                            y: monRect.baseY + monRect.dragDY
                            width: Math.max(28, model.width * page.canvasScale)
                            height: Math.max(20, model.height * page.canvasScale)
                            radius: 6
                            color: Theme.alpha(Theme.accent, 0.20)
                            border.width: 1
                            border.color: Theme.alpha(Theme.accent, 0.55)

                            Text {
                                anchors.centerIn: parent
                                width: parent.width - 8
                                text: model.name
                                color: Theme.foreground
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.size(0)
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 4
                                text: model.width + "×" + model.height
                                color: Theme.dim
                                font.family: Theme.fontFamily
                                font.pixelSize: 9
                            }

                            DragHandler {
                                id: monDrag
                                cursorShape: Qt.SizeAllCursor
                                grabPermissions: PointerHandler.CanTakeOverFromAnything
                                onTranslationChanged: {
                                    const maxX = canvasItem.width - monRect.width - 12;
                                    const maxY = canvasItem.height - monRect.height - 12;
                                    monRect.dragDX = Math.max(12 - monRect.baseX,
                                        Math.min(maxX - monRect.baseX, monDrag.translation.x));
                                    monRect.dragDY = Math.max(12 - monRect.baseY,
                                        Math.min(maxY - monRect.baseY, monDrag.translation.y));
                                }
                                onActiveChanged: {
                                    if (monDrag.active)
                                        return;
                                    const nx = (monRect.baseX + monRect.dragDX - 12) / page.canvasScale;
                                    const ny = (monRect.baseY + monRect.dragDY - 12) / page.canvasScale;
                                    layout.setProperty(index, "x", Math.max(0, Math.round(nx / 8) * 8));
                                    layout.setProperty(index, "y", Math.max(0, Math.round(ny / 8) * 8));
                                    monRect.dragDX = 0;
                                    monRect.dragDY = 0;
                                }
                            }
                        }
                    }
                }
            }

            Repeater {
                model: layout
                delegate: SectionCard {
                    id: card
                    width: column.width
                    title: model.name
                    description: (model.description || "Monitor") + " · " +
                                 (model.disabled ? "disabled"
                                  : model.width + "×" + model.height + " @ " +
                                    Number(model.refreshRate).toFixed(2) + " Hz" +
                                    (model.format ? " · " + model.format : "") +
                                    (model.currentCm ? " · " + model.currentCm : ""))

                    SettingRow {
                        label: "Enabled"
                        help: "Turn this output on or off."
                        visible: page.monitors.length > 1
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
                        label: "Variable refresh rate"
                        help: "Adaptive sync; the monitor must support it."
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 200
                            value: model.vrr
                            choices: page.vrrChoices
                            onSelected: (v) => layout.setProperty(index, "vrr", v)
                        }
                    }
                    SettingRow {
                        label: "Bit depth"
                        help: "Auto keeps the compositor default; 10-bit needs a capable display."
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 160
                            value: model.bitdepth
                            choices: page.bitDepthChoices
                            onSelected: (v) => layout.setProperty(index, "bitdepth", v)
                        }
                    }
                    SettingRow {
                        label: "Colour management"
                        help: "HDR requires an HDR-capable output; unsupported rules are ignored."
                        visible: !model.disabled
                        Dropdown {
                            preferredWidth: 180
                            value: model.cm
                            choices: page.cmChoices
                            onSelected: (v) => layout.setProperty(index, "cm", v)
                        }
                    }
                    SettingRow {
                        label: "Mirror"
                        help: "Show this output's image on another monitor."
                        visible: !model.disabled && page.monitors.length > 1
                        Dropdown {
                            preferredWidth: 200
                            value: model.mirror
                            choices: page.mirrorChoices(model.name)
                            onSelected: (v) => layout.setProperty(index, "mirror", v)
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
                description: "Applying writes the managed block into monitors.lua and reloads Hyprland, so the layout survives a reboot."
                Row {
                    width: parent.width
                    spacing: 8
                    TButton { text: "Apply layout"; primary: true; onClicked: page.persistAll() }
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
                title: "Layout profiles"
                description: "Save this arrangement by name, then switch the whole layout back to it later."
                Row {
                    width: parent.width
                    spacing: 8
                    TTextField {
                        id: profileName
                        preferredWidth: 240
                        placeholder: "Desk, Movie, Docked…"
                    }
                    TButton {
                        text: "Save current layout"
                        onClicked: {
                            page.saveProfile(profileName.text);
                            profileName.text = "";
                        }
                    }
                }
                ListBlock {
                    width: parent.width
                    items: page.profileItems
                    onInvoke: (action) => page.invoke("displays", action)
                }
                Text {
                    visible: page.profileItems.length === 0
                    topPadding: 4
                    width: parent.width
                    text: "No saved layouts yet. A profile stores every monitor's mode, scale, rotation, position, VRR and mirroring."
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
