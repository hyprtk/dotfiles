// Colour value: swatch, hex field and a palette popup built from the live pywal
// colours so a manual accent can still match the wallpaper.
import QtQuick
import QtQuick.Controls
import "../theme"

Row {
    id: root

    property string value: "#c084fc"
    property int preferredWidth: 200
    signal edited(string value)

    spacing: 6

    Rectangle {
        id: swatch
        width: 30; height: 30; radius: Theme.radiusControl
        color: Theme.isHex(root.value) ? root.value : Theme.accent
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.25)
        HoverHandler { id: swatchHover }
        TapHandler { onTapped: popup.visible ? popup.close() : popup.open() }
    }

    TTextField {
        id: field
        preferredWidth: root.preferredWidth - 40
        mono: true
        text: root.value
        onEdited: (v) => { if (Theme.isHex(v)) root.edited(v); }
        onCommitted: (v) => { if (Theme.isHex(v)) root.edited(v); else field.text = root.value; }
    }

    Popup {
        id: popup
        parent: swatch
        x: 0
        y: swatch.height + 4
        width: 220
        padding: 8
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.radiusCard
            color: Theme.background
            border.width: 1
            border.color: Theme.alpha(Theme.accent2, 0.35)
        }

        contentItem: Grid {
            columns: 8
            spacing: 4
            Repeater {
                model: {
                    const out = [];
                    for (let i = 1; i <= 16; i++) {
                        const c = Theme.colors["color" + i];
                        if (Theme.isHex(c)) out.push(c);
                    }
                    if (Theme.isHex(Theme.special.background)) out.push(Theme.special.background);
                    if (Theme.isHex(Theme.special.foreground)) out.push(Theme.special.foreground);
                    return out;
                }
                delegate: Rectangle {
                    required property string modelData
                    width: 22; height: 22; radius: 5
                    color: modelData
                    border.width: String(modelData).toLowerCase() === String(root.value).toLowerCase() ? 2 : 1
                    border.color: Theme.foreground
                    HoverHandler { id: dotHover }
                    TapHandler {
                        onTapped: {
                            root.edited(modelData);
                            field.text = modelData;
                            popup.close();
                        }
                    }
                }
            }
        }
    }
}
