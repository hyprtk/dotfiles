// Plain read-only text panel (share URL, model description, mount list).
import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string text: ""

    signal closed()

    anchors.fill: parent
    visible: false
    z: 244
    focus: visible

    function show(titleText, body) {
        root.title = titleText;
        root.text = body;
        root.visible = true;
        Qt.callLater(function () { closeButton.forceActiveFocus(); });
    }

    function dismiss() {
        root.visible = false;
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45
        MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(680, parent.width - 80)
        height: Math.min(460, parent.height - 80)
        radius: Theme.radiusLg
        color: Theme.background
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.35)

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            Text {
                width: parent.width
                text: root.title
                color: Theme.accent
                font.pixelSize: Theme.size(4)
                font.bold: true
                elide: Text.ElideMiddle
            }

            Rectangle {
                width: parent.width
                height: parent.height - 92
                radius: 6
                color: Theme.alpha(Theme.background, 0.6)
                border.width: 1
                border.color: Theme.alpha(Theme.foreground, 0.10)
                clip: true

                Flickable {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    contentWidth: body.implicitWidth
                    contentHeight: body.implicitHeight

                    Text {
                        id: body
                        text: root.text
                        color: Theme.foreground
                        font.pixelSize: Theme.size(2)
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        width: Math.min(parent.width, 620)
                    }
                }
            }

            DialogButton {
                id: closeButton
                text: "Close"
                onClicked: root.dismiss()
            }
        }
    }

    Keys.onEscapePressed: root.dismiss()
}
