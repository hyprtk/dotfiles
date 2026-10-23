import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    property string label: ""
    property string hint: ""
    spacing: 12

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Text {
            text: label
            color: Theme.text
            font.pixelSize: Theme.scaled(13)
        }
        Text {
            visible: hint.length > 0
            text: hint
            color: Theme.dim
            font.pixelSize: Theme.scaled(11)
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
