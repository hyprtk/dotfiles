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
        if (cfg.source === "window") return "Focused window";
        var rows = Bridge.monitors;
        for (var i = 0; i < rows.length; i++)
            if (rows[i].focused) return rows[i].name;
        return rows.length > 0 ? rows[0].name : "Monitor";
    }
    readonly property string summary: sourceLabel + " · " + cfg.fps + " fps · "
        + String(cfg.codec).toUpperCase() + " · "
        + (cfg.audio === "none" ? "no audio" : (cfg.audio === "mic" ? "microphone" : "system audio"))

    property bool blink: true

    visible: true
    width: 560
    height: 720
    minimumWidth: 500
    minimumHeight: 600
    color: th.background
    title: rec ? "Recording" : "Screen Recorder"
    flags: Qt.Window

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
                                  { v: "mic", l: "Mic" }]
                        onPicked: function (value) { Bridge.setConfig("audio", value); }
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: cfg.audio === "mic" ? "SIGSTOP-safe · default input" : ""
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
