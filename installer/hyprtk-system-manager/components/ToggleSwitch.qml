// Pill toggle matching hyprtk-bar-qt/components/Toggle: 46x24, accent when on,
// accent2 at 35% when off, foreground knob.
import QtQuick
import "../theme"

Item {
    id: root
    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: 46
    implicitHeight: 24
    opacity: enabled ? 1 : 0.55

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked
            ? Theme.accent
            : Qt.rgba(Theme.accent2.r, Theme.accent2.g, Theme.accent2.b, 0.35)
        Behavior on color { ColorAnimation { duration: 140 } }

        Rectangle {
            width: parent.height - 6
            height: width
            radius: width / 2
            y: 3
            x: root.checked ? parent.width - width - 3 : 3
            color: Theme.foreground
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    TapHandler { enabled: root.enabled; onTapped: root.toggled(!root.checked) }
}
