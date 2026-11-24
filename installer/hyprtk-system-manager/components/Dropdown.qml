// Dropdown matching hyprtk-bar-qt/components/TComboBox: 30px field, radius 6,
// translucent fill, accent2 border, and a solid-background popup with the
// accent2 hover row. The popup is hand-built so no platform palette leaks in.
import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: box

    property string value: ""
    property var choices: []
    property int preferredWidth: 200
    signal selected(string value)

    implicitWidth: preferredWidth
    implicitHeight: Theme.controlHeight
    radius: Theme.radiusControl
    color: Theme.controlFill
    border.width: 1
    border.color: popup.visible ? Theme.accent : Theme.controlBorder

    function labelFor(v) {
        const list = box.choices || [];
        for (let i = 0; i < list.length; i++) {
            if (list[i] && String(list[i].value) === String(v))
                return list[i].label;
        }
        return String(v);
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 9
        anchors.right: caret.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        text: box.labelFor(box.value)
        color: Theme.foreground
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
        elide: Text.ElideRight
    }
    Glyph {
        id: caret
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.verticalCenter: parent.verticalCenter
        glyph: "\uf078"
        pixelSize: 10
        color: Theme.dim
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: popup.visible ? popup.close() : popup.open() }

    Popup {
        id: popup
        parent: box
        x: 0
        y: box.height + 2
        width: box.width
        padding: 1
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusCard
            color: Theme.background
            border.width: 1
            border.color: Theme.alpha(Theme.accent2, 0.35)
        }

        contentItem: ListView {
            id: list
            implicitHeight: Math.min(300, contentHeight)
            clip: true
            model: box.choices
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                required property var modelData
                width: list.width
                height: 28
                color: hoverRow.hovered ? Theme.alpha(Theme.accent2, 0.20) : "transparent"
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: String(modelData.value) === String(box.value) ? Theme.accent : Theme.foreground
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                    elide: Text.ElideRight
                }
                HoverHandler { id: hoverRow }
                TapHandler {
                    onTapped: {
                        box.selected(String(modelData.value));
                        popup.close();
                    }
                }
            }
        }
    }
}
