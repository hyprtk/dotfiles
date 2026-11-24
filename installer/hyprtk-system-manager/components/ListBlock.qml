// Rows with badges and inline actions, in the bar's module-card language.
import QtQuick
import "../theme"

Column {
    id: root

    property var items: []
    signal invoke(var action)

    width: parent ? parent.width : 0
    spacing: 4

    Repeater {
        model: root.items

        delegate: Rectangle {
            id: row
            required property var modelData

            width: root.width
            height: Math.max(44, textColumn.implicitHeight + 14)
            radius: Theme.radiusCard
            color: Theme.cardFill
            border.width: 1
            border.color: Theme.cardBorder

            Column {
                id: textColumn
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.right: actions.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Row {
                    spacing: 6
                    Text {
                        text: row.modelData.title || ""
                        color: Theme.foreground
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.size(2)
                        font.bold: true
                    }
                    Repeater {
                        model: row.modelData.badges || []
                        delegate: StatusPill {
                            required property var modelData
                            text: String(modelData)
                            tone: String(modelData) === "running" ? "ok"
                                : String(modelData) === "disabled" ? "warn"
                                : String(modelData) === "danger" ? "danger"
                                : "neutral"
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: (row.modelData.subtitle || "").length > 0
                    text: row.modelData.subtitle || ""
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(0)
                    elide: Text.ElideRight
                }
            }

            Row {
                id: actions
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 5

                Repeater {
                    model: row.modelData.actions || []
                    delegate: TButton {
                        required property var modelData
                        text: modelData.label || "Run"
                        small: true
                        danger: modelData.variant === "danger"
                        primary: modelData.variant === "primary"
                        onClicked: root.invoke(modelData)
                    }
                }
            }
        }
    }

    Text {
        visible: root.items.length === 0
        text: "Nothing here."
        color: Theme.dim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.size(2)
    }
}
