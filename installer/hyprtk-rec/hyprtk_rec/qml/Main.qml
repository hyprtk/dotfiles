import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: win

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config
    readonly property var recState: Bridge.status
    readonly property var recent: Bridge.recentRecordings
    readonly property bool rec: Bridge.recording
    readonly property bool paused: Bridge.paused

    // The idle summary: what pressing Record would do right now.
    readonly property string sourceLabel: {
        if (cfg.source === "region") return "Region";
        if (cfg.source === "window") return Bridge.windowLabel;
        var rows = Bridge.monitors;
        for (var i = 0; i < rows.length; i++)
            if (rows[i].focused) return rows[i].name;
        return rows.length > 0 ? rows[0].name : "Monitor";
    }
    readonly property string summary: sourceLabel + " · " + cfg.fps + " fps · "
        + String(cfg.codec).toUpperCase() + " · "
        + (cfg.audio === "none" ? "no audio"
           : cfg.audio === "mic" ? "microphone"
           : cfg.audio === "mix" ? "system + mic"
           : "system audio")

    property bool blink: true
    // The window picker is a plain overlay with our own colours: a Controls
    // Popup/Menu would take its palette from the GTK platform theme.
    property bool picking: false
    // The settings sheet holds what the daily panel does not: where files go,
    // whether to notify, how long the recent list is, and which encoder wins.
    property bool settingsOpen: false
    property string dirText: cfg.dir

    visible: true
    width: 560
    height: 720
    minimumWidth: 500
    minimumHeight: 600
    color: th.background
    title: rec ? "Recording" : "Screen Recorder"
    flags: Qt.Window

    function commitDir() {
        var value = dirText.trim();
        Bridge.setConfig("dir", value);
        win.dirText = Bridge.config.dir;
    }

    // Closing the window ends the window process. The encoder keeps running on
    // its own session and the state file still answers `stop`, which is exactly
    // the same situation as a keybinding-started recording.
    onClosing: Qt.quit()

    Timer {
        interval: 800
        repeat: true
        running: win.rec && !win.paused
        onTriggered: win.blink = !win.blink
    }

    Connections {
        target: Bridge
        function onToast(title, body) { toast.show(title, body); }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        // -- header -------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ColumnLayout {
                spacing: 2
                Text {
                    text: "Screen Recorder"
                    color: th.foreground
                    font.pixelSize: 20
                    font.bold: true
                }
                Text {
                    text: "wf-recorder · wl-screenrec · Wayland-native"
                    color: th.muted
                    font.pixelSize: 12
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: Bridge.backendLabel
                color: th.muted
                font.pixelSize: 11
            }
            Text {
                text: "Settings"
                color: th.accent2
                font.pixelSize: 11
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { win.dirText = Bridge.config.dir; win.settingsOpen = true; }
                }
            }
        }

        // -- record card --------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 156
            radius: 12
            color: rec ? th.panel : th.panelAlt
            border.width: 1
            border.color: rec ? (paused ? th.paused : th.record) : th.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    // Status dot
                    Rectangle {
                        width: 12
                        height: 12
                        radius: 6
                        color: rec ? (paused ? th.paused : th.record) : th.idle
                        opacity: rec && !paused && !win.blink ? 0.35 : 1
                    }
                    Text {
                        text: rec ? (paused ? "PAUSED" : "RECORDING") : "READY"
                        color: rec ? (paused ? th.paused : th.record) : th.muted
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 1
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        visible: rec
                        text: Bridge.elapsed
                        color: th.foreground
                        font.pixelSize: 26
                        font.bold: true
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: rec ? (recState.path || "") : summary
                    color: th.muted
                    font.pixelSize: 11
                    elide: Text.ElideMiddle
                    wrapMode: Text.NoWrap
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // Big primary control
                    Rectangle {
                        width: 168
                        height: 44
                        radius: 10
                        color: rec ? th.record : th.accent
                        Text {
                            anchors.centerIn: parent
                            text: rec ? "Stop recording" : "Start recording"
                            color: rec ? "#ffffff" : th.textOnAccent
                            font.pixelSize: 14
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: rec ? Bridge.stop() : Bridge.start()
                        }
                    }

                    ActionButton {
                        th: win.th
                        visible: rec
                        label: paused ? "Resume" : "Pause"
                        onClicked: Bridge.togglePause()
                    }
                    ActionButton {
                        th: win.th
                        visible: rec && Bridge.replayActive
                        label: "Save replay"
                        onClicked: Bridge.saveReplay()
                    }
                    ActionButton {
                        th: win.th
                        label: "Refresh"
                        usable: !rec
                        onClicked: { Bridge.refreshSources(); Bridge.refreshStatus(); }
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        visible: !Bridge.canRecord
                        text: "wf-recorder is not installed"
                        color: th.danger
                        font.pixelSize: 11
                    }
                }
            }
        }

        // -- source / options ---------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: options.implicitHeight + 26
            radius: 10
            color: th.panelAlt
            border.width: 1
            border.color: th.border

            ColumnLayout {
                id: options
                anchors.fill: parent
                anchors.margins: 13
                spacing: 9

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Source"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
                    Segmented {
                        th: win.th
                        current: cfg.source
                        options: [{ v: "output", l: "Monitor" }, { v: "region", l: "Region" },
                                  { v: "window", l: "Window" }]
                        onPicked: function (value) { Bridge.setConfig("source", value); }
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        visible: cfg.source === "window"
                        text: Bridge.windowLabel
                        color: th.mutedText
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.maximumWidth: 120
                    }
                    Text {
                        visible: cfg.source === "window"
                        text: "Pick"
                        color: th.accent2
                        font.pixelSize: 11
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.picking = true
                        }
                    }
                    Text {
                        visible: cfg.source !== "window"
                        text: win.sourceLabel
                        color: th.mutedText
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.maximumWidth: 160
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Audio"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
                    Segmented {
                        th: win.th
                        current: cfg.audio
                        options: [{ v: "none", l: "Off" }, { v: "system", l: "System" },
                                  { v: "mic", l: "Mic" }, { v: "mix", l: "Both" }]
                        onPicked: function (value) { Bridge.setConfig("audio", value); }
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: cfg.audio === "mic" ? "SIGSTOP-safe · default input"
                              : cfg.audio === "mix" ? "null sink · unloaded on stop" : ""
                        color: th.mutedText
                        font.pixelSize: 11
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Frame"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
                    Segmented {
                        th: win.th
                        current: Number(cfg.fps)
                        options: [{ v: 30, l: "30" }, { v: 60, l: "60" }, { v: 120, l: "120" }]
                        onPicked: function (value) { Bridge.setConfig("fps", value); }
                    }
                    Text { text: "Codec"; color: th.muted; font.pixelSize: 12 }
                    Segmented {
                        th: win.th
                        current: cfg.codec
                        options: [{ v: "h264", l: "H.264" }, { v: "hevc", l: "HEVC" },
                                  { v: "vp9", l: "VP9" }]
                        onPicked: function (value) { Bridge.setConfig("codec", value); }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Quality"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
                    Segmented {
                        th: win.th
                        current: cfg.quality
                        options: [{ v: "low", l: "Low" }, { v: "medium", l: "Medium" },
                                  { v: "high", l: "High" }]
                        onPicked: function (value) { Bridge.setConfig("quality", value); }
                    }
                    Text { text: "Countdown"; color: th.muted; font.pixelSize: 12 }
                    Segmented {
                        th: win.th
                        current: Number(cfg.countdown)
                        options: [{ v: 0, l: "off" }, { v: 3, l: "3s" }, { v: 5, l: "5s" }]
                        onPicked: function (value) { Bridge.setConfig("countdown", value); }
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Format"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
                    Segmented {
                        th: win.th
                        current: cfg.container
                        options: [{ v: "mp4", l: "MP4" }, { v: "mkv", l: "MKV" },
                                  { v: "webm", l: "WebM" }, { v: "gif", l: "GIF" }]
                        onPicked: function (value) { Bridge.setConfig("container", value); }
                    }
                    Text {
                        text: cfg.container === "gif" ? "GIF · 30 fps max · wf-recorder" : ""
                        color: th.mutedText
                        font.pixelSize: 11
                    }
                    Item { Layout.fillWidth: true }
                    Text { text: "Encoder"; color: th.muted; font.pixelSize: 12 }
                    Segmented {
                        th: win.th
                        current: cfg.vaapi === true
                        options: [{ v: false, l: "CPU" }, { v: true, l: "VAAPI" }]
                        opacity: Bridge.vaapiAvailable ? 1 : 0.5
                        onPicked: function (value) {
                            if (value && !Bridge.vaapiAvailable) return;
                            Bridge.setConfig("vaapi", value);
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: !Bridge.vaapiAvailable || cfg.vaapi === true
                    text: Bridge.vaapiAvailable
                          ? (cfg.vaapi === true ? "GPU encoding · h264/hevc only" : "")
                          : "GPU encoding unavailable: " + Bridge.vaapiReason
                    color: Bridge.vaapiAvailable ? th.mutedText : th.danger
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "Save to"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 58 }
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

        // -- recent -------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Recent recordings"; color: th.muted; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            Text {
                text: recent.length + " file" + (recent.length === 1 ? "" : "s")
                color: th.mutedText
                font.pixelSize: 11
            }
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
                text: "Nothing recorded yet."
                color: th.muted
                font.pixelSize: 12
            }
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 42
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
                    Text { text: modelData.durationText; color: th.muted; font.pixelSize: 11 }
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
                            onClicked: Bridge.deleteRecording(modelData.path)
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
                text: "Super+Shift+Print toggles recording"
                color: th.muted
                font.pixelSize: 11
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "v" + Bridge.version
                color: th.mutedText
                font.pixelSize: 11
            }
        }
    }


    // -- recording HUD ----------------------------------------------------
    // A separate top-level window: the recorder window can be closed, tiled or
    // on another workspace while a recording runs, so the only reliable place
    // for the timer and the stop button is a pinned floating window.
    Window {
        id: hud
        visible: Bridge.recording
        width: Bridge.replayActive ? 300 : 240
        height: 56
        color: "transparent"
        title: "hyprtk-rec HUD"
        // No focus: showing the HUD must not take the keyboard away from the
        // app being recorded.
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
               | Qt.WindowDoesNotAcceptFocus

        Rectangle {
            anchors.fill: parent
            radius: 12
            color: th.panel
            opacity: 0.96
            border.width: 1
            border.color: win.paused ? th.paused : th.record

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Rectangle {
                    Layout.preferredWidth: 10
                    Layout.preferredHeight: 10
                    radius: 5
                    color: win.paused ? th.paused : th.record
                    opacity: win.paused || win.blink ? 1 : 0.35
                }

                Text {
                    text: Bridge.elapsed
                    color: th.foreground
                    font.pixelSize: 15
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    Layout.preferredWidth: 52
                    Layout.preferredHeight: 28
                    radius: 7
                    color: win.paused ? th.accent : th.panelAlt
                    border.width: 1
                    border.color: th.border
                    Text {
                        anchors.centerIn: parent
                        text: win.paused ? "Resume" : "Pause"
                        color: win.paused ? th.textOnAccent : th.foreground
                        font.pixelSize: 10
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.togglePause()
                    }
                }

                Rectangle {
                    visible: Bridge.replayActive
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 28
                    radius: 7
                    color: th.panelAlt
                    border.width: 1
                    border.color: th.border
                    Text {
                        anchors.centerIn: parent
                        text: "Save"
                        color: th.foreground
                        font.pixelSize: 10
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.saveReplay()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 28
                    radius: 7
                    color: th.record
                    Text {
                        anchors.centerIn: parent
                        text: "Stop"
                        color: "#ffffff"
                        font.pixelSize: 10
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.stop()
                    }
                }
            }
        }
    }

    // -- countdown --------------------------------------------------------
    Rectangle {
        anchors.fill: parent
        visible: Bridge.countdown > 0
        color: Qt.rgba(0, 0, 0, 0.55)
        z: 20
        Text {
            anchors.centerIn: parent
            text: Bridge.countdown
            color: "#ffffff"
            font.pixelSize: 120
            font.bold: true
        }
        MouseArea {
            anchors.fill: parent
            onClicked: Bridge.stop()
        }
    }



    // -- settings sheet ---------------------------------------------------
    Rectangle {
        anchors.fill: parent
        visible: win.settingsOpen
        color: Qt.rgba(0, 0, 0, 0.5)
        z: 22

        MouseArea {
            anchors.fill: parent
            onClicked: win.settingsOpen = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 40, 500)
            height: sheet.implicitHeight + 28
            radius: 12
            color: th.panel
            border.width: 1
            border.color: th.border

            ColumnLayout {
                id: sheet
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 14
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Settings"
                        color: th.foreground
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "v" + Bridge.version
                        color: th.mutedText
                        font.pixelSize: 11
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { text: "Save recordings to"; color: th.muted; font.pixelSize: 12 }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Rectangle {
                            Layout.fillWidth: true
                            height: 32
                            radius: 7
                            color: th.panelAlt
                            border.width: 1
                            border.color: dirField.activeFocus ? th.accent2 : th.border
                            TextInput {
                                id: dirField
                                anchors.fill: parent
                                anchors.leftMargin: 9
                                anchors.rightMargin: 9
                                verticalAlignment: TextInput.AlignVCenter
                                color: th.foreground
                                font.pixelSize: 12
                                selectionColor: th.accent
                                selectedTextColor: th.textOnAccent
                                clip: true
                                text: win.dirText
                                onTextChanged: if (win.dirText !== text) win.dirText = text
                                onAccepted: win.commitDir()
                                onActiveFocusChanged: if (!activeFocus) win.commitDir()
                            }
                        }
                        Text {
                            text: "Open"
                            color: th.accent2
                            font.pixelSize: 11
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.openPath(Bridge.config.dir)
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Notifications"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 110 }
                    Segmented {
                        th: win.th
                        current: cfg.notify === true
                        options: [{ v: true, l: "On" }, { v: false, l: "Off" }]
                        onPicked: function (value) { Bridge.setConfig("notify", value); }
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Recent list"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 110 }
                    Segmented {
                        th: win.th
                        current: Number(cfg.recent)
                        options: [{ v: 6, l: "6" }, { v: 12, l: "12" }, { v: 24, l: "24" }]
                        onPicked: function (value) { Bridge.setConfig("recent", value); }
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Encoder backend"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 110 }
                    Segmented {
                        th: win.th
                        current: cfg.backend
                        options: [{ v: "auto", l: "Auto" }, { v: "wf-recorder", l: "wf-recorder" },
                                  { v: "wl-screenrec", l: "wl-screenrec" }]
                        onPicked: function (value) { Bridge.setConfig("backend", value); }
                    }
                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Replay buffer"; color: th.muted; font.pixelSize: 12; Layout.preferredWidth: 110 }
                    Segmented {
                        th: win.th
                        current: Number(cfg.replay)
                        opacity: Bridge.replayAvailable ? 1 : 0.5
                        options: [{ v: 0, l: "Off" }, { v: 15, l: "15s" },
                                  { v: 30, l: "30s" }, { v: 60, l: "60s" }]
                        onPicked: function (value) {
                            if (value && !Bridge.replayAvailable) return;
                            Bridge.setConfig("replay", value);
                        }
                    }
                    Item { Layout.fillWidth: true }
                }

                Text {
                    Layout.fillWidth: true
                    visible: !Bridge.replayAvailable || Number(cfg.replay) > 0
                    text: Bridge.replayAvailable
                          ? "Save flushes the last " + cfg.replay + " s and keeps recording"
                          : "needs wl-screenrec, which is not installed"
                    color: Bridge.replayAvailable ? th.mutedText : th.danger
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: "Installed: " + (Bridge.backends.length ? Bridge.backends.join(", ") : "none") +
                          " · wl-screenrec is used automatically when present"
                    color: th.mutedText
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Rectangle {
                        width: 96
                        height: 30
                        radius: 8
                        color: th.panelAlt
                        border.width: 1
                        border.color: th.border
                        Text {
                            anchors.centerIn: parent
                            text: "Reset"
                            color: th.danger
                            font.pixelSize: 11
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { Bridge.resetDefaults(); win.dirText = Bridge.config.dir; }
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        width: 76
                        height: 30
                        radius: 8
                        color: th.accent
                        Text {
                            anchors.centerIn: parent
                            text: "Done"
                            color: th.textOnAccent
                            font.pixelSize: 11
                            font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: win.settingsOpen = false
                        }
                    }
                }
            }
        }
    }

    // -- window picker ----------------------------------------------------
    Rectangle {
        id: picker
        anchors.fill: parent
        visible: win.picking
        color: Qt.rgba(0, 0, 0, 0.5)
        z: 25

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
                        text: "Record a window"
                        color: th.foreground
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Bridge.windows.length + " open"
                        color: th.mutedText
                        font.pixelSize: 11
                    }
                    Text {
                        text: "Focused"
                        color: th.accent2
                        font.pixelSize: 11
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { Bridge.pickWindow(""); win.picking = false; }
                        }
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
                            onClicked: { Bridge.pickWindow(modelData.address); win.picking = false; }
                        }
                    }
                }
            }
        }
    }

    // -- toast ------------------------------------------------------------
    Rectangle {
        id: toast
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 16
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 36, toastText.implicitWidth + 28)
        height: toastText.implicitHeight + 18
        radius: 9
        color: th.panel
        border.width: 1
        border.color: th.accent2
        opacity: 0
        visible: opacity > 0

        function show(title, body) {
            toastTitle.text = title;
            toastText.text = body;
            toast.opacity = 1;
            hideTimer.restart();
        }

        Column {
            anchors.centerIn: parent
            spacing: 2
            Text {
                id: toastTitle
                anchors.horizontalCenter: parent.horizontalCenter
                color: th.foreground
                font.pixelSize: 12
                font.bold: true
            }
            Text {
                id: toastText
                anchors.horizontalCenter: parent.horizontalCenter
                color: th.muted
                font.pixelSize: 11
                elide: Text.ElideMiddle
                width: toast.width - 24
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Timer {
            id: hideTimer
            interval: 3200
            onTriggered: toast.opacity = 0
        }
        Behavior on opacity { NumberAnimation { duration: 180 } }
    }

    Shortcut { sequence: "Ctrl+R"; onActivated: Bridge.toggle() }
    Shortcut { sequence: "Space"; onActivated: Bridge.togglePause() }
    Shortcut { sequence: "Escape"; onActivated: Bridge.quit() }
}
