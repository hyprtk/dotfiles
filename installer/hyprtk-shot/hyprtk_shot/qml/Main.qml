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
    // Window capture is a choice, not a guess: the card opens this list.
    property bool picking: false

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
    onClosing: Bridge.quit()

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
        // Unpinning a keybinding-started capture ends the session; the window
        // is the one that decides, so the bridge has no quit side effect.
        function onPinChanged() {
            if (!Bridge.pinned && Bridge.standalone && !Bridge.overlayVisible)
                Bridge.quit();
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
                    { mode: "window", title: "Window", sub: "Any open window, from a list" },
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
                        onClicked: {
                            if (modelData.mode === "window") {
                                Bridge.refreshWindows();
                                win.picking = true;
                            } else {
                                Bridge.capture(modelData.mode);
                            }
                        }
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
                    Toggle {
                        th: win.th
                        label: "Cross-output"
                        checked: cfg.picker === "slurp"
                        onToggled: Bridge.setConfig("picker", checked ? "overlay" : "slurp")
                    }
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
                text: "Print → region · Shift = square · arrows nudge"
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


    // -- window picker ----------------------------------------------------
    Rectangle {
        anchors.fill: parent
        visible: win.picking
        color: Qt.rgba(0, 0, 0, 0.5)
        z: 20

        MouseArea {
            anchors.fill: parent
            onClicked: win.picking = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 60, 430)
            height: Math.min(parent.height - 90, 430)
            radius: 12
            color: th.panel
            border.width: 1
            border.color: th.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: "Capture a window"
                        color: th.foreground
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Bridge.windows.length + " open"
                        color: th.muted
                        font.pixelSize: 11
                    }
                }

                // The fast path stays one click away.
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    radius: 6
                    color: focusedRow.containsMouse ? th.panelHover : "transparent"
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Focused window"
                        color: th.accent2
                        font.pixelSize: 12
                    }
                    MouseArea {
                        id: focusedRow
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { win.picking = false; Bridge.capture("window"); }
                    }
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: Bridge.windows
                    spacing: 2
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: 34
                        radius: 6
                        color: pickRow.containsMouse ? th.panelHover : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8
                            Text {
                                text: modelData.class
                                color: th.muted
                                font.pixelSize: 11
                                Layout.maximumWidth: 110
                                elide: Text.ElideRight
                            }
                            Text {
                                text: modelData.title
                                color: th.foreground
                                font.pixelSize: 12
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            id: pickRow
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { win.picking = false; Bridge.captureWindow(modelData.address); }
                        }
                    }
                }
            }
        }
    }



    // -- capture countdown ------------------------------------------------
    // Shown only while the delay runs, and hidden 120 ms before grim so the
    // number can never end up in the capture.
    Window {
        id: countdownWindow
        visible: Bridge.countdown > 0
        width: 200
        height: 200
        color: "transparent"
        title: "hyprtk-shot countdown"
        transientParent: null
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
               | Qt.WindowDoesNotAcceptFocus

        Rectangle {
            anchors.fill: parent
            radius: 18
            color: th.background
            opacity: 0.94
            border.width: 1
            border.color: th.accent2

            Text {
                anchors.centerIn: parent
                text: Bridge.countdown
                color: th.foreground
                font.pixelSize: 96
                font.bold: true
            }
        }
    }

    // -- pinned capture ---------------------------------------------------
    // A plain image window over the file Bridge.pin() wrote: the overlay is
    // fullscreen and has to close, so there is nothing left to paint from.
    Window {
        id: pinnedWindow
        visible: Bridge.pinned
        width: Bridge.pinWidth
        height: Bridge.pinHeight
        color: "transparent"
        title: "hyprtk-shot pinned"
        // A pinned capture must survive the overlay closing: without this it is
        // a transient child of the application window and dies with it.
        transientParent: null
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

        Image {
            id: pinImage
            anchors.fill: parent
            source: Bridge.pinPath ? "file://" + Bridge.pinPath : ""
            fillMode: Image.PreserveAspectFit
            cache: false
        }

        // A compositor close (Super+Q on the pin) is a dismissal too.
        onClosing: Bridge.unpin()

        // Dismissal is deliberate: a close button that appears on hover, plus
        // double-click. (A QML Shortcut and a Keys handler here both fired on
        // their own when the window mapped.)
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
            hoverEnabled: true
            onDoubleClicked: Bridge.unpin()
            onClicked: pinHover.visible = true
            onExited: pinHover.visible = false
        }

        Rectangle {
            id: pinHover
            visible: false
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 6
            width: 22
            height: 22
            radius: 11
            color: th.panel
            border.width: 1
            border.color: th.border
            Text {
                anchors.centerIn: parent
                text: "×"
                color: th.foreground
                font.pixelSize: 14
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: Bridge.unpin()
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
            // The bridge's `finished` signal is the one place that decides
            // whether the process ends (a pinned capture keeps it alive), so a
            // compositor close just cancels the session.
            Bridge.cancel();
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
                    if (!Bridge.selectionReady)
                        return "Drag to select a region · Esc to cancel";
                    var sel = Bridge.selectionInfo;
                    return sel.width + " × " + sel.height + "  ·  " + info.label
                           + "  ·  Enter saves";
                }
                color: th.foreground
                font.pixelSize: 12
            }
        }

        // Toolbar: only once a region exists, so the first step is unambiguous.
        Rectangle {
            id: bar
            visible: Bridge.selectionReady
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
                    BarButton { th: win.th; label: "Pin"; onClicked: Bridge.pin() }
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

        Shortcut { sequence: "Escape"; onActivated: { console.log("KEY escape"); Bridge.close(); } }
        Shortcut { sequence: "Return"; onActivated: { console.log("KEY return"); Bridge.saveAndCopy(); } }
        Shortcut { sequence: "Ctrl+S"; onActivated: { console.log("KEY ctrl+s"); Bridge.save(); Bridge.close(); } }
        Shortcut { sequence: "Ctrl+C"; onActivated: { Bridge.copy(); Bridge.close(); } }
        Shortcut { sequence: "Ctrl+Z"; onActivated: Bridge.undo() }
        Shortcut { sequence: "Ctrl+Shift+Z"; onActivated: Bridge.redo() }
        Shortcut { sequence: "Ctrl+A"; onActivated: Bridge.selectAll() }
        // Arrows nudge the selection; disabled while the text tool has a field
        // open, so they move the caret instead of the box.
        Shortcut { sequence: "Left"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(-1, 0) }
        Shortcut { sequence: "Right"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(1, 0) }
        Shortcut { sequence: "Up"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(0, -1) }
        Shortcut { sequence: "Down"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(0, 1) }
        Shortcut { sequence: "Shift+Left"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(-10, 0) }
        Shortcut { sequence: "Shift+Right"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(10, 0) }
        Shortcut { sequence: "Shift+Up"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(0, -10) }
        Shortcut { sequence: "Shift+Down"; enabled: !textEntry.visible; onActivated: Bridge.nudgeSelection(0, 10) }
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
