import QtQuick
import "../theme"

Item {
    id: root

    property string path: ""
    property bool editing: false

    signal navigate(string path)

    implicitHeight: 28

    function segments() {
        const value = root.path || "/";
        const parts = value.split("/").filter(function (part) { return part.length > 0; });
        const out = [];
        if (value.charAt(0) === "/")
            out.push({ label: "/", path: "/" });
        let acc = "";
        for (let i = 0; i < parts.length; i++) {
            acc += "/" + parts[i];
            out.push({ label: parts[i], path: acc });
        }
        return out;
    }

    function startEdit() {
        root.editing = true;
        field.text = root.path;
        field.forceActiveFocus();
        field.selectAll();
    }

    function stopEdit() {
        root.editing = false;
        field.focus = false;
        if (root.parent)
            root.parent.forceActiveFocus();
    }

    function revealTail() {
        flick.contentX = Math.max(0, flick.contentWidth - flick.width);
    }

    onPathChanged: Qt.callLater(root.revealTail)
    onWidthChanged: Qt.callLater(root.revealTail)

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.alpha(Theme.foreground, 0.06)
        visible: !root.editing

        Flickable {
            id: flick
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            contentWidth: crumbRow.width
            contentHeight: height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            onContentWidthChanged: Qt.callLater(root.revealTail)

            Row {
                id: crumbRow
                height: parent.height

                Repeater {
                    model: root.segments()

                    delegate: Row {
                        id: segment
                        required property var modelData
                        required property int index
                        height: crumbRow.height

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: segment.modelData.label
                            color: crumbHover.hovered ? Theme.accent : Theme.foreground
                            font.pixelSize: Theme.fontSize

                            MouseArea {
                                id: crumbHover
                                anchors.fill: parent
                                anchors.margins: -4
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.navigate(segment.modelData.path)
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: segment.index < root.segments().length - 1
                            text: "›"
                            color: Theme.alpha(Theme.foreground, 0.35)
                            font.pixelSize: Theme.fontSize
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.accent
        visible: root.editing

        TextInput {
            id: field
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.foreground
            selectionColor: Theme.accent
            selectedTextColor: Theme.textOnAccent
            font.pixelSize: Theme.fontSize
            onAccepted: {
                root.navigate(text);
                root.stopEdit();
            }
            Keys.onEscapePressed: root.stopEdit()
        }
    }
}
