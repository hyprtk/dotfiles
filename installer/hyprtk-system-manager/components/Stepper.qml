// Numeric field matching hyprtk-bar-qt/components/TSpinBox: a single 30px
// control with the value at the left and up/down glyph steppers on the right.
import QtQuick
import "../theme"

Rectangle {
    id: root

    property real value: 0
    property real from: 0
    property real to: 100
    property real step: 1
    property int decimals: 0
    property string unit: ""
    signal moved(real value)

    implicitWidth: 120
    implicitHeight: Theme.controlHeight
    radius: Theme.radiusControl
    color: Theme.controlFill
    border.width: 1
    border.color: input.activeFocus ? Theme.accent : Theme.controlBorder

    function clamp(v) {
        let next = Math.max(root.from, Math.min(root.to, v));
        if (root.step > 0)
            next = Math.round(next / root.step) * root.step;
        return next;
    }
    function label(v) {
        const n = root.decimals > 0 ? Number(v).toFixed(root.decimals) : String(Math.round(v));
        return n + root.unit;
    }

    TextInput {
        id: input
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: steppers.left
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        text: root.label(root.value)
        color: Theme.foreground
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
        clip: true
        horizontalAlignment: TextInput.AlignLeft
        onEditingFinished: {
            const parsed = parseFloat(String(text).replace(root.unit, ""));
            if (!isNaN(parsed)) {
                const next = root.clamp(parsed);
                root.moved(next);
                text = root.label(next);
            } else {
                text = root.label(root.value);
            }
        }
    }

    Column {
        id: steppers
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: 22
        height: parent.height

        Rectangle {
            width: parent.width
            height: parent.height / 2
            color: upHover.hovered ? Theme.alpha(Theme.accent2, 0.28) : "transparent"
            Text {
                anchors.centerIn: parent
                text: "\uf077"
                color: Theme.dim
                font.family: Theme.iconFont
                font.pixelSize: 9
            }
            HoverHandler { id: upHover }
            TapHandler { onTapped: root.moved(root.clamp(root.value + root.step)) }
        }
        Rectangle {
            width: parent.width
            height: parent.height / 2
            color: downHover.hovered ? Theme.alpha(Theme.accent2, 0.28) : "transparent"
            Text {
                anchors.centerIn: parent
                text: "\uf078"
                color: Theme.dim
                font.family: Theme.iconFont
                font.pixelSize: 9
            }
            HoverHandler { id: downHover }
            TapHandler { onTapped: root.moved(root.clamp(root.value - root.step)) }
        }
    }
}
