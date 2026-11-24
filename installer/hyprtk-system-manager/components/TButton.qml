// Push button matching hyprtk-bar-qt/components/TButton: 30px tall, radius 8,
// accent2-tinted fill with an accent2 border. Primary reuses the bar's
// selected-item accent fill with black text; danger uses the error colour.
import QtQuick
import "../theme"

Rectangle {
    id: btn

    property string text: ""
    property string glyph: ""
    property bool primary: false
    property bool danger: false
    property bool ghost: false
    property bool small: false
    signal clicked()

    readonly property int height30: small ? 26 : Theme.controlHeight

    implicitWidth: Math.max(small ? 46 : 64, content.implicitWidth + (small ? 18 : 24))
    implicitHeight: height30
    radius: 8
    opacity: enabled ? 1 : 0.55

    color: !enabled ? Theme.alpha(Theme.dim, 0.08)
         : danger ? (hover.hovered ? Qt.lighter(Theme.danger, 1.10) : Theme.danger)
         : primary ? (hover.hovered ? Qt.lighter(Theme.accent, 1.12) : Theme.accent)
         : ghost ? (hover.hovered ? Theme.hoverTint : "transparent")
         : tap.pressed ? Theme.pressTint
         : hover.hovered ? Theme.buttonHover
         : Theme.buttonFill
    border.width: (primary || danger) ? 0 : 1
    border.color: Theme.buttonBorder

    Row {
        id: content
        anchors.centerIn: parent
        spacing: 6
        Glyph {
            visible: btn.glyph.length > 0
            glyph: btn.glyph
            pixelSize: btn.small ? Theme.size(0) : Theme.size(2)
            color: btn.primary ? Theme.textOnAccent
                 : btn.danger ? Theme.textOnDanger
                 : btn.enabled ? Theme.foreground : Theme.dim
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: btn.text
            color: btn.primary ? Theme.textOnAccent
                 : btn.danger ? Theme.textOnDanger
                 : btn.enabled ? Theme.foreground : Theme.dim
            font.family: Theme.fontFamily
            font.pixelSize: btn.small ? Theme.size(1) : Theme.size(2)
            font.weight: btn.primary ? Font.DemiBold : Font.Normal
            visible: btn.text.length > 0
        }
    }

    // `pressed` comes from the TapHandler so the fill darkens on press exactly
    // like the bar's Button.down path, without QtQuick.Controls in the tree.
    HoverHandler { id: hover; enabled: btn.enabled }
    TapHandler {
        id: tap
        enabled: btn.enabled
        onTapped: btn.clicked()
    }
}
