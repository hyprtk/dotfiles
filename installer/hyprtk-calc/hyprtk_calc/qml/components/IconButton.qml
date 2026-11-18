import QtQuick
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// A square chrome button carrying a Symbols Nerd Font glyph.
Rectangle {
    id: button

    property var th: null
    property string glyph: ""
    property string tooltip: ""
    property bool active: false

    signal clicked()

    implicitWidth: 30
    implicitHeight: 30
    radius: 8
    color: mouse.containsMouse || button.active
           ? Util.alpha(button.th ? button.th.foreground : "#ffffff", button.active ? 0.16 : 0.09)
           : "transparent"

    Behavior on color { ColorAnimation { duration: 100 } }

    Text {
        anchors.centerIn: parent
        text: button.glyph
        font.family: Glyph.family
        font.pixelSize: 13
        color: button.active
               ? (button.th ? button.th.accent : "#c084fc")
               : (button.th ? button.th.muted : "#a6adc8")
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: button.clicked()
    }
}
