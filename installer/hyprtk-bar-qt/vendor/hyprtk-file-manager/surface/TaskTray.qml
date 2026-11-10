import QtQuick
import "../theme"
import "../config"
import "../data"
import "../components"

Rectangle {
    id: root

    visible: Config.showTransfers && Jobs.jobs.length > 0
    height: visible ? 96 : 0
    color: Theme.alpha(Theme.surface, 0.55)

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Row {
            width: parent.width
            height: 18
            spacing: 8

            Text {
                text: "Transfers" + (Jobs.activeCount > 0 ? " · " + Jobs.activeCount + " active" : "")
                color: Theme.accent
                font.pixelSize: 10
                font.bold: true
            }

            Item {
                width: parent.width - 290
                height: 1
            }

            Text {
                text: "Hide"
                color: Theme.muted
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Config.showTransfers = false
                }
            }

            Text {
                text: "Clear"
                color: Theme.muted
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Jobs.clearFinished()
                }
            }
        }

        Repeater {
            model: Jobs.jobs.slice(0, 3)

            delegate: Rectangle {
                required property var modelData
                width: parent.width
                height: 20
                color: "transparent"

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 90
                    text: Jobs.label(modelData.kind)
                    color: Theme.foreground
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: 96
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 190
                    height: 6
                    radius: 3
                    color: Theme.alpha(Theme.foreground, 0.12)

                    Rectangle {
                        width: parent.width * (modelData.total > 0
                            ? Math.min(1, modelData.done / modelData.total)
                            : (modelData.state === "done" ? 1 : 0.15))
                        height: parent.height
                        radius: 3
                        color: (modelData.state === "failed" || (modelData.errors && modelData.errors.length))
                            ? Theme.danger : Theme.accent
                    }
                }

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.done + "/" + modelData.total
                        + (modelData.errors && modelData.errors.length ? "  !" + modelData.errors.length : "")
                    color: (modelData.errors && modelData.errors.length) ? Theme.danger : Theme.muted
                    font.pixelSize: 10
                }

                IconButton {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 18
                    height: 18
                    text: "×"
                    available: modelData.state === "running" || modelData.state === "queued"
                    onClicked: Jobs.cancel(modelData.id)
                }
            }
        }
    }
}
