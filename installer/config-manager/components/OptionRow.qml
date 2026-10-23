// One settings row in the bar-qt style: fixed label column, control beside it.
import QtQuick
import QtQuick.Layouts
import "../theme"

RowLayout {
    id: root
    property var opt: ({})
    property var value
    property bool pending: false
    signal changed(var value)

    readonly property var current: value !== undefined ? value : opt.default

    spacing: 8
    implicitHeight: Theme.controlHeight

    Text {
        Layout.preferredWidth: 170
        Layout.alignment: Qt.AlignVCenter
        text: root.opt.label || root.opt.path || ""
        color: root.pending ? Theme.accent2 : Theme.foreground
        font.pixelSize: Theme.scaled(12)
        elide: Text.ElideRight
    }

    TCheckBox {
        visible: root.opt.type === "bool"
        Layout.alignment: Qt.AlignVCenter
        checked: root.current === true
        onToggled: v => root.changed(v)
    }

    TSpinBox {
        visible: root.opt.type === "int" || root.opt.type === "float"
        Layout.preferredWidth: 120
        Layout.alignment: Qt.AlignVCenter
        from: root.opt.min !== undefined ? root.opt.min : 0
        to: root.opt.max !== undefined ? root.opt.max : 1000
        step: root.opt.step !== undefined ? root.opt.step : 1
        decimals: root.opt.type === "float" ? 2 : 0
        value: Number(root.current) || 0
        onModified: v => root.changed(v)
    }

    TComboBox {
        visible: root.opt.type === "enum"
        Layout.preferredWidth: 180
        Layout.alignment: Qt.AlignVCenter
        model: root.opt.choices || []
        currentIndex: (root.opt.choices || []).indexOf(String(root.current))
        onActivated: i => root.changed(model[i])
    }

    TTextField {
        visible: root.opt.type === "str" || root.opt.type === "color"
        Layout.preferredWidth: 200
        Layout.alignment: Qt.AlignVCenter
        text: root.current === undefined || root.current === null ? "" : String(root.current)
        onEdited: v => root.changed(v)
    }

    Item { Layout.fillWidth: true }
}
