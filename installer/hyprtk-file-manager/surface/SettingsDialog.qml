import QtQuick
import QtQuick.Layouts
import "../theme"
import "../config"
import "../data"
import "../components"

Item {
    id: root

    anchors.fill: parent
    visible: false
    z: 240
    focus: visible

    signal closed()
    signal contextMenuRequested()

    function open() {
        root.visible = true;
        root.forceActiveFocus();
    }

    function dismiss() {
        root.visible = false;
        Ui.close();
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
        width: Math.min(560, parent.width - 40)
        height: Math.min(620, parent.height - 40)
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 8

            Text {
                text: "Settings"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
                Layout.fillWidth: true
            }

            Text {
                text: "Applies instantly and is saved automatically."
                color: Theme.muted
                font.pixelSize: 10
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.alpha(Theme.foreground, 0.1)
            }

            Flickable {
                id: flick
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: settingsColumn.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: settingsColumn
                    width: flick.width
                    spacing: 4

                SettingRow {
                    width: parent.width
                    label: "View"

                    Segmented {
                        options: [
                            { label: "List", value: "list" },
                            { label: "Grid", value: "grid" },
                            { label: "Compact", value: "compact" }
                        ]
                        current: Config.viewMode
                        onSelected: (value) => Config.viewMode = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Icon size"

                    ValueStepper {
                        value: Config.iconSize
                        onChanged: (value) => Config.iconSize = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Sort by"

                    Segmented {
                        options: [
                            { label: "Name", value: "name" },
                            { label: "Size", value: "size" },
                            { label: "Modified", value: "mtime" },
                            { label: "Type", value: "type" }
                        ]
                        current: Config.sortKey
                        onSelected: (value) => Config.sortKey = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Descending order"

                    ToggleSwitch {
                        checked: Config.sortDesc
                        onToggled: (value) => Config.sortDesc = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Folders first"

                    ToggleSwitch {
                        checked: Config.dirsFirst
                        onToggled: (value) => Config.dirsFirst = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Show hidden files"

                    ToggleSwitch {
                        checked: Config.showHidden
                        onToggled: (value) => Config.showHidden = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Dual pane"

                    ToggleSwitch {
                        checked: Config.dualPane
                        onToggled: (value) => Config.dualPane = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Preview panel"

                    ToggleSwitch {
                        checked: Config.showPreview
                        onToggled: (value) => Config.showPreview = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Grid thumbnails"

                    ToggleSwitch {
                        checked: Config.thumbnails
                        onToggled: (value) => Config.thumbnails = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Transfers tray"

                    ToggleSwitch {
                        checked: Config.showTransfers
                        onToggled: (value) => Config.showTransfers = value
                    }
                }

                SettingRow {
                    width: parent.width
                    label: "Right-click menu"

                    DialogButton {
                        text: "Edit…"
                        onClicked: root.contextMenuRequested()
                    }
                }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 30

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "hyprtk-file-manager " + (Backend.version.length > 0 ? Backend.version : "…")
                    color: Theme.muted
                    font.pixelSize: 10
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
