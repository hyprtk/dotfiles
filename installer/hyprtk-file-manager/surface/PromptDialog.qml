import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string label: ""
    property string initial: ""
    property string placeholder: ""

    signal accepted(string value)
    signal cancelled()

    anchors.fill: parent
    visible: false
    z: 220
    focus: visible

    function open(titleText, labelText, initialText) {
        root.title = titleText;
        root.label = labelText;
        root.initial = initialText;
        root.visible = true;
        field.text = initialText;
        Qt.callLater(function () {
            field.forceActiveFocus();
            field.selectAll();
        });
    }

    function close() {
        root.visible = false;
    }

    function dismiss() {
        field.focus = false;
        root.focus = false;
        root.visible = false;
        if (root.parent)
            root.parent.forceActiveFocus();
    }

    function submit() {
        const value = field.text.trim();
        if (!value)
            return;
        root.dismiss();
        root.accepted(value);
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 430
        height: 196
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Text {
                text: root.title
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                text: root.label
                color: Theme.muted
                font.pixelSize: 11
            }

            Rectangle {
                width: parent.width
                height: 32
                radius: 6
                color: Theme.alpha(Theme.foreground, 0.06)
                border.width: 1
                border.color: Theme.accent

                TextInput {
                    id: field
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.foreground
                    selectionColor: Theme.accent
                    selectedTextColor: Theme.textOnAccent
                    font.pixelSize: 12
                    onAccepted: root.submit()
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Cancel"
                    onClicked: {
                        root.dismiss();
                        root.cancelled();
                    }
                }

                DialogButton {
                    text: "OK"
                    primary: true
                    onClicked: root.submit()
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: {
            root.dismiss();
            root.cancelled();
        }
    }
}
