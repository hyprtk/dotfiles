import QtQuick
import "../theme"

Row {
    id: root

    property alias text: field.text
    property string placeholder: ""
    property bool mono: true
    property int preferredWidth: 280
    signal edited(string value)
    signal browseRequested()

    spacing: 6

    TTextField {
        id: field
        preferredWidth: root.preferredWidth - 92
        placeholder: root.placeholder
        mono: root.mono
        onEdited: (v) => root.edited(v)
    }
    TButton {
        text: "Browse"
        small: true
        onClicked: root.browseRequested()
    }
}
