import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme/util.js" as Util
import "."

Rectangle {
    id: root

    property string title: ""
    property string label: ""
    property string placeholder: ""
    property string text: ""
    property string acceptText: "OK"
    signal accepted(string text)
    signal cancelled()

    readonly property var th: Bridge.palette

    anchors.fill: parent
    z: 610
    visible: false
    color: Util.alpha(root.th.background, 0.55)

    function open() {
        root.visible = true;
        field.text = root.text;
        field.forceActiveFocus();
        field.selectAll();
    }

    function close() {
        root.visible = false;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: { root.close(); root.cancelled(); }
    }

    Rectangle {
        width: Math.min(380, root.width - 80)
        height: content.implicitHeight + 40
        anchors.centerIn: parent
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
            }

            Text {
                visible: root.label.length > 0
                text: root.label
                color: root.th.muted
                font.pixelSize: 11
                Layout.fillWidth: true
            }

            TextField {
                id: field
                Layout.fillWidth: true
                height: 30
                color: root.th.foreground
                selectionColor: Util.alpha(root.th.accent, 0.4)
                selectedTextColor: root.th.foreground
                font.pixelSize: 12
                placeholderText: root.placeholder
                placeholderTextColor: Util.alpha(root.th.muted, 0.7)
                background: Rectangle {
                    radius: 6
                    color: Util.alpha(root.th.background, 0.8)
                    border.width: 1
                    border.color: Util.alpha(root.th.accent, 0.5)
                }
                onAccepted: { root.close(); root.accepted(field.text); }
                Keys.onPressed: function (event) {
                    if (event.key === Qt.Key_Escape) {
                        root.close();
                        root.cancelled();
                        event.accepted = true;
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Item { Layout.fillWidth: true }
                FlatButton { text: "Cancel"; onClicked: { root.close(); root.cancelled(); } }
                FlatButton { text: root.acceptText; active: true; onClicked: { root.close(); root.accepted(field.text); } }
            }
        }
    }
}
