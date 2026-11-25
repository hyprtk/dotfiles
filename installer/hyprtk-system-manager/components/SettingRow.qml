// One settings row in the bar-qt rhythm: a fixed-width label column, then the
// control immediately to its right (not pushed to the far edge), 8px apart.
import QtQuick
import "../theme"

Item {
    id: row

    property string label: ""
    property string help: ""
    property string value: ""
    property bool mono: false
    property bool copyValue: false
    property int labelWidth: 180
    property bool highlighted: false
    default property alias control: controlRow.data

    width: parent ? parent.width : 0
    implicitHeight: Math.max(leftColumn.implicitHeight, host.implicitHeight, Theme.controlHeight) + 4

    Rectangle {
        anchors.fill: parent
        anchors.margins: -6
        radius: Theme.radiusSm
        visible: row.highlighted
        color: Theme.alpha(Theme.accent2, 0.10)
        border.width: 1
        border.color: Theme.alpha(Theme.accent2, 0.45)
    }

    Column {
        id: leftColumn
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: row.labelWidth
        spacing: 2

        Text {
            width: parent.width
            text: row.label
            color: Theme.foreground
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(2)
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            visible: row.help.length > 0
            text: row.help
            color: Theme.dim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(0)
            wrapMode: Text.WordWrap
            lineHeight: 1.2
        }
    }

    Row {
        id: host
        anchors.left: leftColumn.right
        anchors.leftMargin: 8
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        Text {
            id: valueText
            visible: row.value.length > 0
            anchors.verticalCenter: parent.verticalCenter
            text: row.value
            color: Theme.foreground
            font.family: row.mono ? Theme.monoFamily : Theme.fontFamily
            font.pixelSize: row.mono ? Theme.size(1) : Theme.size(2)
            elide: Text.ElideMiddle
            width: Math.min(implicitWidth, row.width - row.labelWidth - 16)
        }
        Row { id: controlRow; spacing: 8; anchors.verticalCenter: parent.verticalCenter }

        Rectangle {
            visible: row.copyValue && row.value.length > 0
            width: 22
            height: 22
            radius: 6
            color: copyHover.hovered ? Theme.hoverTint : "transparent"
            anchors.verticalCenter: parent.verticalCenter
            Glyph { anchors.centerIn: parent; glyph: "\uf0c5"; pixelSize: Theme.size(0); color: Theme.dim }
            HoverHandler { id: copyHover }
            TapHandler {
                onTapped: {
                    clipboard.text = row.value;
                    clipboard.selectAll();
                    clipboard.copy();
                }
            }
        }
    }

    TextInput {
        id: clipboard
        visible: false
        width: 1; height: 1
    }
}
