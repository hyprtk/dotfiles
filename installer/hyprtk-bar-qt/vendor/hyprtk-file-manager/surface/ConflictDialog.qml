import QtQuick
import "../theme"
import "../data"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: Jobs.currentConflict !== null
    z: 230

    property bool applyAll: false

    signal finished()

    function decide(decision) {
        const all = root.applyAll;
        root.applyAll = false;
        Jobs.resolve(decision, all);
        root.finished();
    }

    function cancelJob() {
        Jobs.cancelConflict();
        root.finished();
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 470
        height: 248
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Text {
                text: "File exists"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: Jobs.currentConflict ? Jobs.currentConflict.conflict.name : ""
                color: Theme.accent
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }

            Text {
                width: parent.width
                text: "An item with this name already exists in the destination."
                color: Theme.muted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            Rectangle {
                width: 140
                height: 24
                radius: 5
                color: root.applyAll ? Theme.alpha(Theme.accent, 0.32) : Theme.alpha(Theme.foreground, 0.06)

                Text {
                    anchors.centerIn: parent
                    text: "Apply to all"
                    color: Theme.foreground
                    font.pixelSize: 11
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.applyAll = !root.applyAll
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Replace"
                    primary: true
                    onClicked: root.decide("replace")
                }
                DialogButton {
                    text: "Skip"
                    onClicked: root.decide("skip")
                }
                DialogButton {
                    text: "Keep both"
                    onClicked: root.decide("keep-both")
                }
                DialogButton {
                    text: "Cancel job"
                    danger: true
                    onClicked: root.cancelJob()
                }
            }

            Text {
                text: "R replace · S skip · K keep both · A apply to all"
                color: Theme.alpha(Theme.foreground, 0.45)
                font.pixelSize: 10
            }
        }
    }

    Shortcut {
        sequence: "R"
        enabled: root.visible
        onActivated: root.decide("replace")
    }
    Shortcut {
        sequence: "S"
        enabled: root.visible
        onActivated: root.decide("skip")
    }
    Shortcut {
        sequence: "K"
        enabled: root.visible
        onActivated: root.decide("keep-both")
    }
    Shortcut {
        sequence: "A"
        enabled: root.visible
        onActivated: root.applyAll = !root.applyAll
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.cancelJob()
    }
}
