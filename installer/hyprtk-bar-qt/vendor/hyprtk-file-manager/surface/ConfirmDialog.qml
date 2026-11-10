import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string message: ""
    property string confirmText: "Delete"

    signal confirmed()
    signal cancelled()

    anchors.fill: parent
    visible: false
    z: 220

    function open(titleText, messageText, confirmLabel) {
        root.title = titleText;
        root.message = messageText;
        root.confirmText = confirmLabel || "Delete";
        root.visible = true;
    }

    function close() {
        root.visible = false;
    }

    function dismiss() {
        root.visible = false;
        if (root.parent)
            root.parent.forceActiveFocus();
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
        height: 186
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text {
                text: root.title
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: root.message
                color: Theme.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
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
                    text: root.confirmText
                    danger: true
                    onClicked: {
                        root.dismiss();
                        root.confirmed();
                    }
                }
            }
        }
    }

    Shortcut {
        sequence: "Return"
        enabled: root.visible
        onActivated: {
            root.dismiss();
            root.confirmed();
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
