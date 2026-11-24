// Navigation in the bar's Settings language: 200px rail at 60% background,
// accent2 group labels, 32px items with an accent-fill selection.
import QtQuick
import "../theme"
import "../components"

Rectangle {
    id: sidebar

    property var groups: []
    property var panels: []
    property var searchResults: []
    property string currentPage: ""
    property string hostname: ""
    property string version: ""
    property string privilege: ""
    property alias searchText: search.text

    signal select(string id)
    signal searchChanged(string text)
    signal submitted()

    function focusSearch() { search.forceActiveFocus(); }
    function clearSearch() {
        if (search.text.length > 0) {
            search.text = "";
            sidebar.searchChanged("");
        }
    }
    function panelsIn(groupId) {
        return sidebar.panels.filter(p => p.group === groupId);
    }
    function matches(panel) {
        if (search.text.length === 0)
            return true;
        const hay = (panel.title + " " + panel.description + " " +
                     (panel.keywords || []).join(" ")).toLowerCase();
        return hay.indexOf(search.text.toLowerCase()) >= 0;
    }

    color: Theme.alpha(Theme.background, 0.60)
    // Match the panel's corner so the rail never paints a square corner outside
    // the animated border (the bar's Settings sidebar does the same).
    topLeftRadius: Theme.radiusLg
    bottomLeftRadius: Theme.radiusLg

    Column {
        anchors.fill: parent
        anchors.topMargin: 14
        spacing: 8

        // ── identity ───────────────────────────────────────────────
        Row {
            x: 14
            width: parent.width - 28
            spacing: 8
            Glyph {
                glyph: "\uf1de"
                pixelSize: 22
                color: Theme.accent
                anchors.verticalCenter: parent.verticalCenter
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 0
                Text {
                    text: "System Settings"
                    color: Theme.foreground
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(3)
                    font.bold: true
                }
                Text {
                    text: sidebar.hostname || "this device"
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(0)
                }
            }
        }

        // ── search ─────────────────────────────────────────────────
        Rectangle {
            x: 10
            width: parent.width - 20
            height: Theme.controlHeight
            radius: Theme.radiusControl
            color: Theme.controlFill
            border.width: 1
            border.color: search.activeFocus ? Theme.accent : Theme.controlBorder

            Glyph {
                id: searchGlyph
                anchors.left: parent.left
                anchors.leftMargin: 9
                anchors.verticalCenter: parent.verticalCenter
                glyph: "\uf002"
                pixelSize: 10
                color: Theme.dim
            }
            TextInput {
                id: search
                anchors.left: searchGlyph.right
                anchors.leftMargin: 7
                anchors.right: parent.right
                anchors.rightMargin: 9
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.foreground
                selectionColor: Theme.accent
                selectedTextColor: Theme.textOnAccent
                font.family: Theme.fontFamily
                font.pixelSize: Theme.size(2)
                clip: true
                onTextEdited: sidebar.searchChanged(text)
                onAccepted: sidebar.submitted()
                Keys.onEscapePressed: { text = ""; sidebar.searchChanged(""); }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: search.text.length === 0
                    text: "Search settings…"
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                }
            }
        }

        // ── results / navigation ───────────────────────────────────
        Flickable {
            id: scroller
            width: parent.width
            height: parent.height - y - 32
            contentHeight: navColumn.implicitHeight + 12
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: navColumn
                width: scroller.width
                spacing: 1

                // search results
                Repeater {
                    model: sidebar.searchText.length > 0 ? sidebar.searchResults : []
                    delegate: Rectangle {
                        required property var modelData
                        width: navColumn.width - 20
                        x: 10
                        height: 44
                        radius: Theme.radiusCard
                        color: resultHover.hovered ? Theme.hoverTint : "transparent"

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            Glyph { glyph: modelData.icon || ""; pixelSize: Theme.size(2); color: Theme.dim; anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                width: parent.width - 30
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 0
                                Text {
                                    text: modelData.title || ""
                                    color: Theme.foreground
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.size(2)
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                                Text {
                                    text: modelData.description || ""
                                    color: Theme.dim
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.size(0)
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }
                        }
                        HoverHandler { id: resultHover }
                        TapHandler { onTapped: sidebar.select(modelData.id) }
                    }
                }

                // grouped panels
                Repeater {
                    model: sidebar.searchText.length > 0 ? [] : sidebar.groups
                    delegate: Column {
                        required property var modelData
                        width: navColumn.width
                        spacing: 1
                        visible: sidebar.panelsIn(modelData.id).some(p => sidebar.matches(p))

                        Text {
                            x: 14
                            topPadding: 10
                            bottomPadding: 2
                            text: modelData.title
                            color: Theme.accent2
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.size(0)
                            font.bold: true
                        }

                        Repeater {
                            model: sidebar.panelsIn(modelData.id).filter(p => sidebar.matches(p))
                            delegate: NavItem {
                                required property var modelData
                                x: 10
                                width: navColumn.width - 20
                                glyph: modelData.icon
                                label: modelData.title
                                active: sidebar.currentPage === modelData.id
                                onClicked: sidebar.select(modelData.id)
                            }
                        }
                    }
                }

                Text {
                    visible: sidebar.searchText.length > 0 && sidebar.searchResults.length === 0
                    x: 14
                    topPadding: 12
                    text: "No matching settings."
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(2)
                }
            }
        }

        // ── footer ─────────────────────────────────────────────────
        Row {
            x: 14
            width: parent.width - 28
            spacing: 5
            Text {
                text: "v" + (sidebar.version || "0.1.0")
                color: Theme.dim
                font.family: Theme.monoFamily
                font.pixelSize: 9
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "·"
                color: Theme.dim
                font.pixelSize: 9
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: sidebar.privilege || "user"
                color: Theme.dim
                font.family: Theme.monoFamily
                font.pixelSize: 9
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
