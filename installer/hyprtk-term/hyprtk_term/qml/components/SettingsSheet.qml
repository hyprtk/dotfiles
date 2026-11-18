import QtQuick
import "../theme"
import "../theme/util.js" as Util

// The v0.1 settings sheet. Deliberately stepper-based: no dropdowns, no
// sliders, nothing that needs its own styling pass. Every edit goes through
// Bridge.setConfig so the running tabs update live.
Rectangle {
    id: sheet

    property var theme
    property var cfg
    property var fonts: []
    property int alpha: 0
    signal closed()

    anchors.fill: parent
    color: Util.alpha(theme.background, 0.55 * (alpha / 255))
    visible: alpha > 0

    MouseArea {
        anchors.fill: parent
        onClicked: sheet.closed()
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: 420
        height: content.implicitHeight + 40
        radius: 14
        color: Util.alpha(theme.background, 0.98)
        border.width: 1
        border.color: Util.alpha(theme.accent, 0.35)
        opacity: sheet.alpha / 255

        MouseArea { anchors.fill: parent }

        Column {
            id: content
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Row {
                width: parent.width
                spacing: 8
                Text {
                    text: Glyph.settings
                    font.family: Glyph.family
                    font.pixelSize: 13
                    color: sheet.theme.accent
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "Terminal settings"
                    color: sheet.theme.foreground
                    font.pixelSize: 14
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Stepper {
                width: parent.width
                label: "Font"
                value: sheet.cfg.font_family
                onStep: function (dir) {
                    var list = sheet.fonts.length ? sheet.fonts : [sheet.cfg.font_family];
                    var i = Math.max(0, list.indexOf(sheet.cfg.font_family));
                    i = (i + dir + list.length) % list.length;
                    Bridge.setConfig("font_family", list[i]);
                }
            }

            Stepper {
                width: parent.width
                label: "Size"
                value: Number(sheet.cfg.font_size).toFixed(1) + " pt"
                onStep: function (dir) {
                    Bridge.setConfig("font_size",
                        Math.max(4, Math.min(28, Number(sheet.cfg.font_size) + dir * 0.5)));
                }
            }

            Stepper {
                width: parent.width
                label: "Opacity"
                value: Math.round(sheet.cfg.opacity * 100) + "%"
                onStep: function (dir) {
                    Bridge.setConfig("opacity",
                        Math.max(0.4, Math.min(1, Number(sheet.cfg.opacity) + dir * 0.02)));
                }
            }

            Stepper {
                width: parent.width
                label: "Scrollback"
                value: sheet.cfg.scrollback + " lines"
                onStep: function (dir) {
                    var v = Number(sheet.cfg.scrollback);
                    v = dir > 0 ? (v < 1000 ? v + 1000 : v + 5000) : Math.max(0, v - (v > 5000 ? 5000 : 1000));
                    Bridge.setConfig("scrollback", v);
                }
            }

            Stepper {
                width: parent.width
                label: "Cursor blink"
                value: sheet.cfg.cursor_blink ? "on" : "off"
                onStep: function () { Bridge.setConfig("cursor_blink", !sheet.cfg.cursor_blink); }
            }

            Stepper {
                width: parent.width
                label: "Copy on select"
                value: sheet.cfg.copy_on_select ? "on" : "off"
                onStep: function () { Bridge.setConfig("copy_on_select", !sheet.cfg.copy_on_select); }
            }

            Column {
                width: parent.width
                spacing: 4
                Text {
                    text: "Shell"
                    color: Util.alpha(sheet.theme.muted, 0.95)
                    font.pixelSize: 11
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    radius: 7
                    color: Util.alpha(sheet.theme.surface, 0.9)
                    border.width: 1
                    border.color: shellInput.activeFocus ? Util.alpha(sheet.theme.accent, 0.7)
                                                         : Util.alpha(sheet.theme.border, 0.5)
                    TextInput {
                        id: shellInput
                        anchors.fill: parent
                        anchors.leftMargin: 9
                        anchors.rightMargin: 9
                        verticalAlignment: TextInput.AlignVCenter
                        color: sheet.theme.foreground
                        selectionColor: Util.alpha(sheet.theme.accent2, 0.5)
                        selectedTextColor: sheet.theme.background
                        font.family: sheet.cfg.font_family
                        font.pixelSize: 12
                        text: sheet.cfg.shell
                        onEditingFinished: Bridge.setConfig("shell", text)
                    }
                }
                Text {
                    text: "Blank uses $SHELL (" + Bridge.defaultShell() + "). Applies to new tabs."
                    color: Util.alpha(sheet.theme.muted, 0.6)
                    font.pixelSize: 10
                    width: parent.width
                    wrapMode: Text.Wrap
                }
            }

            Row {
                width: parent.width
                spacing: 10
                anchors.right: parent.right
                layoutDirection: Qt.RightToLeft

                Pill {
                    label: "Done"
                    primary: true
                    onClicked: { Bridge.saveConfig(); sheet.closed(); }
                }
                Pill {
                    label: "Reset"
                    onClicked: Bridge.resetConfig()
                }
            }
        }
    }

    component Stepper: Row {
        property string label: ""
        property string value: ""
        signal step(int direction)

        width: parent.width
        spacing: 8

        Text {
            width: parent.width - 132
            text: label
            color: Util.alpha(sheet.theme.muted, 0.95)
            font.pixelSize: 11
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideRight
        }
        Text {
            width: 96
            text: value
            color: sheet.theme.foreground
            font.family: sheet.cfg.font_family
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideRight
        }
        Pill {
            label: "\u2212"
            width: 26
            onClicked: parent.step(-1)
        }
        Pill {
            label: "+"
            width: 26
            onClicked: parent.step(1)
        }
    }

    component Pill: Rectangle {
        property string label: ""
        property bool primary: false
        signal clicked()

        width: primary ? 74 : 62
        height: 26
        radius: 7
        color: area.containsMouse
               ? Util.alpha(primary ? sheet.theme.accent : sheet.theme.surface_alt, 0.95)
               : Util.alpha(primary ? sheet.theme.accent : sheet.theme.surface, primary ? 0.90 : 0.85)
        border.width: 1
        border.color: Util.alpha(primary ? sheet.theme.accent : sheet.theme.border, 0.5)

        Text {
            anchors.centerIn: parent
            text: parent.label
            font.pixelSize: 11
            font.bold: parent.primary
            color: parent.primary ? sheet.theme.text_on_accent : sheet.theme.foreground
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
