import QtQuick
import QtQuick.Layouts
import "../theme/util.js" as Util
import "."

Rectangle {
    id: root

    property string title: "Are you sure?"
    property string message: ""
    property string detail: ""
    property string acceptText: "OK"
    property string cancelText: "Cancel"
    property bool danger: false
    property bool showCancel: true
    signal accepted()
    signal cancelled()

    readonly property var th: Bridge.palette

    anchors.fill: parent
    z: 600
    visible: false
    color: Util.alpha(root.th.background, 0.55)

    function open() { root.visible = true; }
    function close() { root.visible = false; }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (root.showCancel) {
                root.close();
                root.cancelled();
            }
        }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(440, root.width - 60)
        height: content.implicitHeight + 40
        radius: 10
        color: root.th.surface
        border.width: 1
        border.color: Util.alpha(root.th.border, 0.9)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Text {
                text: root.title
                color: root.th.foreground
                font.pixelSize: 15
                font.weight: 600
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Text {
                visible: root.message.length > 0
                text: root.message
                color: Util.alpha(root.th.foreground, 0.9)
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Text {
                visible: root.detail.length > 0
                text: root.detail
                color: root.th.muted
                font.pixelSize: 11
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                spacing: 8
                Item { Layout.fillWidth: true }
                FlatButton {
                    visible: root.showCancel
                    text: root.cancelText
                    onClicked: { root.close(); root.cancelled(); }
                }
                FlatButton {
                    text: root.acceptText
                    active: true
                    danger: root.danger
                    onClicked: { root.close(); root.accepted(); }
                }
            }
        }
    }
}
