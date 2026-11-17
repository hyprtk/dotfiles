import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../theme/util.js" as Util

// The card shared by every keyboard picker (commands, quick open).
//
// It owns the parts that must look and behave identically everywhere — the
// field, the row list, the arrow/Enter/Esc handling and the footer — and stays
// dumb about where the rows come from: the command palette binds a filtered
// action list, quick open assigns ranked files. Rows are
// `{label, detail, hint}`; `detail` is the second line and may be empty.
Rectangle {
    id: root

    property string placeholder: "Type to filter…"
    property var items: []
    property int index: 0
    property string footer: ""
    property string emptyText: "Nothing matches"
    property int rowHeight: 38

    readonly property var th: Bridge.palette

    signal edited(string text)
    signal chosen(int index)
    signal dismissed()

    width: 620
    height: 432
    radius: 10
    color: root.th.surface
    border.width: 1
    border.color: Util.alpha(root.th.accent, 0.45)

    function reset() {
        field.text = "";
        root.index = root.items.length > 0 ? 0 : -1;
        list.currentIndex = root.index;
        field.forceActiveFocus();
    }

    function focusField() {
        field.forceActiveFocus();
    }

    function step(delta) {
        if (root.items.length === 0)
            return;
        root.index = Util.clamp(root.index + delta, 0, root.items.length - 1);
        list.currentIndex = root.index;
        list.positionViewAtIndex(root.index, ListView.Contain);
    }

    function choose(at) {
        var target = (at === undefined || at === null) ? root.index : at;
        if (target < 0 || target >= root.items.length)
            return;
        root.chosen(target);
    }

    // Rows change on every keystroke (binding) and once per open (assignment);
    // either way the selection belongs at the top.
    onItemsChanged: {
        root.index = root.items.length > 0 ? 0 : -1;
        list.currentIndex = root.index;
    }

    MouseArea { anchors.fill: parent }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        TextField {
            id: field
            Layout.fillWidth: true
            height: 36
            ContextMenu.menu: EditorMenu { editor: field }
            color: root.th.foreground
            selectionColor: Util.alpha(root.th.accent, 0.4)
            selectedTextColor: root.th.foreground
            font.pixelSize: 14
            leftPadding: 10
            placeholderText: root.placeholder
            placeholderTextColor: Util.alpha(root.th.muted, 0.75)
            background: Rectangle {
                radius: 6
                color: Util.alpha(root.th.background, 0.8)
                border.width: 1
                border.color: Util.alpha(root.th.accent, 0.5)
            }
            onTextChanged: root.edited(text)
            onAccepted: root.choose()
            Keys.onPressed: function (event) {
                if (event.key === Qt.Key_Escape) {
                    root.dismissed();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Down) {
                    root.step(1);
                    event.accepted = true;
                } else if (event.key === Qt.Key_Up) {
                    root.step(-1);
                    event.accepted = true;
                } else if (event.key === Qt.Key_PageDown) {
                    root.step(8);
                    event.accepted = true;
                } else if (event.key === Qt.Key_PageUp) {
                    root.step(-8);
                    event.accepted = true;
                }
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: root.items
            currentIndex: root.index
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                width: list.width
                height: root.rowHeight
                radius: 6
                color: index === root.index
                    ? Util.alpha(root.th.accent, 0.22)
                    : (rowMouse.containsMouse ? Util.alpha(root.th.surfaceAlt, 0.6) : "transparent")

                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: hintText.left
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        width: parent.width
                        text: modelData.label || ""
                        color: index === root.index ? root.th.accent : root.th.foreground
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                    }

                    Text {
                        width: parent.width
                        visible: (modelData.detail || "").length > 0
                        text: modelData.detail || ""
                        color: Util.alpha(root.th.muted, 0.8)
                        font.pixelSize: 10
                        elide: Text.ElideMiddle
                    }
                }

                Text {
                    id: hintText
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.hint || ""
                    color: root.th.muted
                    font.pixelSize: 10
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        root.index = index;
                        root.choose(index);
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.items.length > 0 ? root.footer : root.emptyText
            color: Util.alpha(root.th.muted, 0.8)
            font.pixelSize: 10
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }
    }
}
