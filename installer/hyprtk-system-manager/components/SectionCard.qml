// Section card in the bar-qt module-card language: radius 8, background at 42%,
// accent2 border at 15%, accent section title, dim description.
import QtQuick
import "../theme"

Rectangle {
    id: card

    property string title: ""
    property string description: ""
    default property alias body: rows.data

    width: parent ? parent.width : 0
    implicitHeight: column.implicitHeight + 16
    radius: Theme.radiusCard
    color: Theme.cardFill
    border.width: 1
    border.color: Theme.cardBorder

    Column {
        id: column
        width: parent.width - 16
        x: 8
        y: 8
        spacing: 6

        Text {
            visible: card.title.length > 0
            width: parent.width
            text: card.title
            color: Theme.accent
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(2)
            font.bold: true
        }
        Text {
            visible: card.description.length > 0
            width: parent.width
            text: card.description
            color: Theme.dim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(0)
            wrapMode: Text.WordWrap
            lineHeight: 1.25
        }
        Column {
            id: rows
            width: parent.width
            spacing: 2
        }
    }
}
