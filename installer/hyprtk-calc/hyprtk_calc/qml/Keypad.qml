import QtQuick
import QtQuick.Layouts
import "theme"
import "theme/util.js" as Util
import "components"

// The keypad for one mode, laid out as a flat list of four-column rows.
//
// The model is a plain JS array: every delegate is stateless, so the
// destroy-and-recreate on a mode change costs nothing and clicking is never
// interrupted (there is no grab and no animation to lose).
Item {
    id: pad

    property var th: null
    property string mode: "basic"
    property real fontScale: 1.0

    signal token(string text)
    signal action(string name)

    implicitHeight: grid.implicitHeight

    readonly property var keys: {
        var basic = [
            { l: "AC", a: "clear", s: 1 }, { l: "DEL", a: "back" },
            { l: "%", t: "%" }, { l: "÷", t: "/", accent: true },
            { l: "7", t: "7" }, { l: "8", t: "8" }, { l: "9", t: "9" },
            { l: "×", t: "*", accent: true },
            { l: "4", t: "4" }, { l: "5", t: "5" }, { l: "6", t: "6" },
            { l: "−", t: "-", accent: true },
            { l: "1", t: "1" }, { l: "2", t: "2" }, { l: "3", t: "3" },
            { l: "+", t: "+", accent: true },
            { l: "±", a: "sign" }, { l: "0", t: "0" }, { l: ".", t: "." },
            { l: "=", a: "equals", accent: true, solid: true }
        ];

        var scientific = [
            { l: "sin", t: "sin(" }, { l: "cos", t: "cos(" },
            { l: "tan", t: "tan(" }, { l: "π", t: "pi" },
            { l: "ln", t: "ln(" }, { l: "log", t: "log(" },
            { l: "√", t: "sqrt(" }, { l: "xʸ", t: "^", accent: true },
            { l: "(", t: "(" }, { l: ")", t: ")" },
            { l: "x²", t: "^2" }, { l: "e", t: "e" }
        ];

        var programmer = [
            { l: "A", a: "hex:A" }, { l: "B", a: "hex:B" },
            { l: "C", a: "hex:C" }, { l: "D", a: "hex:D" },
            { l: "E", a: "hex:E" }, { l: "F", a: "hex:F" },
            { l: "<<", t: "<<", accent: true }, { l: ">>", t: ">>", accent: true },
            { l: "&", t: "&", accent: true }, { l: "|", t: "|", accent: true },
            { l: "xor", t: " xor " , accent: true }, { l: "~", t: "~", accent: true }
        ];

        if (mode === "scientific")
            return scientific.concat(basic);
        if (mode === "programmer")
            return programmer.concat(basic);
        return basic;
    }

    GridLayout {
        id: grid
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        columns: 4
        columnSpacing: 8
        rowSpacing: 8

        Repeater {
            model: pad.keys
            delegate: CalcKey {
                id: keyItem

                required property var modelData

                th: pad.th
                fontScale: pad.fontScale
                label: modelData.l
                token: modelData.t || ""
                action: modelData.a || ""
                accent: modelData.accent === true
                solid: modelData.solid === true
                soft: modelData.a === "clear" || modelData.a === "back"
                Layout.fillHeight: true
                Layout.preferredHeight: 50 * pad.fontScale
                Layout.columnSpan: modelData.s || 1
                onActivated: {
                    if (keyItem.token)
                        pad.token(keyItem.token);
                    else if (keyItem.action)
                        pad.action(keyItem.action);
                }
            }
        }
    }
}
