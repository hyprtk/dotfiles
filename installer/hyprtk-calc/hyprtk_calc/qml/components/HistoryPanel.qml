import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../theme"
import "../theme/util.js" as Util

// The history drawer. Rows come from Bridge.historyRows, which is a notify
// property, so a new entry appears without any imperative refresh.
Rectangle {
    id: panel

    property var th: null
    property var rows: []
    property real fontScale: 1.0

    signal recall(int index)
    signal clearRequested()
    signal closed()

    radius: 14
    color: panel.th ? panel.th.display : "#12141e"
    border.width: 1
    border.color: Util.alpha(panel.th ? panel.th.foreground : "#ffffff", 0.09)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: "History"
                font.pixelSize: 13 * panel.fontScale
                font.weight: Font.DemiBold
                color: panel.th ? panel.th.foreground : "#e5e7eb"
                Layout.fillWidth: true
            }

            IconButton {
                th: panel.th
                glyph: Glyph.trash
                visible: panel.rows.length > 0
                onClicked: panel.clearRequested()
            }

            IconButton {
                th: panel.th
                glyph: Glyph.close
                onClicked: panel.closed()
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: panel.rows
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: rowItem

                required property var modelData
                required property int index

                width: list.width
                height: 46
                radius: 8
                color: hover.containsMouse
                       ? Util.alpha(panel.th ? panel.th.foreground : "#ffffff", 0.07)
                       : "transparent"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 1

                    Text {
                        Layout.fillWidth: true
                        text: rowItem.modelData.expression
                        elide: Text.ElideLeft
                        font.family: panel.th && panel.th.mono ? panel.th.mono : "monospace"
                        font.pixelSize: 11 * panel.fontScale
                        color: panel.th ? panel.th.muted : "#a6adc8"
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "= " + rowItem.modelData.result
                        elide: Text.ElideLeft
                        font.family: panel.th && panel.th.mono ? panel.th.mono : "monospace"
                        font.pixelSize: 13 * panel.fontScale
                        font.weight: Font.DemiBold
                        color: panel.th ? panel.th.foreground : "#e5e7eb"
                    }
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: panel.recall(rowItem.index)
                }
            }

            Text {
                anchors.centerIn: parent
                width: parent.width - 20
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: panel.rows.length === 0
                text: "Nothing yet. Press Enter after a calculation."
                font.pixelSize: 11.5 * panel.fontScale
                color: panel.th ? panel.th.dim : "#6e7075"
            }
        }
    }
}
