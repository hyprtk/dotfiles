// A Nerd Font icon. The suite ships the Symbols font, so glyphs are the
// consistent icon language across the bar, file manager and this app.
import QtQuick
import "../theme"

Text {
    id: root
    property string glyph: ""
    property int pixelSize: Theme.size(2)
    property bool dim: false

    text: root.glyph
    color: root.dim ? Theme.dim : Theme.text
    font.family: Theme.iconFont
    font.pixelSize: root.pixelSize
    verticalAlignment: Text.AlignVCenter
    horizontalAlignment: Text.AlignHCenter
    renderType: Text.QtRendering
}
