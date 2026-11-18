import QtQuick
import QtQuick.Controls
import "../theme"
import "../theme/util.js" as Util

// A themed context menu.
//
// QtQuick.Controls' Menu takes its palette from QQuickTheme, which follows the
// platform theme (GTK here) and ignores pywal — that is why the right-click
// menu used to be a white GTK box. Popup only supplies the window/dismiss
// behaviour; the surface, the rows and the colours are ours.
Popup {
    id: menu

    property var theme
    property var items: []          // [{ id, label, enabled, separator }]
    signal triggered(string action)

    width: 208
    padding: 6
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function openAt(x, y) {
        menu.x = x;
        menu.y = y;
        menu.open();
    }

    background: Rectangle {
        color: Util.alpha(menu.theme.surface, 0.98)
        radius: 9
        border.width: 1
        border.color: Util.alpha(menu.theme.border, 0.65)
    }

    contentItem: Column {
        spacing: 1

        Repeater {
            model: menu.items

            delegate: Item {
                id: row
                width: menu.width - 12
                height: modelData.separator ? 9 : 28

                Rectangle {
                    visible: !!modelData.separator
                    anchors.centerIn: parent
                    width: parent.width - 8
                    height: 1
                    color: Util.alpha(menu.theme.border, 0.5)
                }

                Rectangle {
                    anchors.fill: parent
                    visible: !modelData.separator
                    radius: 6
                    color: area.containsMouse && row.usable
                           ? Util.alpha(menu.theme.accent, 0.22)
                           : "transparent"
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !modelData.separator
                    text: modelData.label || ""
                    font.pixelSize: 12
                    color: row.usable ? menu.theme.foreground
                                       : Util.alpha(menu.theme.muted, 0.45)
                }

                // `enabled` is already a QQuickItem property; shadowing it is an error.
                property bool usable: !modelData.separator && modelData.enabled !== false

                MouseArea {
                    id: area
                    anchors.fill: parent
                    enabled: row.usable
                    hoverEnabled: true
                    cursorShape: row.usable ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        menu.triggered(modelData.id);
                        menu.close();
                    }
                }
            }
        }
    }
}
