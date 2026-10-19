// Per-widget settings — a centred layer-shell dialog opened by the cog in each
// desktop widget's bottom-right corner. Edits the widget's own `widgets.<id>`
// block in ~/.config/hyprtk-bar-qt/config.json through
// backend/.../barsettings.py, so the bar's Settings → Widgets page and the
// widget itself stay in sync. Separate surface from surface/Settings.qml.
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import "../theme"
import "../config"
import "../state"
import "../data"
import "../components"
import "../data/WidgetOptions.js" as Schema

PanelWindow {
    id: win

    visible: UiState.widgetSettingsOpen && UiState.widgetSettingsId !== ""
    color: "transparent"
    focusable: true
    exclusionMode: ExclusionMode.Ignore
    implicitWidth: 380
    implicitHeight: 560

    // Open on the focused monitor (captured when shown), as Settings does.
    property var targetScreen: null
    screen: targetScreen

    property real reveal: 0
    readonly property int animMs: Config.uiAnimations ? Config.animationDuration : 0
    Behavior on reveal { NumberAnimation { duration: win.animMs; easing.type: Easing.OutCubic } }
    onVisibleChanged: {
        reveal = visible ? 1 : 0;
        if (visible)
            targetScreen = Screens.focused();
    }

    readonly property string widgetId: UiState.widgetSettingsId
    readonly property var options: Schema.options(win.widgetId)
    readonly property var block: Widgets.block(win.widgetId)
    readonly property string title: Schema.label(win.widgetId) + " settings"

    readonly property string backend:
        Qt.resolvedUrl("../backend/hyprtk_bar_qt/barsettings.py").toString().replace("file://", "")

    Shortcut {
        sequence: "Escape"
        onActivated: win.close()
    }
    function close() {
        UiState.widgetSettingsOpen = false;
    }

    // Effective value for a row: the configured value, else the schema default.
    function valueFor(opt) {
        const v = win.block ? win.block[opt.key] : undefined;
        return v === undefined ? opt.def : v;
    }

    // ── debounced config writer (same backend as the Settings panel) ───
    property var pending: ({})
    Timer { id: flushTimer; interval: 200; onTriggered: win.flush() }
    Process {
        id: setProc
        onExited: (code, status) => {
            if (code !== 0)
                console.warn("hyprtk-bar-qt widget settings: write failed (exit " + code + ")");
        }
    }
    function write(key, value) {
        const patch = (win.pending && win.pending.widgets) ? win.pending : { widgets: {} };
        patch.widgets[win.widgetId] = patch.widgets[win.widgetId] || {};
        patch.widgets[win.widgetId][key] = value;
        win.pending = patch;
        flushTimer.restart();
    }
    function flush() {
        if (!win.pending || !win.pending.widgets)
            return;
        const patch = win.pending;
        win.pending = ({});
        setProc.command = ["python3", win.backend, "set", "--json", JSON.stringify(patch)];
        setProc.running = true;
    }

    // ── controls (instantiated per row by the Loader below) ───────────
    Component {
        id: boolCtl
        TCheckBox {
            property var opt: ({})
            property var cur: false
            checked: cur === true
            onToggled: win.write(opt.key, checked)
        }
    }
    Component {
        id: intCtl
        TSpinBox {
            property var opt: ({})
            property var cur: 0
            from: opt.min !== undefined ? opt.min : 0
            to: opt.max !== undefined ? opt.max : 9999
            stepSize: opt.step !== undefined ? opt.step : 1
            value: {
                const v = Number(cur);
                return isFinite(v) ? v : (opt.def !== undefined ? opt.def : 0);
            }
            onValueModified: win.write(opt.key, value)
        }
    }
    Component {
        id: percentCtl
        TSpinBox {
            property var opt: ({})
            property var cur: 1
            from: opt.min !== undefined ? opt.min : 0
            to: opt.max !== undefined ? opt.max : 100
            stepSize: opt.step !== undefined ? opt.step : 5
            value: {
                const v = Number(cur);
                return Math.round((isFinite(v) ? v : (opt.def !== undefined ? opt.def : 1)) * 100);
            }
            onValueModified: win.write(opt.key, value / 100)
        }
    }
    Component {
        id: textCtl
        TTextField {
            property var opt: ({})
            property var cur: ""
            placeholderText: opt.placeholder || ""
            text: (cur === undefined || cur === null) ? "" : String(cur)
            onEditingFinished: win.write(opt.key, text)
        }
    }
    Component {
        id: choiceCtl
        TComboBox {
            property var opt: ({})
            property var cur: ""
            model: opt.choices || []
            currentIndex: {
                const want = (cur === undefined || cur === null) ? opt.def : cur;
                const i = (opt.choices || []).indexOf(want);
                return i < 0 ? 0 : i;
            }
            onActivated: win.write(opt.key, opt.choices[currentIndex])
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusPanel
        color: Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b, Theme.panelOpacityStrong)
        opacity: win.reveal
        transform: Translate { y: (1 - win.reveal) * -8 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: "\uf013"
                    color: Theme.accent
                    font.family: BarConfig.glyphFont
                    font.pixelSize: BarConfig.scaled(14)
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text {
                        Layout.fillWidth: true
                        text: win.title
                        color: Theme.foreground
                        font.bold: true
                        font.pixelSize: BarConfig.scaled(14)
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Saved to the bar config · also on Settings → Widgets"
                        color: Theme.dim
                        font.pixelSize: BarConfig.scaled(10)
                        elide: Text.ElideRight
                    }
                }
                Rectangle {
                    implicitWidth: 24
                    implicitHeight: 24
                    radius: 6
                    color: closeHover.hovered ? Theme.alpha(Theme.accent2, 0.22) : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "\uf00d"
                        color: Theme.dim
                        font.family: BarConfig.glyphFont
                        font.pixelSize: BarConfig.scaled(11)
                    }
                    HoverHandler { id: closeHover }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: win.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 1
                color: Theme.alpha(Theme.accent2, 0.2)
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: rows.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ColumnLayout {
                    id: rows
                    width: parent.width
                    spacing: 5

                    Repeater {
                        model: win.visible ? win.options : []
                        delegate: ColumnLayout {
                            id: cell
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                Layout.fillWidth: true
                                visible: cell.index === 0
                                    || win.options[cell.index - 1].section !== cell.modelData.section
                                text: cell.modelData.section
                                color: Theme.accent
                                font.bold: true
                                font.pixelSize: BarConfig.scaled(11)
                                topPadding: cell.index === 0 ? 0 : 6
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Text {
                                    text: cell.modelData.label
                                    color: Theme.dim
                                    font.pixelSize: BarConfig.scaled(11)
                                    Layout.preferredWidth: 100
                                    elide: Text.ElideRight
                                }
                                Loader {
                                    id: ctl
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    property var opt: cell.modelData
                                    property var cur: win.valueFor(cell.modelData)
                                    sourceComponent: cell.modelData.type === "bool" ? boolCtl
                                        : cell.modelData.type === "choice" ? choiceCtl
                                        : cell.modelData.type === "text" ? textCtl
                                        : cell.modelData.type === "percent" ? percentCtl
                                        : intCtl
                                    onLoaded: {
                                        item.opt = ctl.opt;
                                        item.cur = ctl.cur;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
