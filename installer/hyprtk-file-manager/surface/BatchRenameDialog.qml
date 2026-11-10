import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 225

    property var paths: []
    property string findText: ""
    property string replaceText: ""
    property string prefix: ""
    property string suffix: ""
    property bool numbering: false
    property int start: 1
    property int step: 1
    property int padding: 3
    property string caseMode: "keep"

    signal accepted(var renames)
    signal cancelled()

    function open(list) {
        root.paths = list.slice();
        root.findText = "";
        root.replaceText = "";
        root.prefix = "";
        root.suffix = "";
        root.numbering = false;
        root.start = 1;
        root.step = 1;
        root.padding = 3;
        root.caseMode = "keep";
        root.visible = true;
        Qt.callLater(function () { findField.input.forceActiveFocus(); });
    }

    function close() {
        root.visible = false;
    }

    function cancel() {
        root.visible = false;
        root.cancelled();
    }

    function baseName(path) {
        return path.slice(path.lastIndexOf("/") + 1);
    }

    function splitExt(name) {
        const dot = name.lastIndexOf(".");
        return dot > 0 ? [name.slice(0, dot), name.slice(dot)] : [name, ""];
    }

    function pad(value, width) {
        let text = String(value);
        while (text.length < width)
            text = "0" + text;
        return text;
    }

    function newName(path, index) {
        const parts = root.splitExt(root.baseName(path));
        let stem = parts[0];
        const ext = parts[1];
        if (root.findText.length > 0)
            stem = stem.split(root.findText).join(root.replaceText);
        stem = root.prefix + stem + root.suffix;
        if (root.numbering) {
            const number = root.start + index * root.step;
            stem += root.pad(number, Math.max(1, root.padding));
        }
        if (root.caseMode === "lower")
            stem = stem.toLowerCase();
        else if (root.caseMode === "upper")
            stem = stem.toUpperCase();
        return stem + ext;
    }

    function plan() {
        const out = [];
        for (let i = 0; i < root.paths.length; i++)
            out.push({ path: root.paths[i], name: root.newName(root.paths[i], i) });
        return out;
    }

    function valid() {
        const items = root.plan();
        if (items.length === 0)
            return false;
        for (let i = 0; i < items.length; i++) {
            const name = items[i].name;
            if (!name || name === "." || name === ".." || name.indexOf("/") >= 0)
                return false;
        }
        return true;
    }

    function apply() {
        if (!root.valid())
            return;
        root.visible = false;
        root.accepted(root.plan());
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(720, root.width - 80)
        height: 560
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Text {
                text: "Batch rename " + root.paths.length + " item(s)"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Row {
                spacing: 12

                LabeledField {
                    id: findField
                    width: 260
                    label: "Find"
                    placeholder: "text to replace"
                    onTextChanged: root.findText = text
                    onAccepted: root.apply()
                }

                LabeledField {
                    width: 260
                    label: "Replace"
                    placeholder: "replacement"
                    onTextChanged: root.replaceText = text
                    onAccepted: root.apply()
                }
            }

            Row {
                spacing: 12

                LabeledField {
                    width: 260
                    label: "Prefix"
                    placeholder: ""
                    onTextChanged: root.prefix = text
                    onAccepted: root.apply()
                }

                LabeledField {
                    width: 260
                    label: "Suffix"
                    placeholder: ""
                    onTextChanged: root.suffix = text
                    onAccepted: root.apply()
                }
            }

            Row {
                spacing: 12

                Rectangle {
                    width: 120
                    height: 30
                    radius: 6
                    color: root.numbering ? Theme.alpha(Theme.accent, 0.32) : Theme.alpha(Theme.foreground, 0.06)

                    Text {
                        anchors.centerIn: parent
                        text: "Numbering"
                        color: Theme.foreground
                        font.pixelSize: 11
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.numbering = !root.numbering
                    }
                }

                LabeledField {
                    width: 90
                    label: "Start"
                    placeholder: "1"
                    text: "1"
                    onTextChanged: root.start = parseInt(text) || 1
                    onAccepted: root.apply()
                }

                LabeledField {
                    width: 90
                    label: "Step"
                    placeholder: "1"
                    text: "1"
                    onTextChanged: root.step = parseInt(text) || 1
                    onAccepted: root.apply()
                }

                LabeledField {
                    width: 90
                    label: "Padding"
                    placeholder: "3"
                    text: "3"
                    onTextChanged: root.padding = parseInt(text) || 3
                    onAccepted: root.apply()
                }

                Column {
                    spacing: 4

                    Text {
                        text: "Case"
                        color: Theme.muted
                        font.pixelSize: 10
                    }

                    Row {
                        spacing: 6

                        Repeater {
                            model: [
                                { label: "Keep", value: "keep" },
                                { label: "lower", value: "lower" },
                                { label: "UPPER", value: "upper" }
                            ]

                            delegate: Rectangle {
                                required property var modelData
                                width: 62
                                height: 30
                                radius: 6
                                color: root.caseMode === modelData.value
                                    ? Theme.alpha(Theme.accent, 0.32)
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
                                    onClicked: root.caseMode = modelData.value
                                }
                            }
                        }
                    }
                }
            }

            Text {
                text: "Preview"
                color: Theme.muted
                font.pixelSize: 10
            }

            ListView {
                width: parent.width
                height: 170
                clip: true
                model: root.paths

                delegate: Row {
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    height: 20
                    spacing: 6

                    Text {
                        width: parent.width * 0.44
                        text: root.baseName(modelData)
                        color: Theme.muted
                        font.pixelSize: 10
                        elide: Text.ElideMiddle
                    }

                    Text {
                        width: 16
                        text: "→"
                        color: Theme.alpha(Theme.foreground, 0.4)
                        font.pixelSize: 10
                    }

                    Text {
                        width: parent.width * 0.44
                        text: root.newName(modelData, index)
                        color: Theme.foreground
                        font.pixelSize: 10
                        elide: Text.ElideMiddle
                    }
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Cancel"
                    onClicked: root.cancel()
                }

                DialogButton {
                    text: "Rename"
                    primary: true
                    onClicked: root.apply()
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.cancel()
    }
}
