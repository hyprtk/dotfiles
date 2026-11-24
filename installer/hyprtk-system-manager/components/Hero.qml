// Compact page hero in the bar's dialog language: an accent glyph, a dim
// eyebrow, a bold foreground title, dim subtitle and chip pills. No big tile.
import QtQuick
import "../theme"

Item {
    id: hero
    property string glyph: "\uf05a"
    property string eyebrow: ""
    property string title: ""
    property string subtitle: ""
    property var chips: []

    width: parent ? parent.width : 0
    implicitHeight: layout.implicitHeight + 6

    Row {
        id: layout
        width: parent.width
        spacing: 12

        Glyph {
            glyph: hero.glyph
            pixelSize: 22
            color: Theme.accent
            anchors.top: parent.top
            anchors.topMargin: 2
        }

        Column {
            width: parent.width - 34
            spacing: 2

            Text {
                visible: hero.eyebrow.length > 0
                text: hero.eyebrow
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(0)
                font.weight: Font.DemiBold
            }
            Text {
                width: parent.width
                text: hero.title
                color: Theme.foreground
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(4)
                font.bold: true
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                visible: hero.subtitle.length > 0
                text: hero.subtitle
                color: Theme.dim
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(1)
                elide: Text.ElideRight
            }
            Row {
                spacing: 6
                topPadding: 4
                Repeater {
                    model: hero.chips
                    delegate: StatusPill {
                        required property var modelData
                        text: typeof modelData === "string" ? modelData : (modelData.label || "")
                        tone: "accent2"
                    }
                }
            }
        }
    }
}
