// Compact numeric field with inline step buttons.
import QtQuick
import "../theme"

Rectangle {
    id: root
    property real value: 0
    property real from: 0
    property real to: 100
    property real step: 1
    property int decimals: 0
    signal modified(real value)

    implicitWidth: 150
    implicitHeight: Theme.controlHeight
    radius: 8
    color: Theme.alpha(Theme.background, 0.6)
    border.color: input.activeFocus ? Theme.accent : Theme.alpha(Theme.accent2, 0.30)
    clip: true

    function apply(v, notify) {
        const clamped = Math.max(root.from, Math.min(root.to, v));
        root.value = clamped;
        sync();
        if (notify)
            root.modified(clamped);
    }

    function sync() {
        if (!input.activeFocus)
            input.text = root.value.toFixed(root.decimals);
    }

    onValueChanged: sync()
    Component.onCompleted: sync()

    Rectangle {
        id: minus
        width: 24
        height: parent.height
        anchors.left: parent.left
        color: minusArea.containsMouse ? Theme.alpha(Theme.accent2, 0.28) : "transparent"
        Text {
            anchors.centerIn: parent
            text: "\u2212"
            color: Theme.dim
            font.pixelSize: Theme.scaled(13)
        }
        MouseArea {
            id: minusArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.apply(root.value - root.step, true)
        }
    }

    Rectangle {
        id: plus
        width: 24
        height: parent.height
        anchors.right: parent.right
        color: plusArea.containsMouse ? Theme.alpha(Theme.accent2, 0.28) : "transparent"
        Text {
            anchors.centerIn: parent
            text: "+"
            color: Theme.dim
            font.pixelSize: Theme.scaled(13)
        }
        MouseArea {
            id: plusArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.apply(root.value + root.step, true)
        }
    }

    TextInput {
        id: input
        anchors.left: minus.right
        anchors.right: plus.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        color: Theme.foreground
        selectionColor: Theme.accent
        selectedTextColor: Theme.textOnAccent
        font.pixelSize: Theme.scaled(12)
        selectByMouse: true
        validator: DoubleValidator {
            bottom: root.from
            top: root.to
            decimals: root.decimals
        }
        onEditingFinished: {
            const v = parseFloat(text);
            if (!isNaN(v))
                root.apply(v, true);
            else
                root.sync();
        }
        onActiveFocusChanged: if (!activeFocus) root.sync()
    }
}
