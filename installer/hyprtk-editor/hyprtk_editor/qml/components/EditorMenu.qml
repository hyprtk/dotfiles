import QtQuick
import QtQuick.Controls
import "../theme/util.js" as Util

// The editor's right-click menu.
//
// Qt Quick Controls ships a TextEditingContextMenu for TextArea, but it is
// painted from the control palette, which knows nothing about the wallpaper —
// so the menu came up in the stock black/blue of the Basic style next to a
// pywal window. This is the same action set dressed in the editor palette.
Menu {
    id: menu

    // The TextArea this menu belongs to.
    required property var editor

    readonly property var th: Bridge.palette
    readonly property int fontSize: 12

    // A window popup is its own surface on Wayland and cannot be positioned
    // against the editor; an item popup stays inside the window.
    popupType: Qt.platform.pluginName !== "wayland" ? Popup.Window : Popup.Item
    margins: 0
    overlap: 1
    padding: 5
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    palette.window: menu.th.surface
    palette.windowText: menu.th.foreground
    palette.light: Util.alpha(menu.th.accent, 0.22)
    palette.midlight: Util.alpha(menu.th.accent, 0.3)
    palette.mid: menu.th.border
    palette.dark: menu.th.border
    palette.text: menu.th.foreground
    palette.highlight: menu.th.accent
    palette.highlightedText: menu.th.onAccent

    background: Rectangle {
        implicitWidth: 210
        implicitHeight: 40
        radius: 10
        color: menu.th.surface
        border.width: 1
        border.color: Util.alpha(menu.th.accent, 0.45)
    }

    // The Basic menu puts a ScrollIndicator in its list view, which showed as a
    // stray line down the right edge. Same list, no indicator.
    contentItem: ListView {
        implicitHeight: contentHeight
        model: menu.contentModel
        interactive: Window.window
                     ? contentHeight + menu.topPadding + menu.bottomPadding > menu.height
                     : false
        clip: true
        currentIndex: menu.currentIndex
    }

    delegate: MenuItem {
        id: entry

        implicitWidth: 200
        implicitHeight: 32
        padding: 0

        contentItem: Text {
            text: entry.text
            leftPadding: 12
            rightPadding: 12
            font.family: Bridge.fontFamily
            font.pixelSize: menu.fontSize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            color: !entry.enabled
                ? Util.alpha(menu.th.muted, 0.55)
                : (entry.highlighted ? menu.th.accent : menu.th.foreground)
        }

        background: Rectangle {
            width: entry.width
            height: entry.height
            radius: 6
            color: entry.highlighted && entry.enabled
                ? Util.alpha(menu.th.accent, 0.22)
                : "transparent"
        }
    }

    Action {
        text: "Undo"
        enabled: menu.editor.canUndo
        onTriggered: menu.editor.undo()
    }
    Action {
        text: "Redo"
        enabled: menu.editor.canRedo
        onTriggered: menu.editor.redo()
    }

    MenuSeparator {}

    Action {
        text: "Cut"
        enabled: !menu.editor.readOnly && menu.editor.selectedText.length > 0
        onTriggered: menu.editor.cut()
    }
    Action {
        text: "Copy"
        enabled: menu.editor.selectedText.length > 0
        onTriggered: menu.editor.copy()
    }
    Action {
        text: "Paste"
        enabled: !menu.editor.readOnly && menu.editor.canPaste
        onTriggered: menu.editor.paste()
    }
    Action {
        text: "Delete"
        enabled: !menu.editor.readOnly && menu.editor.selectedText.length > 0
        onTriggered: menu.editor.remove(menu.editor.selectionStart, menu.editor.selectionEnd)
    }

    MenuSeparator {}

    Action {
        text: "Select All"
        onTriggered: menu.editor.selectAll()
    }
}
