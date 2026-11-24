// Users: the account list plus an inline create form. Passwords are collected
// in a modal (App) and sent once; they are never stored.
import QtQuick
import "../../theme"
import "../../components"

Flickable {
    id: page

    property var model: ({})
    property string panelId: "users"
    property var pending: ({})

    signal change(string panelId, string key, var value)
    signal invoke(string panelId, var action)
    signal browse(string panelId, string key, string mode, string value)

    contentWidth: width
    contentHeight: content.height
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    property var accounts: model.accounts || []
    property var shells: model.shells || []

    property string newName: ""
    property string newFullname: ""
    property string newPassword: ""
    property string newGroups: ""
    property string newShell: model.defaultShell || (shells.length > 0 ? shells[0] : "/bin/sh")
    property bool newAdmin: false
    readonly property bool canCreate:
        /^[a-z_][a-z0-9_-]{0,31}$/.test(page.newName) &&
        page.newPassword.length > 0 &&
        page.newShell.length > 0

    function create() {
        if (!page.canCreate)
            return;
        page.invoke("users", {
            action: "users.create",
            args: {
                username: page.newName,
                fullname: page.newFullname,
                password: page.newPassword,
                groups: page.newGroups,
                shell: page.newShell,
                admin: page.newAdmin,
            },
        });
        page.newName = "";
        page.newFullname = "";
        page.newPassword = "";
        page.newGroups = "";
    }

    Item {
        id: content
        width: page.width
        height: column.implicitHeight + 40

        Column {
            id: column
            x: 16
            y: 20
            width: parent.width - 32
            spacing: 10

            SectionCard {
                width: column.width
                title: "Accounts"
                description: "Local accounts on this machine. Locking and passwords need administrator authentication."

                ListBlock {
                    width: parent.width
                    items: page.accounts
                    onInvoke: (action) => page.invoke("users", action)
                }
            }

            SectionCard {
                width: column.width
                title: "Add an account"
                description: "Creates a home directory and sets the password in one step."

                SettingRow {
                    label: "User name"
                    help: "Lowercase letters, digits, underscore or dash."
                    TTextField {
                        id: nameField
                        preferredWidth: 220
                        placeholder: "e.g. kori"
                        text: page.newName
                        invalid: page.newName.length > 0 &&
                                 !/^[a-z_][a-z0-9_-]{0,31}$/.test(page.newName)
                        onEdited: (v) => page.newName = v
                    }
                    Connections {
                        target: page
                        function onNewNameChanged() {
                            if (nameField.text !== page.newName)
                                nameField.text = page.newName;
                        }
                    }
                }
                SettingRow {
                    label: "Full name"
                    help: "Shown in login screens and account lists."
                    TTextField {
                        id: fullnameField
                        preferredWidth: 220
                        placeholder: "optional"
                        text: page.newFullname
                        onEdited: (v) => page.newFullname = v
                    }
                    Connections {
                        target: page
                        function onNewFullnameChanged() {
                            if (fullnameField.text !== page.newFullname)
                                fullnameField.text = page.newFullname;
                        }
                    }
                }
                SettingRow {
                    label: "Password"
                    help: "Sent to chpasswd on stdin, never logged."
                    TTextField {
                        id: passwordField
                        preferredWidth: 220
                        echoMode: TextInput.Password
                        text: page.newPassword
                        onEdited: (v) => page.newPassword = v
                    }
                    Connections {
                        target: page
                        function onNewPasswordChanged() {
                            if (passwordField.text !== page.newPassword)
                                passwordField.text = page.newPassword;
                        }
                    }
                }
                SettingRow {
                    label: "Login shell"
                    Dropdown {
                        preferredWidth: 220
                        value: page.newShell
                        choices: page.shells.map(s => ({ value: s, label: s }))
                        onSelected: (v) => page.newShell = v
                    }
                }
                SettingRow {
                    label: "Administrator"
                    help: "Adds the account to the wheel group."
                    ToggleSwitch {
                        checked: page.newAdmin
                        onToggled: (v) => page.newAdmin = v
                    }
                }
                SettingRow {
                    label: "Extra groups"
                    help: "Comma-separated, e.g. audio,video."
                    TTextField {
                        id: groupsField
                        preferredWidth: 220
                        placeholder: "optional"
                        text: page.newGroups
                        onEdited: (v) => page.newGroups = v
                    }
                    Connections {
                        target: page
                        function onNewGroupsChanged() {
                            if (groupsField.text !== page.newGroups)
                                groupsField.text = page.newGroups;
                        }
                    }
                }
                Row {
                    width: parent.width
                    topPadding: 6
                    Item { width: parent.width - createButton.width - 8; height: 1 }
                    TButton {
                        id: createButton
                        text: "Create account"
                        primary: true
                        enabled: page.canCreate
                        onClicked: page.create()
                    }
                }
            }

            SectionCard {
                width: column.width
                title: "Applied with"
                description: ""
                RowView {
                    width: parent.width
                    panelId: page.panelId
                    rowData: ({ type: "note", tone: "info",
                        text: "useradd, usermod, gpasswd and chpasswd through pkexec. " +
                              "Deleting an account removes its home directory and cannot be undone." })
                }
            }
        }
    }
}
