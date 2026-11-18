import QtQuick
import "../theme"
import "../theme/util.js" as Util

// Scrollback search bar. Lives in the window chrome, drives the active
// TerminalView through runSearch/searchNext/searchPrevious.
Rectangle {
    id: bar

    property var theme
    property var view
    property string monoFamily: "monospace"
    property bool caseSensitive: false
    property bool regex: false
    signal closed()

    width: 438
    height: 34
    radius: 9
    visible: false
    color: Util.alpha(theme.surface, 0.97)
    border.width: 1
    border.color: Util.alpha(theme.accent, 0.45)

    function open() {
        visible = true;
        field.forceActiveFocus();
        field.selectAll();
        run();
    }

    function close() {
        visible = false;
        if (view)
            view.clearSearch();
        closed();
    }

    function run() {
        if (!view)
            return;
        view.runSearch(field.text, bar.caseSensitive, bar.regex);
    }

    Connections {
        target: bar.view ? bar.view : null
        ignoreUnknownSignals: true
        function onSearchChanged() {
            count.text = bar.view.matchCount > 0
                ? bar.view.matchIndex + "/" + bar.view.matchCount
                : (field.text ? "0/0" : "");
        }
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 9
        anchors.rightMargin: 7
        spacing: 7

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: Glyph.search
            font.family: Glyph.family
            font.pixelSize: 11
            color: Util.alpha(bar.theme.muted, 0.9)
        }

        TextInput {
            id: field
            width: Math.max(80, parent.width - 224)
            anchors.verticalCenter: parent.verticalCenter
            color: bar.theme.foreground
            selectionColor: Util.alpha(bar.theme.accent2, 0.45)
            selectedTextColor: bar.theme.background
            font.family: bar.monoFamily
            font.pixelSize: 12
            clip: true
            onTextChanged: searchTimer.restart()
            onAccepted: bar.view && bar.view.searchNext()
            Keys.onEscapePressed: bar.close()
            Keys.onDownPressed: bar.view && bar.view.searchNext()
            Keys.onUpPressed: bar.view && bar.view.searchPrevious()

            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: !field.text.length
                text: "Search scrollback"
                color: Util.alpha(bar.theme.muted, 0.55)
                font: field.font
            }
        }

        Text {
            id: count
            width: 54
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignRight
            text: ""
            color: Util.alpha(bar.theme.muted, 0.95)
            font.family: bar.monoFamily
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        Chip {
            label: "Aa"
            active: bar.caseSensitive
            onClicked: { bar.caseSensitive = !bar.caseSensitive; bar.run(); }
        }
        Chip {
            label: ".*"
            active: bar.regex
            onClicked: { bar.regex = !bar.regex; bar.run(); }
        }
        Chip {
            label: Glyph.chevronUp
            glyph: true
            onClicked: bar.view && bar.view.searchPrevious()
        }
        Chip {
            label: Glyph.chevronDown
            glyph: true
            onClicked: bar.view && bar.view.searchNext()
        }
        Chip {
            label: Glyph.close
            glyph: true
            onClicked: bar.close()
        }
    }

    Timer {
        id: searchTimer
        interval: 130
        onTriggered: bar.run()
    }

    component Chip: Rectangle {
        property string label: ""
        property bool glyph: false
        property bool active: false
        signal clicked()

        width: glyph ? 22 : 26
        height: 22
        radius: 6
        anchors.verticalCenter: parent.verticalCenter
        color: active ? Util.alpha(bar.theme.accent, 0.28)
                      : (area.containsMouse ? Util.alpha(bar.theme.surface_alt, 0.9) : "transparent")
        border.width: active ? 1 : 0
        border.color: Util.alpha(bar.theme.accent, 0.6)

        Text {
            anchors.centerIn: parent
            text: parent.label
            font.family: parent.glyph ? Glyph.family : bar.monoFamily
            font.pixelSize: parent.glyph ? 9 : 10
            color: parent.active ? bar.theme.accent : Util.alpha(bar.theme.foreground, 0.85)
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }
}
