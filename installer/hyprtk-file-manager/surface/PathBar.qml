import QtQuick
import Quickshell
import "../theme"

Item {
    id: root

    property string path: ""
    property bool editing: false

    signal navigate(string path)

    readonly property string homePath: Quickshell.env("HOME") || ""

    implicitHeight: 28

    function lastSegment(value) {
        const trimmed = (value || "").replace(/\/+$/, "");
        return trimmed.slice(trimmed.lastIndexOf("/") + 1) || "/";
    }

    function mountRoot(value) {
        let match = value.match(/^(\/run\/media\/[^/]+\/[^/]+)(?:\/|$)/);
        if (match)
            return match[1];
        match = value.match(/^(\/media\/[^/]+)(?:\/|$)/);
        if (match)
            return match[1];
        match = value.match(/^(\/mnt\/[^/]+)(?:\/|$)/);
        if (match)
            return match[1];
        return "";
    }

    function appendSegments(out, base, rest) {
        let acc = base.replace(/\/+$/, "");
        for (let i = 0; i < rest.length; i++) {
            acc += "/" + rest[i];
            out.push({ label: rest[i], path: acc });
        }
    }

    function tail(value, base) {
        if (value === base)
            return [];
        return value.slice(base.length + 1).split("/").filter(function (part) {
            return part.length > 0;
        });
    }

    function segments() {
        const value = root.path || "/";
        const out = [];
        const home = root.homePath;
        if (home && (value === home || value.indexOf(home + "/") === 0)) {
            out.push({ label: "Home", path: home });
            root.appendSegments(out, home, root.tail(value, home));
            return out;
        }
        const mount = root.mountRoot(value);
        if (mount) {
            out.push({ label: root.lastSegment(mount), path: mount });
            root.appendSegments(out, mount, root.tail(value, mount));
            return out;
        }
        const parts = value.split("/").filter(function (part) { return part.length > 0; });
        if (value.charAt(0) === "/")
            out.push({ label: "/", path: "/" });
        root.appendSegments(out, "/", parts);
        return out;
    }

    function editableText() {
        const value = root.path || "/";
        const home = root.homePath;
        if (home && value === home)
            return "~";
        if (home && value.indexOf(home + "/") === 0)
            return "~/" + value.slice(home.length + 1);
        return value;
    }

    function startEdit() {
        root.editing = true;
        field.text = root.editableText();
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

        MouseArea {
            z: -1
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.IBeamCursor
            onClicked: root.startEdit()
        }

        Flickable {
            id: flick
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            contentWidth: crumbRow.width
            contentHeight: height
            clip: true
            interactive: contentWidth > width
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
