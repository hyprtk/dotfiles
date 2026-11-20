import QtQuick

Row {
    id: segmented

    property var th
    property var options: []
    property var current: ""
    signal picked(var value)

    spacing: 4

    Repeater {
        model: segmented.options
        delegate: Rectangle {
            required property var modelData
            width: optionLabel.implicitWidth + 22
            height: 28
            radius: 7
            color: segmented.current === modelData.v
                   ? segmented.th.accent
                   : (optionHover.containsMouse ? segmented.th.panelHover : segmented.th.panel)
            border.width: 1
            border.color: segmented.current === modelData.v ? segmented.th.accent : segmented.th.border

            Text {
                id: optionLabel
                anchors.centerIn: parent
                text: modelData.l
                color: segmented.current === modelData.v
                       ? segmented.th.textOnAccent
                       : segmented.th.foreground
                font.pixelSize: 11
            }

            MouseArea {
                id: optionHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: segmented.picked(modelData.v)
            }
        }
    }
}
