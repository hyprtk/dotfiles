import QtQuick

Rectangle {
    id: button

    property var th
    property string label: "Button"
    property bool primary: false
    property bool usable: true
    property color tint: "#313244"
    signal clicked()

    width: Math.max(54, buttonText.implicitWidth + 22)
    height: 30
    radius: 8
    opacity: usable ? 1 : 0.4
    color: primary ? button.th.accent : (btnHover.containsMouse && usable ? button.th.panelHover : tint)
    border.width: 1
    border.color: primary ? button.th.accent : button.th.border

    Text {
        id: buttonText
        anchors.centerIn: parent
        text: button.label
        color: button.primary ? button.th.textOnAccent : button.th.foreground
        font.pixelSize: 11
    }

    MouseArea {
        id: btnHover
        anchors.fill: parent
        hoverEnabled: true
        enabled: button.usable
        cursorShape: Qt.PointingHandCursor
        onClicked: button.clicked()
    }
}
