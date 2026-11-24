// Small pill matching hyprtk-bar-qt/components/ChipButton: radius 6, tinted
// fill, 10px label.
import QtQuick
import "../theme"

Rectangle {
    id: pill
    property string text: ""
    property string tone: "neutral"

    readonly property var tones: ({
        neutral: Theme.dim,
        ok: Theme.ok,
        warn: Theme.warn,
        danger: Theme.danger,
        info: Theme.info,
        accent: Theme.accent,
        accent2: Theme.accent2,
    })
    readonly property color tint: tones[tone] || Theme.dim

    implicitWidth: label.implicitWidth + 16
    implicitHeight: 22
    radius: Theme.radiusControl
    color: Theme.alpha(tint, 0.18)
    border.width: 1
    border.color: Theme.alpha(tint, 0.32)

    Text {
        id: label
        anchors.centerIn: parent
        text: pill.text
        color: pill.tint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(0)
        font.weight: Font.DemiBold
    }
}
