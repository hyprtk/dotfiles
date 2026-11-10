import QtQuick
import Quickshell
import "../theme"
import "../config"
import "../data"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 210

    property string rootDir: ""
    property string mode: "name"
    property var results: []
    property int pendingId: -1
    property bool truncated: false
    property int cursor: 0

    signal activated(var entry)

    function open(dir) {
        root.rootDir = dir || Config.startPath;
        root.mode = "name";
        root.results = [];
        root.truncated = false;
        root.cursor = 0;
        root.visible = true;
        Ui.modalOpen = true;
        field.text = "";
        Qt.callLater(function () { field.forceActiveFocus(); });
    }

    function close() {
        root.visible = false;
        Ui.modalOpen = false;
        root.pendingId = -1;
    }

    function run() {
        const value = field.text.trim();
        if (value.length < 2) {
            root.results = [];
            root.truncated = false;
            return;
        }
        root.pendingId = Backend.call("search", {
            root: root.rootDir,
            query: value,
            mode: root.mode,
            hidden: Config.showHidden,
            limit: 500
        });
    }

    function move(delta) {
        if (root.results.length === 0)
            return;
        root.cursor = (root.cursor + delta + root.results.length) % root.results.length;
        resultList.positionViewAtIndex(root.cursor, ListView.Contain);
    }

    function activate() {
        const entry = root.results[root.cursor];
        if (!entry)
            return;
        root.close();
        root.activated(entry);
    }

    Timer {
        id: debounce
        interval: 350
        repeat: false
        onTriggered: root.run()
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            if (result && result.kind === "search") {
                root.results = result.results;
                root.truncated = result.truncated;
                root.cursor = 0;
            }
        }
        function onFailure(id, message) {
            if (id !== root.pendingId)
                return;
            root.pendingId = -1;
            root.results = [];
            root.truncated = false;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(780, root.width - 80)
        height: Math.min(640, root.height - 80)
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            Row {
                width: parent.width
                spacing: 8

                Rectangle {
                    width: parent.width - 190
                    height: 34
                    radius: 6
                    color: Theme.alpha(Theme.foreground, 0.06)
                    border.width: 1
                    border.color: Theme.accent

                    TextInput {
                        id: field
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: TextInput.AlignVCenter
                        color: Theme.foreground
                        selectionColor: Theme.accent
                        selectedTextColor: Theme.textOnAccent
                        font.pixelSize: 13
                        onTextChanged: if (root.visible) debounce.restart()
                        onAccepted: root.activate()
                        Keys.onUpPressed: root.move(-1)
                        Keys.onDownPressed: root.move(1)
                        Keys.onEscapePressed: root.close()
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        visible: field.text.length === 0
                        text: "Search name or content…"
                        color: Theme.alpha(Theme.foreground, 0.35)
                        font.pixelSize: 13
                    }
                }

                Repeater {
                    model: [
                        { label: "Name", value: "name" },
                        { label: "Content", value: "content" }
                    ]

                    delegate: Rectangle {
                        required property var modelData
                        width: 82
                        height: 34
                        radius: 6
                        color: root.mode === modelData.value
                            ? Theme.alpha(Theme.accent, 0.3)
                            : Theme.alpha(Theme.foreground, 0.06)

                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            color: Theme.foreground
                            font.pixelSize: 11
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.mode = modelData.value;
                                root.run();
                            }
                        }
                    }
                }
            }

            Text {
                width: parent.width
                text: "in " + root.rootDir
                color: Theme.muted
                font.pixelSize: 10
                elide: Text.ElideMiddle
            }

            ListView {
                id: resultList
                width: parent.width
                height: parent.height - 120
                clip: true
                model: root.results
                currentIndex: root.cursor
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: resultList.width
                    height: modelData.line ? 46 : 36
                    radius: 6
                    color: index === root.cursor ? Theme.alpha(Theme.accent, 0.2) : "transparent"

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        Image {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 16
                            height: 16
                            sourceSize: Qt.size(16, 16)
                            source: Quickshell.iconPath(modelData.icon, "text-x-generic")
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 28
                            spacing: 1

                            Text {
                                width: parent.width
                                text: modelData.name
                                color: Theme.foreground
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                            }

                            Text {
                                width: parent.width
                                text: modelData.path + (modelData.lineno ? ":" + modelData.lineno : "")
                                color: Theme.muted
                                font.pixelSize: 9
                                elide: Text.ElideMiddle
                            }

                            Text {
                                width: parent.width
                                visible: !!modelData.line
                                text: modelData.line || ""
                                color: Theme.accent2
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.cursor = index
                        onDoubleClicked: {
                            root.cursor = index;
                            root.activate();
                        }
                    }
                }
            }

            Text {
                width: parent.width
                text: root.results.length + (root.truncated ? "+" : "") + " results"
                    + "     ↑↓ navigate · Enter open · Esc close"
                color: Theme.muted
                font.pixelSize: 10
            }
        }
    }

    Shortcut {
        sequence: "Ctrl+1"
        enabled: root.visible
        onActivated: {
            root.mode = "name";
            root.run();
        }
    }

    Shortcut {
        sequence: "Ctrl+2"
        enabled: root.visible
        onActivated: {
            root.mode = "content";
            root.run();
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.close()
    }
}
