import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string uri: ""
    property string targetName: ""

    signal accepted(string uri, string username, string password, string domain, bool anonymous)
    signal cancelled()

    anchors.fill: parent
    visible: false
    z: 236

    function open(name, target) {
        root.targetName = name || target;
        root.uri = target;
        root.visible = true;
        userField.text = "";
        passField.text = "";
        domainField.text = "";
        Qt.callLater(function () { userField.input.forceActiveFocus(); });
    }

    function dismiss() {
        userField.input.focus = false;
        passField.input.focus = false;
        domainField.input.focus = false;
        root.visible = false;
        if (root.parent)
            root.parent.forceActiveFocus();
    }

    function submit() {
        const username = userField.text.trim();
        const password = passField.text;
        const domain = domainField.text.trim();
        root.dismiss();
        root.accepted(root.uri, username, password, domain, false);
    }

    function guest() {
        root.dismiss();
        root.accepted(root.uri, "", "", "", true);
    }

    function cancel() {
        root.dismiss();
        root.cancelled();
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.5

        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 480
        height: 390
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.alpha(Theme.foreground, 0.15)

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10

            Text {
                text: "Connect to network location"
                color: Theme.foreground
                font.pixelSize: 15
                font.bold: true
            }

            Text {
                width: parent.width
                text: root.targetName
                color: Theme.accent
                font.pixelSize: 12
                elide: Text.ElideMiddle
            }

            Text {
                width: parent.width
                text: root.uri
                color: Theme.muted
                font.pixelSize: 9
                elide: Text.ElideMiddle
            }

            LabeledField {
                id: userField
                width: parent.width
                label: "Username"
                placeholder: "user"
                onAccepted: root.submit()
            }

            LabeledField {
                id: passField
                width: parent.width
                label: "Password"
                placeholder: "password"
                onAccepted: root.submit()
                Component.onCompleted: input.echoMode = TextInput.Password
            }

            LabeledField {
                id: domainField
                width: parent.width
                label: "Workgroup / domain"
                placeholder: "WORKGROUP"
                onAccepted: root.submit()
            }

            Row {
                anchors.right: parent.right
                spacing: 8

                DialogButton {
                    text: "Cancel"
                    onClicked: root.cancel()
                }

                DialogButton {
                    text: "Guest"
                    onClicked: root.guest()
                }

                DialogButton {
                    text: "Connect"
                    primary: true
                    onClicked: root.submit()
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.cancel()
    }
}
