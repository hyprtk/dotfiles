pragma Singleton

import QtQuick

// The suite's Symbols Nerd Font, so the calculator's chrome reads like the
// bar's. Glyph codes are from the Symbols Nerd Font cheat sheet.
QtObject {
    id: root

    property FontLoader glyphFont: FontLoader {
        source: "../../assets/fonts/SymbolsNerdFont-Regular.ttf"
    }

    readonly property string family:
        glyphFont.status === FontLoader.Ready ? glyphFont.name : "Symbols Nerd Font"
    readonly property int size: 13

    readonly property string close: "\uf00d"
    readonly property string settings: "\uf013"
    readonly property string history: "\uf1da"
    readonly property string copy: "\uf0c5"
    readonly property string backspace: "\u232b"
    readonly property string trash: "\uf2ed"
    readonly property string left: "\uf060"
    readonly property string right: "\uf061"
    readonly property string up: "\uf077"
    readonly property string down: "\uf078"
    readonly property string check: "\uf00c"
    readonly property string memory: "\uf538"
    readonly property string dot: "\uf111"
}
