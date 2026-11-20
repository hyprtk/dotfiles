import QtQuick

Rectangle {
    id: toggle

    property var th
    property string label: ""
    property bool checked: false
    signal toggled()

    width: label.length > 0 ? toggleText.implicitWidth + 46 : 40
    height: 24
    radius: 12
    color: checked ? toggle.th.accent : toggle.th.panel
    border.width: 1
    border.color: checked ? toggle.th.accent : toggle.th.border

    Text {
        id: toggleText
        visible: toggle.label.length > 0
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: toggle.label
        color: toggle.checked ? toggle.th.textOnAccent : toggle.th.foreground
        font.pixelSize: 11
    }

    Rectangle {
        width: 16
        height: 16
        radius: 8
        x: toggle.checked ? parent.width - width - 4 : 4
        anchors.verticalCenter: parent.verticalCenter
        color: toggle.checked ? toggle.th.textOnAccent : toggle.th.muted
        Behavior on x { NumberAnimation { duration: 90 } }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: toggle.toggled()
    }
}
