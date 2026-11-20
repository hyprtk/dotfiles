import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import HyprtkShot 1.0
import "components"

ApplicationWindow {
    id: win

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config
    readonly property var info: Bridge.imageInfo
    readonly property var recent: Bridge.recentCaptures
    readonly property var tools: [
        { key: "cursor", label: "Select", hint: "Move or redraw the selection" },
        { key: "pen", label: "Pen", hint: "Freehand stroke" },
        { key: "line", label: "Line", hint: "Straight line" },
        { key: "arrow", label: "Arrow", hint: "Arrow with a head" },
        { key: "rect", label: "Rect", hint: "Rectangle outline" },
        { key: "ellipse", label: "Ellipse", hint: "Ellipse outline" },
        { key: "highlight", label: "Mark", hint: "Translucent highlighter" },
        { key: "marker", label: "Step", hint: "Numbered step marker" },
        { key: "text", label: "Text", hint: "Click, then type" },
        { key: "blur", label: "Blur", hint: "Blur an area (redaction)" },
        { key: "pixelate", label: "Pixel", hint: "Pixelate an area (redaction)" }
    ]
    readonly property var swatches: ["#fd4fb6", "#02dede", "#f9e2af", "#a6e3a1", "#89b4fa", "#ffffff"]

    visible: initialMode === "" && initialPath === "" && !Bridge.busy && !Bridge.overlayVisible
    width: 560
    height: 640
    minimumWidth: 480
    minimumHeight: 520
    color: th.background
    title: "Screenshot"
    flags: Qt.Window

    // Closing the launcher must end the process. `visible` is a binding, so it
    // is re-evaluated on the next state change and would otherwise bring a
    // hidden window back (or leave a windowless process in the task list).
    onClosing: Qt.quit()

    // A keybinding launch goes straight to the overlay and never shows this
    // window; a bare launch is the launcher.
    Component.onCompleted: {
        if (initialPath !== "")
            Bridge.openFile(initialPath);
        else if (initialMode !== "")
            Bridge.startStandalone(initialMode);
    }

    Connections {
        target: Bridge
        function onOverlayChanged() {
            if (Bridge.overlayVisible)
                overlay.showFullScreen();
            else
                overlay.close();
        }
    }

    // -- launcher ---------------------------------------------------------
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ColumnLayout {
                spacing: 2
                Text {
                    text: "Screenshot"
                    color: th.foreground
                    font.pixelSize: 20
                    font.bold: true
                }
                Text {
                    text: "grim capture · frozen overlay · annotate · save or copy"
                    color: th.muted
                    font.pixelSize: 12
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "v" + Bridge.version
                color: th.muted
                font.pixelSize: 11
            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: th.border; opacity: 0.5 }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 10
            rowSpacing: 10

            Repeater {
                model: [
                    { mode: "region", title: "Region", sub: "Drag a box on a frozen screen" },
                    { mode: "window", title: "Window", sub: "The focused window" },
                    { mode: "output", title: "Monitor", sub: "The monitor with focus" },
                    { mode: "full", title: "All outputs", sub: "The whole layout in one image" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 78
                    radius: 10
                    color: hover.containsMouse ? th.panelHover : th.panel
                    border.width: 1
                    border.color: hover.containsMouse ? th.accent2 : th.border

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 2
                        Text {
                            text: modelData.title
                            color: th.foreground
                            font.pixelSize: 15
                            font.bold: true
                        }
                        Text {
                            text: modelData.sub
                            color: th.muted
                            font.pixelSize: 11
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                    }
                    MouseArea {
                        id: hover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.capture(modelData.mode)
                    }
                }
            }
        }

        // -- options
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: opt.implicitHeight + 24
            radius: 10
            color: th.panelAlt
            border.width: 1
            border.color: th.border

            ColumnLayout {
                id: opt
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Text { text: "Delay"; color: th.muted; font.pixelSize: 12 }
                    Repeater {
                        model: [0, 2, 5, 10]
                        delegate: Rectangle {
                            required property int modelData
                            width: 40; height: 26; radius: 6
                            color: Number(cfg.delay) === modelData ? th.accent : th.panel
                            Text {
                                anchors.centerIn: parent
                                text: modelData === 0 ? "off" : modelData + "s"
                                color: Number(cfg.delay) === modelData ? th.textOnAccent : th.foreground
                                font.pixelSize: 11
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.setConfig("delay", modelData)
                            }
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Text { text: "Cursor"; color: th.muted; font.pixelSize: 12 }
                    Toggle { th: win.th; checked: cfg.cursor === true; onToggled: Bridge.setConfig("cursor", !checked) }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Toggle { th: win.th; label: "Copy after save"; checked: cfg.copy === true; onToggled: Bridge.setConfig("copy", !checked) }
                    Toggle { th: win.th; label: "Annotate"; checked: cfg.annotate === true; onToggled: Bridge.setConfig("annotate", !checked) }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "Save to"; color: th.muted; font.pixelSize: 12 }
                    Text {
                        Layout.fillWidth: true
                        text: cfg.dir
                        color: th.foreground
                        font.pixelSize: 11
                        elide: Text.ElideMiddle
                    }
                    Text {
                        text: "Open"
                        color: th.accent2
                        font.pixelSize: 11
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Bridge.openPath(cfg.dir)
                        }
                    }
                }
            }
        }

        // -- recent
        Text {
            text: "Recent"
            color: th.muted
            font.pixelSize: 12
            Layout.topMargin: 2
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: recent
            Text {
                anchors.centerIn: parent
                visible: recent.length === 0
                text: "No captures yet — press a mode above, or Print."
                color: th.muted
                font.pixelSize: 12
            }
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 40
                radius: 7
                color: rowHover.containsMouse ? th.panelHover : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8
                    Text {
                        text: modelData.name
                        color: th.foreground
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                    Text { text: modelData.width + "×" + modelData.height; color: th.muted; font.pixelSize: 11 }
                    Text { text: modelData.size; color: th.muted; font.pixelSize: 11 }
                    Text {
                        text: "Open"
                        color: th.accent2
                        font.pixelSize: 11
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Bridge.openPath(modelData.path)
                        }
                    }
                    Text {
                        text: "Delete"
                        color: th.danger
                        font.pixelSize: 11
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Bridge.deleteCapture(modelData.path)
                        }
                    }
                }
                MouseArea {
                    id: rowHover
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Print → region · Super+Shift+Print → recorder"
                color: th.muted
                font.pixelSize: 11
            }
            Item { Layout.fillWidth: true }
            Text {
                visible: !Bridge.hasGrim
                text: "grim is missing"
                color: th.danger
                font.pixelSize: 11
            }
        }
    }

    // -- overlay ----------------------------------------------------------
    Window {
        id: overlay
        visible: false
        color: "#000000"
        flags: Qt.Window | Qt.FramelessWindowHint
        title: "hyprtk-shot"

        // Close from the compositor (a keybind, a window rule) must quit a
        // keybinding-started instance instead of leaving a hidden process.
        onClosing: function (event) {
            if (Bridge.standalone)
                Bridge.quit();
        }

        CaptureCanvas {
            id: canvas
            anchors.fill: parent
            bridge: Bridge
            onTextRequested: function (x, y) { textEntry.open(x, y); }
        }

        // Selection size pill
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 18
            anchors.horizontalCenter: parent.horizontalCenter
            width: dims.implicitWidth + 22
            height: 30
            radius: 15
            color: th.background
            opacity: 0.92
            border.width: 1
            border.color: th.border

            Text {
                id: dims
                anchors.centerIn: parent
                text: {
                    var sel = Bridge.selectionInfo;
                    if (!sel.width) return "Drag to select · Esc to close";
                    return sel.width + " × " + sel.height + "  ·  " + info.label;
                }
                color: th.foreground
                font.pixelSize: 12
            }
        }

        // Toolbar
        Rectangle {
            id: bar
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 26
            anchors.horizontalCenter: parent.horizontalCenter
            width: barCol.implicitWidth + 24
            height: barCol.implicitHeight + 20
            radius: 14
            color: th.background
            opacity: 0.95
            border.width: 1
            border.color: th.border

            ColumnLayout {
                id: barCol
                anchors.centerIn: parent
                spacing: 8

                RowLayout {
                    spacing: 4
                    Repeater {
                        model: win.tools
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.max(52, labelText.implicitWidth + 18)
                            height: 30
                            radius: 8
                            color: Bridge.tool === modelData.key ? th.accent : (toolHover.containsMouse ? th.panelHover : "transparent")
                            Text {
                                id: labelText
                                anchors.centerIn: parent
                                text: modelData.label
                                color: Bridge.tool === modelData.key ? th.textOnAccent : th.foreground
                                font.pixelSize: 11
                            }
                            MouseArea {
                                id: toolHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.setTool(modelData.key)
                            }
                        }
                    }
                    Item { Layout.preferredWidth: 6; Layout.preferredHeight: 1 }
                    BarButton { th: win.th; label: "Undo"; usable: Bridge.canUndo; onClicked: Bridge.undo() }
                    BarButton { th: win.th; label: "Redo"; usable: Bridge.canRedo; onClicked: Bridge.redo() }
                    BarButton { th: win.th; label: "Clear"; usable: Bridge.canUndo; onClicked: Bridge.clearShapes() }
                }

                RowLayout {
                    spacing: 6
                    Repeater {
                        model: win.swatches
                        delegate: Rectangle {
                            required property string modelData
                            width: 22; height: 22; radius: 11
                            color: modelData
                            border.width: Bridge.color === modelData ? 3 : 1
                            border.color: Bridge.color === modelData ? th.foreground : th.border
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.setColor(modelData)
                            }
                        }
                    }
                    Item { Layout.preferredWidth: 10; Layout.preferredHeight: 1 }
                    Text { text: "Size"; color: th.muted; font.pixelSize: 11 }
                    Rectangle {
                        Layout.preferredWidth: 90
                        Layout.preferredHeight: 4
                        radius: 2
                        color: th.border
                        Rectangle {
                            width: Math.max(4, parent.width * (Bridge.stroke - 1) / 15)
                            height: parent.height
                            radius: 2
                            color: th.accent2
                        }
                        MouseArea {
                            anchors.fill: parent
                            anchors.topMargin: -8
                            anchors.bottomMargin: -8
                            cursorShape: Qt.PointingHandCursor
                            onClicked: function (mouse) {
                                Bridge.setStroke(1 + Math.round(15 * Math.max(0, Math.min(1, mouse.x / width))));
                            }
                        }
                    }
                    Item { Layout.fillWidth: true }
                    BarButton { th: win.th; label: "Save"; onClicked: { Bridge.save(); Bridge.close(); } }
                    BarButton { th: win.th; label: "Copy"; onClicked: { Bridge.copy(); Bridge.close(); } }
                    BarButton {
                        th: win.th
                        label: "Save + Copy"
                        primary: true
                        onClicked: Bridge.saveAndCopy()
                    }
                    BarButton { th: win.th; label: "Close"; onClicked: Bridge.close() }
                }
            }
        }

        // Inline text entry, placed where the click landed.
        Rectangle {
            id: textEntry
            visible: false
            width: 280
            height: 38
            radius: 8
            color: th.panel
            border.width: 1
            border.color: th.accent2
            z: 10

            property real anchorX: 0
            property real anchorY: 0

            function open(x, y) {
                anchorX = Math.min(x, Math.max(10, overlay.width - width - 10));
                anchorY = Math.min(y, Math.max(10, overlay.height - height - 10));
                visible = true;
                field.text = "";
                field.forceActiveFocus();
            }

            function close() {
                visible = false;
                field.text = "";
            }

            function commit() {
                canvas.commitText(field.text);
                close();
            }

            x: anchorX
            y: anchorY

            TextInput {
                id: field
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: TextInput.AlignVCenter
                color: th.foreground
                font.pixelSize: 14
                selectionColor: th.accent
                selectedTextColor: th.textOnAccent
                clip: true
                onAccepted: textEntry.commit()
                Keys.onEscapePressed: textEntry.close()
            }
        }

        Shortcut { sequence: "Escape"; onActivated: Bridge.close() }
        Shortcut { sequence: "Return"; onActivated: Bridge.saveAndCopy() }
        Shortcut { sequence: "Ctrl+S"; onActivated: { Bridge.save(); Bridge.close(); } }
        Shortcut { sequence: "Ctrl+C"; onActivated: { Bridge.copy(); Bridge.close(); } }
        Shortcut { sequence: "Ctrl+Z"; onActivated: Bridge.undo() }
        Shortcut { sequence: "Ctrl+Shift+Z"; onActivated: Bridge.redo() }
        Shortcut { sequence: "Ctrl+A"; onActivated: Bridge.selectAll() }
        Shortcut { sequence: "P"; onActivated: Bridge.setTool("pen") }
        Shortcut { sequence: "L"; onActivated: Bridge.setTool("line") }
        Shortcut { sequence: "A"; onActivated: Bridge.setTool("arrow") }
        Shortcut { sequence: "R"; onActivated: Bridge.setTool("rect") }
        Shortcut { sequence: "E"; onActivated: Bridge.setTool("ellipse") }
        Shortcut { sequence: "H"; onActivated: Bridge.setTool("highlight") }
        Shortcut { sequence: "M"; onActivated: Bridge.setTool("marker") }
        Shortcut { sequence: "T"; onActivated: Bridge.setTool("text") }
        Shortcut { sequence: "B"; onActivated: Bridge.setTool("blur") }
        Shortcut { sequence: "X"; onActivated: Bridge.setTool("pixelate") }
        Shortcut { sequence: "V"; onActivated: Bridge.setTool("cursor") }
    }
}
