import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "theme/util.js" as Util
import "components"

Rectangle {
    id: root

    property alias query: queryField.text
    property alias replacement: replaceField.text
    property bool caseSensitive: false
    property bool wholeWord: false
    property bool regex: false
    property bool replaceMode: false
    property int matchCount: 0
    property int matchIndex: -1

    readonly property var th: Bridge.palette

    signal queryEdited()
    signal nextRequested()
    signal previousRequested()
    signal replaceOneRequested()
    signal replaceAllRequested()
    signal closed()

    width: 540
    height: replaceMode ? 84 : 44
    radius: 9
    color: Util.alpha(root.th.surfaceAlt, 0.98)
    border.width: 1
    border.color: Util.alpha(root.th.accent, 0.45)
    z: 40

    function focusQuery() {
        queryField.forceActiveFocus();
        queryField.selectAll();
    }

    function focusReplace() {
        replaceField.forceActiveFocus();
        replaceField.selectAll();
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: Glyph.search
                color: root.th.muted
                font.family: Glyph.family
                font.pixelSize: 12
            }

            TextField {
                id: queryField
                Layout.fillWidth: true
                height: 26
                color: root.th.foreground
                selectionColor: Util.alpha(root.th.accent, 0.4)
                selectedTextColor: root.th.foreground
                font.pixelSize: 12
                leftPadding: 8
                rightPadding: 8
                background: Rectangle {
                    radius: 5
                    color: Util.alpha(root.th.background, 0.75)
                    border.width: 1
                    border.color: queryField.activeFocus
                        ? Util.alpha(root.th.accent, 0.6)
                        : Util.alpha(root.th.border, 0.6)
                }
                onTextChanged: root.queryEdited()
                onAccepted: root.nextRequested()
                Keys.onPressed: function (event) {
                    if (event.key === Qt.Key_Escape) {
                        root.closed();
                        event.accepted = true;
                    } else if (event.key === Qt.Key_Return && (event.modifiers & Qt.ShiftModifier)) {
                        root.previousRequested();
                        event.accepted = true;
                    }
                }
            }

            Text {
                text: root.matchCount > 0
                    ? (root.matchIndex + 1) + "/" + root.matchCount
                    : "0/0"
                color: root.matchCount > 0 ? root.th.muted : root.th.danger
                font.pixelSize: 11
                Layout.minimumWidth: 44
                horizontalAlignment: Text.AlignRight
            }

            IconButton { glyph: Glyph.chevronUp; hint: "Previous (Shift+Enter)"; size: 26; onClicked: root.previousRequested() }
            IconButton { glyph: Glyph.chevronDown; hint: "Next (Enter)"; size: 26; onClicked: root.nextRequested() }

            FlatButton {
                text: "Aa"
                active: root.caseSensitive
                onClicked: { root.caseSensitive = !root.caseSensitive; root.queryEdited(); }
            }
            FlatButton {
                text: "W"
                active: root.wholeWord
                onClicked: { root.wholeWord = !root.wholeWord; root.queryEdited(); }
            }
            FlatButton {
                text: ".*"
                active: root.regex
                onClicked: { root.regex = !root.regex; root.queryEdited(); }
            }
            FlatButton {
                text: root.replaceMode ? "Find" : "Replace"
                active: root.replaceMode
                onClicked: root.replaceMode = !root.replaceMode
            }
            IconButton {
                glyph: Glyph.close
                hint: "Close (Esc)"
                size: 24
                onClicked: root.closed()
            }
        }

        RowLayout {
            visible: root.replaceMode
            Layout.fillWidth: true
            spacing: 6

            Item { width: 18 }

            TextField {
                id: replaceField
                Layout.fillWidth: true
                height: 26
                color: root.th.foreground
                selectionColor: Util.alpha(root.th.accent, 0.4)
                selectedTextColor: root.th.foreground
                font.pixelSize: 12
                leftPadding: 8
                rightPadding: 8
                placeholderText: "Replace with…"
                placeholderTextColor: Util.alpha(root.th.muted, 0.7)
                background: Rectangle {
                    radius: 5
                    color: Util.alpha(root.th.background, 0.75)
                    border.width: 1
                    border.color: replaceField.activeFocus
                        ? Util.alpha(root.th.accent, 0.6)
                        : Util.alpha(root.th.border, 0.6)
                }
                onAccepted: root.replaceOneRequested()
            }

            FlatButton { text: "Replace"; onClicked: root.replaceOneRequested() }
            FlatButton { text: "All"; onClicked: root.replaceAllRequested() }
            Item { Layout.fillWidth: true }
        }
    }
}
