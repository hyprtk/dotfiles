import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "theme/util.js" as Util
import "components"

Rectangle {
    id: root

    readonly property var th: Bridge.palette
    readonly property var recent: Bridge.recent
    readonly property var drafts: Bridge.drafts

    signal newRequested()
    signal openRequested()
    signal openPath(string path)
    signal recoverRequested()

    color: root.th.background

    ColumnLayout {
        width: Math.min(620, root.width - 120)
        anchors.centerIn: parent
        spacing: 14

        Text {
            Layout.fillWidth: true
            text: "hyprtk-editor"
            color: root.th.accent
            font.pixelSize: 30
            font.weight: 700
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            Layout.fillWidth: true
            text: "A fast, theme-aware text editor. Notepad-simple, Kate-capable."
            color: root.th.muted
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 6
            spacing: 10
            FlatButton { text: "New file   Ctrl+N"; active: true; onClicked: root.newRequested() }
            FlatButton { text: "Open file   Ctrl+O"; onClicked: root.openRequested() }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 12
            height: 1
            color: Util.alpha(root.th.border, 0.6)
        }

        Text {
            Layout.fillWidth: true
            visible: root.drafts.length > 0
            text: root.drafts.length + " unsaved document(s) can be recovered"
            color: root.th.warning
            font.pixelSize: 12
        }

        FlatButton {
            visible: root.drafts.length > 0
            text: "Recover unsaved work"
            onClicked: root.recoverRequested()
        }

        Text {
            Layout.fillWidth: true
            text: "Recent"
            color: root.th.muted
            font.pixelSize: 11
            font.weight: 600
        }

        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(260, Math.max(0, root.recent.length) * 40)
            visible: root.recent.length > 0
            model: root.recent
            clip: true
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                width: ListView.view.width
                height: 38
                radius: 6
                color: rowMouse.containsMouse ? Util.alpha(root.th.surfaceAlt, 0.6) : "transparent"

                Text {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 8
                    text: modelData.name
                    color: root.th.foreground
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(300, parent.width * 0.55)
                    text: modelData.folder
                    color: Util.alpha(root.th.muted, 0.75)
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                    horizontalAlignment: Text.AlignRight
                }
                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.openPath(modelData.path)
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.recent.length === 0
            text: "No recent files yet. Drop a file here, or press Ctrl+O."
            color: Util.alpha(root.th.muted, 0.8)
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
        }

        Item { Layout.fillHeight: true }
    }
}
