import QtQuick
import QtQuick.Controls
import "../theme"

Column {
    id: root

    property string label: ""
    property string placeholder: ""
    property alias text: field.text
    property alias input: field

    signal accepted()

    spacing: 4

    Text {
        text: root.label
        color: Theme.muted
        font.pixelSize: 10
    }

    TextField {
        id: field
        width: parent.width
        placeholderText: root.placeholder
        color: Theme.foreground
        placeholderTextColor: Theme.alpha(Theme.foreground, 0.35)
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.pixelSize: 12
        onAccepted: root.accepted()

        background: Rectangle {
            radius: 6
            color: Theme.alpha(Theme.foreground, 0.06)
            border.width: 1
            border.color: Theme.alpha(Theme.accent, 0.5)
        }
    }
}
