// Themed combo box with a themed popup list.
import QtQuick
import QtQuick.Controls.Basic
import "../theme"

ComboBox {
    id: root

    property string emptyText: "(default)"

    implicitHeight: Theme.controlHeight
    implicitWidth: 180
    font.pixelSize: Theme.scaled(12)
    leftPadding: 10
    rightPadding: 24

    contentItem: Text {
        text: root.displayText.length > 0 ? root.displayText : root.emptyText
        font: root.font
        color: root.enabled ? Theme.foreground : Theme.dim
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: root.width - width - 8
        anchors.verticalCenter: parent.verticalCenter
        text: "\u25be"
        color: Theme.dim
        font.pixelSize: Theme.scaled(11)
    }

    background: Rectangle {
        radius: 8
        color: Theme.alpha(Theme.background, 0.6)
        border.color: root.activeFocus ? Theme.accent : Theme.alpha(Theme.accent2, 0.30)
    }

    delegate: ItemDelegate {
        id: item
        required property var modelData
        required property int index
        width: root.width
        implicitHeight: 28
        highlighted: root.highlightedIndex === index
        contentItem: Text {
            text: item.modelData
            color: Theme.foreground
            font.pixelSize: Theme.scaled(12)
            verticalAlignment: Text.AlignVCenter
            leftPadding: 8
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: item.highlighted ? Theme.alpha(Theme.accent2, 0.20) : "transparent"
        }
    }

    popup: Popup {
        y: root.height + 2
        width: root.width
        implicitHeight: Math.min(260, contentItem.implicitHeight + 2)
        padding: 1
        background: Rectangle {
            radius: 8
            color: Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b, Theme.panelOpacityStrong)
            border.width: 1
            border.color: Theme.alpha(Theme.accent2, 0.35)
        }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
        }
    }
}
