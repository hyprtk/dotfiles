// Text field matching hyprtk-bar-qt/components/TTextField: 30px tall, radius 6,
// translucent background fill and an accent2 border that turns accent on focus.
import QtQuick
import "../theme"

Rectangle {
    id: field

    property alias text: input.text
    property alias input: input
    property alias echoMode: input.echoMode
    property string placeholder: ""
    property bool mono: false
    property int preferredWidth: 200
    property bool invalid: false
    signal edited(string value)
    signal committed(string value)
    signal accepted()

    implicitWidth: preferredWidth
    implicitHeight: Theme.controlHeight
    radius: Theme.radiusControl
    color: Theme.controlFill
    border.width: 1
    border.color: input.activeFocus ? Theme.accent
                : field.invalid ? Theme.danger
                : Theme.controlBorder

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 9
        anchors.rightMargin: 9
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.foreground
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.family: field.mono ? Theme.monoFamily : Theme.fontFamily
        font.pixelSize: Theme.size(2)
        clip: true
        onTextEdited: field.edited(text)
        onEditingFinished: field.committed(text)
        onAccepted: field.accepted()
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.verticalCenter: parent.verticalCenter
        visible: input.text.length === 0
        text: field.placeholder
        color: Theme.dim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
    }
}
