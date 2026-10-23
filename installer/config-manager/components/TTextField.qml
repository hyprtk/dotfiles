// Themed single-line text field (bar field surface).
import QtQuick
import "../theme"

Rectangle {
    id: root
    property string text: ""
    property string placeholderText: ""
    signal edited(string value)

    implicitHeight: Theme.controlHeight
    implicitWidth: 180
    radius: 8
    color: Theme.alpha(Theme.background, 0.6)
    border.color: input.activeFocus ? Theme.accent : Theme.alpha(Theme.accent2, 0.30)
    clip: true

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        visible: input.text.length === 0 && !input.activeFocus
        text: root.placeholderText
        color: Theme.dim
        font.pixelSize: Theme.scaled(12)
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        verticalAlignment: TextInput.AlignVCenter
        text: root.text
        color: Theme.foreground
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.pixelSize: Theme.scaled(12)
        selectByMouse: true
        onEditingFinished: if (text !== root.text) root.edited(text)
        onTextChanged: if (!activeFocus) cursorPosition = 0
    }
    onTextChanged: if (input.text !== text) input.text = text
}
