import QtQuick
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 215

    property var commands: []
    property var filtered: []
    property int cursor: 0

    function fuzzy(text, query) {
        const haystack = (text || "").toLowerCase();
        const needle = (query || "").toLowerCase();
        let hi = 0;
        let ni = 0;
        while (hi < haystack.length && ni < needle.length) {
            if (haystack[hi] === needle[ni])
                ni += 1;
            hi += 1;
        }
        return ni === needle.length;
    }

    function open(list) {
        root.commands = list;
        root.filtered = list;
        root.cursor = 0;
        root.visible = true;
        Ui.modalOpen = true;
        field.text = "";
        Qt.callLater(function () { field.forceActiveFocus(); });
    }

    function close() {
        root.visible = false;
        Ui.modalOpen = false;
    }

    function refilter() {
        const query = field.text.trim();
        if (!query) {
            root.filtered = root.commands;
        } else {
            root.filtered = root.commands.filter(function (command) {
                return root.fuzzy(command.label, query);
            });
        }
        root.cursor = 0;
    }

    function move(delta) {
        if (root.filtered.length === 0)
            return;
        root.cursor = (root.cursor + delta + root.filtered.length) % root.filtered.length;
        commandList.positionViewAtIndex(root.cursor, ListView.Contain);
    }

    function run() {
        const command = root.filtered[root.cursor];
        if (!command)
            return;
        root.close();
        if (command.action)
            command.action();
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(580, root.width - 80)
        height: Math.min(460, root.height - 80)
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            Rectangle {
                width: parent.width
                height: 36
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
                    onTextChanged: root.refilter()
                    onAccepted: root.run()
                    Keys.onUpPressed: root.move(-1)
                    Keys.onDownPressed: root.move(1)
                    Keys.onEscapePressed: root.close()
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    visible: field.text.length === 0
                    text: "Run a command…"
                    color: Theme.alpha(Theme.foreground, 0.35)
                    font.pixelSize: 13
                }
            }

            ListView {
                id: commandList
                width: parent.width
                height: parent.height - 84
                clip: true
                model: root.filtered
                currentIndex: root.cursor
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: commandList.width
                    height: 32
                    radius: 6
                    color: index === root.cursor ? Theme.alpha(Theme.accent, 0.22) : "transparent"

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: Theme.foreground
                        font.pixelSize: 12
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            root.cursor = index;
                            root.run();
                        }
                    }
                }
            }

            Text {
                width: parent.width
                text: "↑↓ navigate · Enter run · Esc close"
                color: Theme.muted
                font.pixelSize: 10
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.close()
    }
}
