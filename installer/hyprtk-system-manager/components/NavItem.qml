// Sidebar item matching the bar's Settings nav: 32px tall, radius 8, selected
// item is the accent fill with black text, hover is accent2 at 15%.
import QtQuick
import "../theme"

Rectangle {
    id: item
    property string glyph: ""
    property string label: ""
    property bool active: false
    signal clicked()

    width: parent ? parent.width : 0
    height: 32
    radius: Theme.radiusCard
    color: item.active
        ? Theme.alpha(Theme.accent, 0.85)
        : (hover.hovered ? Theme.hoverTint : "transparent")

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 9

        Glyph {
            glyph: item.glyph
            pixelSize: Theme.size(2)
            color: item.active ? Theme.textOnAccent : Theme.foreground
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            width: parent.width - 26
            text: item.label
            color: item.active ? Theme.textOnAccent : Theme.foreground
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(2)
            font.weight: item.active ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: item.clicked() }
}
