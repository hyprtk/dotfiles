import QtQuick
import QtQuick.Controls
import HyprtkTerm 1.0
import "components"
import "theme"
import "theme/util.js" as Util

ApplicationWindow {
    id: win

    visible: true
    width: 940
    height: 580
    minimumWidth: 420
    minimumHeight: 260
    color: win.cfg.opacity < 0.999 ? "transparent" : win.th.background
    title: win.activeLabel || "hyprtk-term"

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config
    readonly property string mono: cfg.font_family

    property var tabs: []          // [{id, label, alerted}]
    property string activeId: ""
    property string activeLabel: ""
    property int counter: 0
    property var views: ({})       // id -> TermView (Python objects, not bindings)
    property var fonts: []
    property string toastText: ""
    property bool settingsOpen: false
    property bool findOpen: false
    property real menuX: 0
    property real menuY: 0

    Component.onCompleted: {
        fonts = Bridge.monoFonts();
        newTab();
    }

    // ---------------------------------------------------------------- tabs --

    function indexOf(id) {
        for (var i = 0; i < tabs.length; i++)
            if (tabs[i].id === id)
                return i;
        return -1;
    }

    function labelOf(id) {
        var i = indexOf(id);
        return i < 0 ? "" : tabs[i].label;
    }

    function setLabel(id, label) {
        var next = tabs.slice();
        var i = indexOf(id);
        if (i < 0)
            return;
        next[i] = { id: id, label: label || "Terminal", alerted: next[i].alerted };
        tabs = next;
        if (id === activeId)
            activeLabel = next[i].label;
    }

    function setAlerted(id, value) {
        var i = indexOf(id);
        if (i < 0)
            return;
        var next = tabs.slice();
        next[i] = { id: id, label: next[i].label, alerted: value };
        tabs = next;
    }

    function newTab() {
        counter += 1;
        var id = "t" + counter;
        var view = termComponent.createObject(host, { "visible": false });
        if (!view) {
            toast("Could not create a terminal");
            return;
        }
        views[id] = view;
        view.applySettings(cfg, th);
        view.titleChanged.connect(function () { win.setLabel(id, view.title); });
        view.exited.connect(function (code) {
            win.setLabel(id, "[exited " + code + "]");
            win.toast("Shell exited (" + code + ")");
        });
        view.bell.connect(function () {
            win.setAlerted(id, true);
            win.toast("Bell");
        });
        view.contextMenuRequested.connect(function (x, y) {
            win.menuX = x;
            win.menuY = y;
            termMenu.popup(win.contentItem, x, y);
        });
        tabs = tabs.concat([{ id: id, label: "Terminal", alerted: false }]);
        activate(id);
        return id;
    }

    function activate(id) {
        if (!views[id])
            return;
        if (win.findOpen) {
            findBar.view = views[id];
            findBar.close();
        }
        activeId = id;
        activeLabel = labelOf(id);
        setAlerted(id, false);
        for (var key in views)
            views[key].visible = (key === id);
        views[id].applySettings(cfg, th);
        views[id].forceActiveFocus();
    }

    function closeTab(id) {
        var i = indexOf(id);
        if (i < 0)
            return;
        var view = views[id];
        delete views[id];
        if (view) {
            view.kill();
            view.destroy();
        }
        var next = tabs.slice();
        next.splice(i, 1);
        tabs = next;
        if (tabs.length === 0) {
            newTab();
            return;
        }
        if (id === activeId)
            activate(tabs[Math.min(i, tabs.length - 1)].id);
    }

    function cycle(direction) {
        if (tabs.length < 2)
            return;
        var i = indexOf(activeId);
        i = (i + direction + tabs.length) % tabs.length;
        activate(tabs[i].id);
    }

    function activeView() {
        return views[activeId] || null;
    }

    function applyAll() {
        for (var id in views)
            views[id].applySettings(cfg, th);
    }

    function toast(text) {
        toastText = text;
        toastTimer.restart();
    }

    Connections {
        target: Bridge
        function onConfigChanged() { win.applyAll(); }
        function onPaletteChanged() { win.applyAll(); }
    }

    Component {
        id: termComponent
        TermView {
            anchors.fill: parent
            visible: false
        }
    }

    // --------------------------------------------------------------- chrome --

    Rectangle {
        id: bar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 38
        color: Util.alpha(win.th.background, Math.max(0.75, win.cfg.opacity))

        Row {
            id: strip
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5

            Repeater {
                model: win.tabs
                delegate: TabButton {
                    theme: win.th
                    monoFamily: win.mono
                    label: modelData.label
                    alerted: modelData.alerted
                    active: modelData.id === win.activeId
                    onActivated: win.activate(modelData.id)
                    onClosed: win.closeTab(modelData.id)
                }
            }

            Rectangle {
                width: 26
                height: 26
                radius: 7
                anchors.verticalCenter: parent.verticalCenter
                color: newArea.containsMouse ? Util.alpha(win.th.surface_alt, 0.9) : "transparent"
                Text {
                    anchors.centerIn: parent
                    text: Glyph.plus
                    font.family: Glyph.family
                    font.pixelSize: 10
                    color: Util.alpha(win.th.muted, 0.95)
                }
                MouseArea {
                    id: newArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: win.newTab()
                }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            Item {
                width: 26
                height: 26
                Text {
                    anchors.centerIn: parent
                    text: Glyph.chevronDown
                    font.family: Glyph.family
                    font.pixelSize: 10
                    color: Util.alpha(win.th.muted, 0.9)
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: win.activeView() && win.activeView().scrollToBottom()
                }
            }

            Item {
                width: 26
                height: 26
                Text {
                    anchors.centerIn: parent
                    text: Glyph.settings
                    font.family: Glyph.family
                    font.pixelSize: 11
                    color: gear.containsMouse ? win.th.accent : Util.alpha(win.th.muted, 0.9)
                }
                MouseArea {
                    id: gear
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: win.settingsOpen = !win.settingsOpen
                }
            }
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Util.alpha(win.th.border, 0.45)
        }
    }

    Item {
        id: host
        anchors.top: bar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        FindBar {
            id: findBar
            // The terminal views are created imperatively into this item, so
            // the bar has to sit above them explicitly.
            z: 20
            theme: win.th
            monoFamily: win.mono
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 8
            anchors.rightMargin: 12
            onClosed: {
                win.findOpen = false;
                if (win.activeView())
                    win.activeView().forceActiveFocus();
            }
        }
    }

    function toggleFind() {
        if (win.findOpen) {
            findBar.close();
            return;
        }
        var view = win.activeView();
        if (!view)
            return;
        findBar.view = view;
        win.findOpen = true;
        findBar.open();
    }

    // ---------------------------------------------------------------- toast --

    Rectangle {
        id: toastBox
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        width: toastLabel.implicitWidth + 26
        height: 28
        radius: 8
        visible: opacity > 0.01
        opacity: 0
        color: Util.alpha(win.th.surface_alt, 0.96)
        border.width: 1
        border.color: Util.alpha(win.th.accent, 0.35)

        Text {
            id: toastLabel
            anchors.centerIn: parent
            text: win.toastText
            color: win.th.foreground
            font.pixelSize: 11
        }
        Behavior on opacity { NumberAnimation { duration: 140 } }
    }

    Timer {
        id: toastTimer
        interval: 1900
        onTriggered: toastBox.opacity = 0
    }

    Connections {
        target: win
        function onToastTextChanged() { toastBox.opacity = win.toastText ? 1 : 0; }
    }

    // -------------------------------------------------------------- settings --

    SettingsSheet {
        id: sheet
        theme: win.th
        cfg: win.cfg
        fonts: win.fonts
        alpha: win.settingsOpen ? 255 : 0
        visible: win.settingsOpen
        onClosed: win.settingsOpen = false
        Behavior on alpha { NumberAnimation { duration: 120 } }
    }

    // ----------------------------------------------------------------- menu --

    Menu {
        id: termMenu
        MenuItem { text: "Copy"; enabled: win.activeView() && win.activeView().hasSelection
                   onTriggered: win.activeView() && win.activeView().copy() }
        MenuItem { text: "Paste"; onTriggered: win.activeView() && win.activeView().paste() }
        MenuItem { text: "Select all"; onTriggered: win.activeView() && win.activeView().selectAll() }
        MenuSeparator {}
        MenuItem { text: "Clear scrollback"; onTriggered: win.activeView() && win.activeView().clearScrollback() }
        MenuItem { text: "Settings"; onTriggered: win.settingsOpen = true }
    }

    // ------------------------------------------------------------ shortcuts --

    Shortcut {
        sequences: ["Ctrl+Shift+T"]
        onActivated: win.newTab()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+W"]
        onActivated: win.closeTab(win.activeId)
    }
    Shortcut {
        sequences: ["Ctrl+Shift+C"]
        onActivated: win.activeView() && win.activeView().copy()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+V"]
        onActivated: win.activeView() && win.activeView().paste()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+N", "Ctrl+PageDown", "Alt+Right"]
        onActivated: win.cycle(1)
    }
    Shortcut {
        sequences: ["Ctrl+Shift+P", "Ctrl+PageUp", "Alt+Left"]
        onActivated: win.cycle(-1)
    }
    Shortcut {
        sequences: ["Ctrl+Shift+Q"]
        onActivated: Qt.quit()
    }
    Shortcut {
        sequences: ["Ctrl+,"]
        onActivated: win.settingsOpen = !win.settingsOpen
    }
    Shortcut {
        sequences: ["Ctrl+Shift+F"]
        onActivated: win.toggleFind()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+G", "Shift+F3"]
        onActivated: win.findOpen && findBar.view && findBar.view.searchNext()
    }
    Shortcut {
        sequences: ["Shift+Ctrl+G", "F3"]
        onActivated: win.findOpen && findBar.view && findBar.view.searchPrevious()
    }
    Shortcut {
        sequences: ["Ctrl+=", "Ctrl+Shift+="]
        onActivated: win.activeView() && win.activeView().zoom(0.5)
    }
    Shortcut {
        sequences: ["Ctrl+-"]
        onActivated: win.activeView() && win.activeView().zoom(-0.5)
    }
    Shortcut {
        sequences: ["Ctrl+0"]
        onActivated: win.activeView() && win.activeView().resetZoom()
    }
    Shortcut {
        sequences: ["Ctrl+Shift+Up"]
        onActivated: win.activeView() && win.activeView().scrollToBottom()
    }
}
