import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "theme/util.js" as Util
import "components"

ApplicationWindow {
    id: win

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config
    readonly property real scale: Number(cfg.font_scale || 1)
    readonly property string mono: "JetBrainsMono Nerd Font Mono"
    readonly property var operators: ["+", "-", "*", "/", "^", "%", "&", "|", "<<", ">>", " xor "]

    property string expression: ""
    property var result: ({ ok: false, display: "", error: "", bases: {}, value: "" })
    property string mode: cfg.keypad || "basic"
    property bool historyOpen: false
    property bool settingsOpen: false
    property bool justCommitted: false
    property bool copied: false
    property int historyIndex: -1

    visible: true
    width: 460
    height: 700
    minimumWidth: 360
    minimumHeight: 560
    color: th.background
    title: expression.length > 0 ? expression : "Calculator"
    flags: cfg.always_on_top ? (Qt.Window | Qt.WindowStaysOnTopHint) : Qt.Window

    // -- behaviour --------------------------------------------------------
    function refresh() {
        if (cfg.live === false)
            return;
        result = Bridge.evaluate(expression);
    }

    function commit() {
        var row = Bridge.commit(expression);
        result = row;
        if (row.ok)
            justCommitted = true;
        historyIndex = -1;
        entry.forceActiveFocus();
    }

    function isOperator(token) {
        return operators.indexOf(token) >= 0;
    }

    function insertToken(token) {
        if (justCommitted) {
            var base = result.ok ? (result.value || result.display) : "";
            entry.text = isOperator(token) ? base + token : token;
            entry.cursorPosition = entry.text.length;
            justCommitted = false;
            return;
        }
        if (mode === "programmer" && /^[0-9A-F]$/.test(token))
            insertHex(token);
        else
            insertAtCursor(token);
    }

    // Hex literals are written the Python way (0x1F). Tapping A-F, or a digit
    // while a hex literal is being typed, continues it instead of starting a
    // new one.
    // TextInput.insert takes (position, text); a one-argument call is a QML
    // "Insufficient arguments" error at runtime, not at load time.
    function insertAtCursor(text) {
        entry.insert(entry.cursorPosition, text);
    }

    function insertHex(digit) {
        var before = entry.text.slice(0, entry.cursorPosition);
        if (/(0x[0-9A-Fa-f]*)$/.test(before))
            insertAtCursor(digit);
        else
            insertAtCursor("0x" + digit);
    }

    function backspace() {
        justCommitted = false;
        if (entry.selectedText.length > 0)
            entry.remove(entry.selectionStart, entry.selectionEnd);
        else if (entry.cursorPosition > 0)
            entry.remove(entry.cursorPosition - 1, entry.cursorPosition);
    }

    function clearAll() {
        justCommitted = false;
        historyIndex = -1;
        entry.text = "";
        result = { ok: false, display: "", error: "", bases: {}, value: "" };
        entry.forceActiveFocus();
    }

    function negate() {
        var text = expression;
        if (text.indexOf("-(") === 0 && text.slice(-1) === ")")
            text = text.slice(2, -1);
        else if (text.indexOf("-") === 0)
            text = text.slice(1);
        else
            text = text.length > 0 ? "-(" + text + ")" : "-";
        entry.text = text;
        entry.cursorPosition = text.length;
        justCommitted = false;
    }

    function copyResult() {
        var text = result.ok ? result.display : "";
        if (!text)
            return;
        if (Bridge.copy(text)) {
            copied = true;
            copyTimer.restart();
        }
    }

    function recall(row) {
        var text = Bridge.recall(row);
        if (!text)
            return;
        entry.text = text;
        entry.cursorPosition = text.length;
        justCommitted = false;
        historyOpen = false;
        entry.forceActiveFocus();
    }

    function stepHistory(delta) {
        var rows = Bridge.historyRows;
        if (rows.length === 0)
            return;
        var index = Math.max(0, Math.min(rows.length - 1, historyIndex + delta));
        historyIndex = index;
        var text = rows[index].expression;
        entry.text = text;
        entry.cursorPosition = text.length;
        justCommitted = false;
    }

    function handleAction(name) {
        if (name === "clear")
            clearAll();
        else if (name === "back")
            backspace();
        else if (name === "sign")
            negate();
        else if (name === "equals")
            commit();
        else if (name.indexOf("hex:") === 0)
            insertHex(name.slice(4));
        else if (name.indexOf("memory:") === 0)
            Bridge.memory(name.slice(7));
    }

    // `expression` is the source of truth. The TextInput writes it on every
    // keystroke, which breaks its own `text:` binding, so the reverse direction
    // is restored here: anything that assigns the property (a test, a history
    // recall, a future command palette) lands in the field.
    onExpressionChanged: {
        if (entry.text !== win.expression)
            entry.text = win.expression;
        refresh();
    }

    Component.onCompleted: {
        // Restore the saved size once. Binding width/height to the config would
        // snap the window back every time an unrelated setting changed.
        win.width = Number(cfg.width || 460);
        win.height = Number(cfg.height || 700);
        entry.forceActiveFocus();
    }

    Connections {
        target: Bridge
        function onSettingsChanged() {
            win.mode = Bridge.config.keypad || "basic";
        }
    }

    Timer {
        id: copyTimer
        interval: 1200
        onTriggered: win.copied = false
    }

    onClosing: {
        Bridge.setConfig("width", win.width);
        Bridge.setConfig("height", win.height);
    }

    // -- top bar ----------------------------------------------------------
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: "Calculator"
                font.pixelSize: 13 * win.scale
                font.weight: Font.DemiBold
                color: win.th ? win.th.foreground : "#e5e7eb"
            }

            Segmented {
                Layout.fillWidth: true
                Layout.maximumWidth: 210
                Layout.leftMargin: 8
                th: win.th
                fontScale: win.scale
                options: [
                    { value: "basic", label: "Basic" },
                    { value: "scientific", label: "Sci" },
                    { value: "programmer", label: "Prog" }
                ]
                value: win.mode
                onPicked: function (value) {
                    win.mode = value;
                    Bridge.setConfig("keypad", value);
                }
            }

            IconButton {
                th: win.th
                glyph: Glyph.history
                active: win.historyOpen
                onClicked: win.historyOpen = !win.historyOpen
            }

            IconButton {
                th: win.th
                glyph: Glyph.settings
                active: win.settingsOpen
                onClicked: win.settingsOpen = !win.settingsOpen
            }
        }

        // -- display ------------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(display.implicitHeight + 28, 132)
            radius: 16
            color: win.th ? win.th.display : "#12141e"
            border.width: 1
            border.color: Util.alpha(win.th ? win.th.foreground : "#ffffff", 0.08)

            ColumnLayout {
                id: display
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        text: (win.cfg.angle || "deg").toUpperCase()
                        font.pixelSize: 9.5 * win.scale
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.6
                        color: win.th ? win.th.accent2 : "#22d3ee"
                    }

                    Text {
                        visible: Bridge.memorySet === true
                        text: "M " + Bridge.memoryValue
                        font.pixelSize: 9.5 * win.scale
                        font.family: win.mono
                        color: win.th ? win.th.dim : "#6e7075"
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        visible: win.copied
                        text: "Copied"
                        font.pixelSize: 9.5 * win.scale
                        color: win.th ? win.th.success : "#a6e3a1"
                    }

                    IconButton {
                        th: win.th
                        glyph: Glyph.copy
                        enabled: win.result.ok
                        onClicked: win.copyResult()
                    }
                }

                TextInput {
                    id: entry

                    Layout.fillWidth: true
                    Layout.preferredHeight: 34 * win.scale
                    text: win.expression
                    font.family: win.mono
                    font.pixelSize: 21 * win.scale
                    color: win.th ? win.th.foreground : "#e5e7eb"
                    selectionColor: win.th ? win.th.accent : "#c084fc"
                    selectedTextColor: win.th ? win.th.text_on_accent : "#11111b"
                    horizontalAlignment: TextInput.AlignLeft
                    verticalAlignment: TextInput.AlignVCenter
                    clip: true
                    focus: true
                    selectByMouse: true

                    onTextChanged: {
                        if (win.expression !== text)
                            win.expression = text;
                    }

                    Keys.onPressed: function (event) {
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            win.commit();
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Escape) {
                            win.clearAll();
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Up) {
                            win.stepHistory(1);
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Down) {
                            win.stepHistory(-1);
                            event.accepted = true;
                        } else if (event.modifiers & Qt.ControlModifier) {
                            if (event.key === Qt.Key_C && entry.selectedText.length === 0) {
                                win.copyResult();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_L) {
                                win.clearAll();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_H) {
                                win.historyOpen = !win.historyOpen;
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Comma) {
                                win.settingsOpen = !win.settingsOpen;
                                event.accepted = true;
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    text: win.result.ok ? win.result.display
                          : (win.expression.length === 0 ? "0" : " ")
                    elide: Text.ElideLeft
                    font.family: win.mono
                    font.pixelSize: 30 * win.scale
                    font.weight: Font.DemiBold
                    color: win.th ? win.th.foreground : "#e5e7eb"
                }

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    text: win.result.error
                    visible: win.result.error.length > 0
                    elide: Text.ElideLeft
                    font.pixelSize: 10.5 * win.scale
                    color: win.th ? win.th.danger : "#f38ba8"
                }

                // Programmer readout: the same integer in all four bases.
                GridLayout {
                    id: bases
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    columns: 2
                    columnSpacing: 10
                    rowSpacing: 1
                    visible: win.mode === "programmer"
                             && win.result.bases !== undefined
                             && Object.keys(win.result.bases).length > 0

                    Repeater {
                        model: [
                            { base: "16", label: "HEX" },
                            { base: "10", label: "DEC" },
                            { base: "8", label: "OCT" },
                            { base: "2", label: "BIN" }
                        ]

                        delegate: Item {
                            id: baseCell

                            required property var modelData

                            Layout.fillWidth: true
                            implicitHeight: 17 * win.scale

                            Text {
                                id: baseLabel
                                text: baseCell.modelData.label
                                font.pixelSize: 9.5 * win.scale
                                font.weight: Font.DemiBold
                                color: win.th ? win.th.accent2 : "#22d3ee"
                            }

                            Text {
                                anchors.left: baseLabel.right
                                anchors.leftMargin: 8
                                anchors.right: parent.right
                                text: win.result.bases[baseCell.modelData.base] || ""
                                elide: Text.ElideLeft
                                font.family: win.mono
                                font.pixelSize: 10.5 * win.scale
                                color: win.th ? win.th.foreground : "#e5e7eb"
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var text = win.result.bases[baseCell.modelData.base];
                                    if (text)
                                        Bridge.copy(text);
                                }
                            }
                        }
                    }
                }
            }
        }

        // -- keypad -------------------------------------------------------
        Keypad {
            Layout.fillWidth: true
            Layout.fillHeight: true
            th: win.th
            mode: win.mode
            fontScale: win.scale
            onToken: function (text) { win.insertToken(text) }
            onAction: function (name) { win.handleAction(name) }
        }
    }

    // -- overlays ---------------------------------------------------------
    Rectangle {
        anchors.fill: parent
        visible: win.historyOpen || win.settingsOpen
        color: Util.alpha(win.th ? win.th.background : "#090b15", 0.6)

        MouseArea {
            anchors.fill: parent
            onClicked: {
                win.historyOpen = false;
                win.settingsOpen = false;
            }
        }
    }

    HistoryPanel {
        id: historyPanel

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 14
        width: Math.min(280, parent.width - 60)
        visible: win.historyOpen
        th: win.th
        fontScale: win.scale
        rows: Bridge.historyRows
        onRecall: function (row) { win.recall(row) }
        onClearRequested: Bridge.clearHistory()
        onClosed: win.historyOpen = false
    }

    SettingsSheet {
        id: settingsSheet

        anchors.centerIn: parent
        width: Math.min(380, win.width - 40)
        height: Math.min(settingsSheet.contentHeight, win.height - 40)
        visible: win.settingsOpen
        th: win.th
        cfg: win.cfg
        version: Bridge.version
        fontScale: win.scale
        onClosed: win.settingsOpen = false
    }
}
