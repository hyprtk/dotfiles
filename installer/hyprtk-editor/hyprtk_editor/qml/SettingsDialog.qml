import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme"
import "theme/util.js" as Util
import "components"

Rectangle {
    id: root

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config

    signal closed()

    anchors.fill: parent
    z: 480
    visible: false
    color: Util.alpha(root.th.background, 0.6)

    function open() {
        root.visible = true;
    }

    function close() {
        root.visible = false;
        root.closed();
    }

    function set(key, value) {
        var patch = {};
        patch[key] = value;
        Bridge.updateSettings(patch);
    }

    function cycleFont() {
        var choices = Bridge.fontChoices;
        var current = Bridge.fontFamily;
        var index = 0;
        for (var i = 0; i < choices.length; i++) {
            if (choices[i].name === current) {
                index = i;
                break;
            }
        }
        root.set("font_family", choices[(index + 1) % choices.length].name);
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Rectangle {
        id: card
        width: Math.min(640, root.width - 80)
        height: Math.min(620, root.height - 80)
        anchors.centerIn: parent
        radius: 10
        color: root.th.surface
        border.width: 1
        border.color: Util.alpha(root.th.border, 0.9)

        MouseArea { anchors.fill: parent }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Preferences"
                    color: root.th.foreground
                    font.pixelSize: 15
                    font.weight: 600
                    Layout.fillWidth: true
                }
                FlatButton { text: "Clear recent"; onClicked: Bridge.clearRecent() }
                IconButton { glyph: Glyph.close; hint: "Close"; onClicked: root.close() }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Util.alpha(root.th.border, 0.7)
            }

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentHeight: settingsColumn.implicitHeight
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: settingsColumn
                    width: parent.width
                    spacing: 2

                    SettingRow {
                        width: parent.width
                        label: "Font"
                        hint: "Click to cycle through the installed monospace families"
                        FlatButton { text: Bridge.fontFamily; onClicked: root.cycleFont() }
                    }

                    SettingRow {
                        width: parent.width
                        label: "Font size"
                        FlatButton { text: "−"; onClicked: root.set("font_size", Math.max(9, (root.cfg.font_size || 13) - 1)) }
                        Text {
                            text: root.cfg.font_size || 13
                            color: root.th.foreground
                            font.pixelSize: 12
                            Layout.minimumWidth: 22
                            horizontalAlignment: Text.AlignHCenter
                        }
                        FlatButton { text: "+"; onClicked: root.set("font_size", Math.min(32, (root.cfg.font_size || 13) + 1)) }
                    }

                    SettingRow {
                        width: parent.width
                        label: "Tab width"
                        hint: "Used when Tab inserts spaces"
                        FlatButton { text: "2"; active: (root.cfg.tab_width || 4) === 2; onClicked: root.set("tab_width", 2) }
                        FlatButton { text: "4"; active: (root.cfg.tab_width || 4) === 4; onClicked: root.set("tab_width", 4) }
                        FlatButton { text: "8"; active: (root.cfg.tab_width || 4) === 8; onClicked: root.set("tab_width", 8) }
                    }

                    SettingRow {
                        width: parent.width
                        label: "Autosave drafts"
                        hint: "Seconds between draft writes; 0 turns the safety net off"
                        FlatButton { text: "−"; onClicked: root.set("autosave_seconds", Math.max(0, (root.cfg.autosave_seconds || 0) - 1)) }
                        Text {
                            text: (root.cfg.autosave_seconds || 0) > 0 ? root.cfg.autosave_seconds + "s" : "off"
                            color: (root.cfg.autosave_seconds || 0) > 0 ? root.th.foreground : root.th.muted
                            font.pixelSize: 12
                            Layout.minimumWidth: 30
                            horizontalAlignment: Text.AlignHCenter
                        }
                        FlatButton { text: "+"; onClicked: root.set("autosave_seconds", Math.min(60, (root.cfg.autosave_seconds || 0) + 1)) }
                    }

                    Repeater {
                        model: [
                            { key: "wrap", label: "Word wrap", hint: "Line numbers hide while wrapping is on" },
                            { key: "line_numbers", label: "Line numbers", hint: "" },
                            { key: "highlight_current_line", label: "Highlight current line", hint: "" },
                            { key: "match_brackets", label: "Match brackets", hint: "" },
                            { key: "minimap", label: "Minimap", hint: "" },
                            { key: "syntax", label: "Syntax highlighting", hint: "Pygments; viewport only for speed" },
                            { key: "git_gutter", label: "Git diff gutter", hint: "Added/modified/deleted lines, from git diff against HEAD" },
                            { key: "print_colour", label: "Colour in printed output", hint: "Light syntax theme, so the page stays readable on paper" },
                            { key: "insert_spaces", label: "Insert spaces on Tab", hint: "" },
                            { key: "trim_trailing_on_save", label: "Trim trailing whitespace on save", hint: "" },
                            { key: "restore_session", label: "Restore session on start", hint: "" }
                        ]

                        SettingRow {
                            width: settingsColumn.width
                            label: modelData.label
                            hint: modelData.hint
                            ToggleSwitch {
                                checked: !!root.cfg[modelData.key]
                                onToggled: root.set(modelData.key, !root.cfg[modelData.key])
                            }
                        }
                    }

                    SettingRow {
                        width: parent.width
                        label: "Theme"
                        hint: "Follows the bar and the pywal wallpaper palette"
                        Text {
                            text: root.th.source + (root.th.theme_name ? " · " + root.th.theme_name : "")
                            color: root.th.muted
                            font.pixelSize: 11
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "hyprtk-editor " + Bridge.version
                color: Util.alpha(root.th.muted, 0.7)
                font.pixelSize: 10
            }
        }
    }
}
