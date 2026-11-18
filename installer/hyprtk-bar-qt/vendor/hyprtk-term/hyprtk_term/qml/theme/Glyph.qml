pragma Singleton

import QtQuick

// The suite's Symbols Nerd Font, so the terminal's chrome reads like the bar's.
QtObject {
    id: root

    property FontLoader glyphFont: FontLoader {
        source: "../../assets/fonts/SymbolsNerdFont-Regular.ttf"
    }

    readonly property string family:
        glyphFont.status === FontLoader.Ready ? glyphFont.name : "Symbols Nerd Font"
    readonly property int size: 12

    readonly property string close: "\uf00d"
    readonly property string plus: "\uf067"
    readonly property string terminal: "\uf120"
    readonly property string settings: "\uf013"
    readonly property string chevronDown: "\uf078"
    readonly property string chevronUp: "\uf077"
    readonly property string dot: "\uf111"
    readonly property string search: "\uf002"
    readonly property string arrowDown: "\uf063"
    readonly property string check: "\uf00c"
    readonly property string copy: "\uf0c5"
    readonly property string paste: "\uf0ea"
    readonly property string broom: "\uf12d"
}
