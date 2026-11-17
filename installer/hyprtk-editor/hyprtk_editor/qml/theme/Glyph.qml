pragma Singleton

import QtQuick

// The suite's Symbols Nerd Font, so the editor's chrome reads like the bar's.
QtObject {
    id: root

    property FontLoader glyphFont: FontLoader {
        source: "../../assets/fonts/SymbolsNerdFont-Regular.ttf"
    }

    readonly property string family:
        glyphFont.status === FontLoader.Ready ? glyphFont.name : "Symbols Nerd Font"
    readonly property int size: 13

    readonly property string close: "\uf00d"
    readonly property string plus: "\uf067"
    readonly property string search: "\uf002"
    readonly property string settings: "\uf013"
    readonly property string menu: "\uf142"
    readonly property string chevronDown: "\uf078"
    readonly property string chevronUp: "\uf077"
    readonly property string arrowLeft: "\uf060"
    readonly property string arrowRight: "\uf061"
    readonly property string file: "\uf15b"
    readonly property string folder: "\uf07b"
    readonly property string save: "\uf0c7"
    readonly property string undo: "\uf0e2"
    readonly property string redo: "\uf01e"
    readonly property string palette: "\uf53f"
    readonly property string terminal: "\uf120"
    readonly property string warning: "\uf071"
    readonly property string check: "\uf00c"
    readonly property string dot: "\uf111"
}
