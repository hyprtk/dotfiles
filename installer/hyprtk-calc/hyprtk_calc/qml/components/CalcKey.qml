import QtQuick
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// One keypad key. Stateless and reusable: the label, what it inserts and how it
// is coloured all come from the model row in Keypad.qml.
Rectangle {
    id: key

    property var th: null
    property string label: ""
    property string token: ""      // text inserted into the expression
    property string action: ""     // clear | back | sign | equals | memory:<op>
    property bool accent: false     // operator: tinted with the accent colour
    property bool solid: false      // the equals key: full accent, dark label
    property bool soft: false
    property bool armed: false
    property real fontScale: 1.0

    signal activated()

    Layout.fillWidth: true
    Layout.preferredHeight: 50 * key.fontScale
    Layout.columnSpan: 1
    radius: 10

    readonly property color accentColor: key.th ? key.th.key_operator : "#c084fc"

    readonly property color base:
        key.armed ? (key.th ? key.th.key_hover : "#2a2c34")
                  : key.solid ? key.accentColor
                  : key.accent ? Util.alpha(key.accentColor, 0.16)
                  : key.soft ? (key.th ? key.th.key_alt : "#141620")
                             : (key.th ? key.th.key : "#1d1f28")

    color: mouse.containsMouse && !key.armed
           ? (key.accent || key.solid
              ? Util.alpha(key.accentColor, key.solid ? 0.86 : 0.28)
              : Util.mix(key.base, key.th ? key.th.foreground : "#ffffff", 0.14))
           : key.base
    border.width: 1
    border.color: key.accent || key.solid
                  ? Util.alpha(key.accentColor, 0.34)
                  : Util.alpha(key.th ? key.th.foreground : "#ffffff", 0.07)

    Behavior on color { ColorAnimation { duration: 90 } }

    Text {
        anchors.centerIn: parent
        text: key.label
        font.pixelSize: (key.label.length > 2 ? 15 : 19) * key.fontScale
        font.weight: key.accent ? Font.DemiBold : Font.Normal
        font.family: key.th && key.th.mono ? key.th.mono : "monospace"
        color: key.solid
               ? (key.th ? key.th.text_on_accent : "#11111b")
               : key.accent ? key.accentColor
                            : (key.th ? key.th.foreground : "#e5e7eb")
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: key.activated()
    }
}
