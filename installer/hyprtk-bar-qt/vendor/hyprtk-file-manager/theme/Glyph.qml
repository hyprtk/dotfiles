pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    FontLoader {
        id: glyphFont
        source: "../assets/fonts/SymbolsNerdFont-Regular.ttf"
    }

    readonly property string family:
        glyphFont.status === FontLoader.Ready ? glyphFont.name : "Symbols Nerd Font"
    readonly property int size: 13

    readonly property string close: "\uf00d"
    readonly property string plus: "\uf067"
    readonly property string minus: "\uf068"
    readonly property string search: "\uf002"
    readonly property string settings: "\uf013"
    readonly property string home: "\uf015"
    readonly property string refresh: "\uf021"

    readonly property string back: "\uf060"
    readonly property string forward: "\uf061"
    readonly property string up: "\uf062"
    readonly property string down: "\uf063"
    readonly property string arrowRight: "\uf061"
    readonly property string chevronLeft: "\uf053"
    readonly property string chevronRight: "\uf054"
    readonly property string chevronUp: "\uf077"
    readonly property string chevronDown: "\uf078"

    readonly property string eye: "\uf06e"
    readonly property string eyeOff: "\uf070"
    readonly property string list: "\uf00b"
    readonly property string grid: "\uf009"
    readonly property string compact: "\uf0c9"
    readonly property string dualPane: "\uf0db"
    readonly property string preview: "\uf03e"
    readonly property string menu: "\uf142"

    readonly property string sortName: "\uf15d"
    readonly property string sortSize: "\uf160"
    readonly property string sortTime: "\uf017"
    readonly property string sortType: "\uf016"
}
