import QtQuick
import "../theme"
import "../config"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 242
    focus: visible

    property var catalog: []
    property var order: []
    property var hidden: []

    signal closed()

    function open(items) {
        root.catalog = items || [];
        root.order = root.effectiveOrder();
        root.hidden = (Config.hiddenMenuItems || []).slice();
        root.visible = true;
        Qt.callLater(function () { itemList.forceActiveFocus(); });
    }

    function effectiveOrder() {
        const keys = root.catalog.map(function (item) { return item.key; });
        const saved = Config.menuOrder || [];
        const out = saved.filter(function (key) { return keys.indexOf(key) >= 0; });
        for (let i = 0; i < keys.length; i++) {
            if (out.indexOf(keys[i]) < 0)
                out.push(keys[i]);
        }
        return out;
    }

    function labelFor(key) {
        for (let i = 0; i < root.catalog.length; i++) {
            if (root.catalog[i].key === key)
                return root.catalog[i].label;
        }
        return key;
    }

    function isHidden(key) {
        return root.hidden.indexOf(key) >= 0;
    }

    function persist() {
        Config.menuOrder = root.order;
        Config.hiddenMenuItems = root.hidden;
    }

    function setHidden(key, hide) {
        const next = root.hidden.slice();
        const index = next.indexOf(key);
        if (hide && index < 0)
            next.push(key);
        else if (!hide && index >= 0)
            next.splice(index, 1);
        root.hidden = next;
        root.persist();
    }

    function move(key, delta) {
        const from = root.order.indexOf(key);
        const to = from + delta;
        if (from < 0 || to < 0 || to >= root.order.length)
            return;
        const next = root.order.slice();
        next[from] = next[to];
        next[to] = key;
        root.order = next;
        root.persist();
    }

    function reset() {
        root.order = root.catalog.map(function (item) { return item.key; });
        root.hidden = [];
        Config.menuOrder = [];
        Config.hiddenMenuItems = [];
    }

    function dismiss() {
        root.visible = false;
        if (root.parent)
            root.parent.forceActiveFocus();
        root.closed();
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.45

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 520
        height: 560
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 8

            Text {
                text: "Right-click menu"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: "Show, hide and reorder the items in the file context menu."
                color: Theme.muted
                font.pixelSize: 10
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.alpha(Theme.foreground, 0.1)
            }

            Rectangle {
                width: parent.width
                height: 384
                radius: 8
                color: Theme.alpha(Theme.foreground, 0.04)
                border.width: 1
                border.color: Theme.alpha(Theme.foreground, 0.1)
                clip: true

                ListView {
                    id: itemList
                    anchors.fill: parent
                    anchors.margins: 4
                    model: root.order
                    spacing: 2
                    boundsBehavior: Flickable.StopAtBounds
                    focus: true

                    Keys.onEscapePressed: root.dismiss()

                    delegate: Item {
                        required property string modelData
                        required property int index

                        width: itemList.width
                        height: 34

                        Rectangle {
                            anchors.fill: parent
                            radius: 6
                            color: rowHover.hovered ? Theme.alpha(Theme.foreground, 0.06) : "transparent"
                        }

                        ToggleSwitch {
                            id: shownSwitch
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            checked: !root.isHidden(modelData)
                            onToggled: (value) => root.setHidden(modelData, !value)
                        }

                        Text {
                            anchors.left: shownSwitch.right
                            anchors.leftMargin: 10
                            anchors.right: upButton.left
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.labelFor(modelData)
                            color: root.isHidden(modelData) ? Theme.muted : Theme.foreground
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }

                        IconButton {
                            id: upButton
                            anchors.right: downButton.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: Glyph.up
                            hint: "Move up"
                            iconSize: 11
                            implicitWidth: 26
                            available: index > 0
                            onClicked: root.move(modelData, -1)
                        }

                        IconButton {
                            id: downButton
                            anchors.right: parent.right
                            anchors.rightMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            text: Glyph.down
                            hint: "Move down"
                            iconSize: 11
                            implicitWidth: 26
                            available: index < root.order.length - 1
                            onClicked: root.move(modelData, 1)
                        }

                        MouseArea {
                            id: rowHover
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.NoButton
                        }
                    }
                }
            }

            Item { width: 1; height: 2 }

            Item {
                width: parent.width
                height: 30

                DialogButton {
                    anchors.left: parent.left
                    text: "Reset"
                    onClicked: root.reset()
                }

                DialogButton {
                    anchors.right: parent.right
                    text: "Done"
                    primary: true
                    onClicked: root.dismiss()
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.dismiss()
    }
}
