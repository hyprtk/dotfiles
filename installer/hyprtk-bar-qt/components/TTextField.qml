// Themed text field.
import QtQuick
import QtQuick.Controls.Basic
import "../theme"

TextField {
    id: root

    property int radius: 6
    property color backgroundColor: Theme.alpha(Theme.background, 0.6)
    property color focusBorderColor: Theme.accent
    property color idleBorderColor: Theme.alpha(Theme.accent2, 0.30)

    implicitHeight: 30
    font.pixelSize: Theme.fontSize
    font.family: Theme.fontFamily
    color: Theme.foreground
    placeholderTextColor: Theme.dim
    selectionColor: Theme.accent
    selectedTextColor: Theme.textOnAccent
    leftPadding: 9
    rightPadding: 9

    background: Rectangle {
        radius: root.radius
        color: root.backgroundColor
        border.width: 1
        border.color: root.activeFocus ? root.focusBorderColor : root.idleBorderColor
    }
}
