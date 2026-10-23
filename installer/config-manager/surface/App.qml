// Shared settings contents: sidebar + page stack + footer.
// Used by the standalone FloatingWindow (Main.qml) and the layer-shell overlay
// opened from hyprtk-bar-qt (Overlay.qml). Talks to the Python backend over the
// JSON-lines RPC (config_manager.cli serve).
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import "../theme"
import "../config"
import "../components"
import "pages"

Item {
    id: app

    property var model: ({})
    property var schemaData: ({})
    property var barValues: ({})
    property var pending: ({})
    property var targetModel: ({})
    property string targetFile: ""
    property string status: "connecting…"
    property int reqId: 0
    property var inflight: ({})
    property bool busy: false
    property real reveal: 0
    readonly property bool dirty: pendingCount > 0

    Behavior on reveal { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    Component.onCompleted: reveal = 1

    readonly property var pages: (schemaData && schemaData.pages) || []
    readonly property string currentPage: Config.page
    readonly property int pendingCount: Object.keys(pending).length
    readonly property string backendDir:
        Qt.resolvedUrl("../backend").toString().replace("file://", "")

    function call(method, params) {
        const id = ++reqId;
        const map = Object.assign({}, inflight);
        map[id] = method;
        inflight = map;
        busy = true;
        rpc.write(JSON.stringify({ id: id, method: method, params: params || ({}) }) + "\n");
    }

    function onLine(line) {
        let res = null;
        try {
            res = JSON.parse(line);
        } catch (e) {
            status = line;
            return;
        }
        const method = inflight[res.id];
        const map = Object.assign({}, inflight);
        delete map[res.id];
        inflight = map;
        busy = false;

        if (res.error) {
            status = "error: " + res.error;
            return;
        }
        const r = res.result;
        if (method === "schema") {
            schemaData = r;
        } else if (method === "dump") {
            model = r;
            status = r.error ? ("error: " + r.error)
                             : ("ok · " + r.requires.length + " modules · "
                                + r.animation_order.length + " animations");
        } else if (method === "bar.get") {
            barValues = r;
        } else if (method === "module.dump") {
            if (r && r.model) {
                targetModel = r.model;
                targetFile = r.file;
            }
        } else if (method === "reload") {
            if (!status.startsWith("saved"))
                status = "reloaded Hyprland";
            else
                status += " · Hyprland reloaded";
        } else if (method === "apply") {
            pending = ({});
            status = "applied " + r.files.length + " file(s)"
                     + (r.backup ? (" · backup " + r.backup.stamp) : " · no backup");
            call("reload");
            call("schema");
            call("dump");
            call("bar.get");
            if (targetFile)
                call("module.dump", { file: targetFile });
        }
    }

    function selectPage(id) {
        Config.page = id;
    }

    function saveConfiguration() {
        // Commit the focused text field first: clicking a button or Ctrl+S must
        // not drop the value the user just typed.
        app.forceActiveFocus();
        if (pendingCount > 0)
            applyPending();
    }

    function stage(key, descriptor) {
        const map = Object.assign({}, pending);
        map[key] = descriptor;
        pending = map;
    }

    function unstage(key) {
        const map = Object.assign({}, pending);
        delete map[key];
        pending = map;
    }

    function setPending(path, value, kind) {
        stage(path, { type: "config", path: path, value: value, kind: kind });
    }

    function revertAll() {
        pending = ({});
    }

    function applyEdits(edits, reason) {
        if (!edits || edits.length === 0)
            return;
        call("apply", { edits: edits, reason: reason || "config-manager GUI" });
    }

    function applyPending() {
        const edits = [];
        for (const key of Object.keys(pending))
            edits.push(pending[key]);
        applyEdits(edits, "config-manager GUI");
    }

    function loadTarget(file) {
        if (!file)
            return;
        targetFile = file;
        status = "reading " + file + "…";
        call("module.dump", { file: file });
    }

    function reload() {
        status = "reading config…";
        call("schema");
        call("dump");
        call("bar.get");
        if (targetFile)
            call("module.dump", { file: targetFile });
    }

    Process {
        id: rpc
        running: true
        stdinEnabled: true
        command: ["python3", "-m", "config_manager.cli", "serve"]
        clearEnvironment: false
        environment: ({ "PYTHONPATH": app.backendDir })
        stdout: SplitParser { onRead: line => app.onLine(line) }
        stderr: SplitParser { onRead: line => console.warn("config-manager:", line) }
        onStarted: {
            console.log("config-manager: backend started");
            app.call("schema");
            app.reload();
        }
        onExited: (code, status) => {
            if (code !== 0)
                app.status = "backend exited (" + code + ")";
        }
    }

    onStatusChanged: console.log("config-manager:", status)


    Shortcut {
        sequence: "Escape"
        onActivated: Qt.quit()
    }

    Shortcut {
        sequence: "Ctrl+S"
        onActivated: app.saveConfiguration()
    }

    // ── chrome ─────────────────────────────────────────────────────────
    // Mirrors the hyprtk-bar-qt settings dialogue: flush 150px sidebar,
    // flat label rows, 16px content margins and a footer with the actions.
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusPanel
        color: Qt.rgba(Theme.background.r, Theme.background.g,
                       Theme.background.b, Theme.panelOpacityStrong)
        border.width: 0

        RowLayout {
            anchors.fill: parent
            spacing: 0
            opacity: app.reveal
            transform: Translate { y: (1 - app.reveal) * -8 }

            // ── sidebar ──────────────────────────────────────────────
            Rectangle {
                Layout.fillHeight: true
                implicitWidth: 150
                topLeftRadius: Theme.radiusPanel
                bottomLeftRadius: Theme.radiusPanel
                color: Theme.alpha(Theme.background, 0.6)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 4

                    Repeater {
                        model: app.pages
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 32
                            radius: 8
                            color: app.currentPage === modelData.id
                                   ? Theme.alpha(Theme.accent, 0.85)
                                   : (navHover.hovered ? Theme.alpha(Theme.accent2, Theme.hoverAlpha) : "transparent")

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                anchors.right: parent.right
                                anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.title
                                color: app.currentPage === modelData.id ? Theme.textOnAccent : Theme.foreground
                                font.pixelSize: Theme.scaled(12)
                                elide: Text.ElideRight
                            }
                            HoverHandler { id: navHover }
                            TapHandler { onTapped: app.selectPage(modelData.id) }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // ── content ──────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 16
                spacing: 12

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Animations {
                        id: animPage
                        anchors.fill: parent
                        visible: app.currentPage === "animations"
                        model: app.model
                        schemaData: app.schemaData
                        bar: app.barValues
                        targetModel: app.targetModel
                        targetFile: app.targetFile
                        pending: app.pending
                        onStage: (key, descriptor) => app.stage(key, descriptor)
                        onRequestTarget: file => app.loadTarget(file)
                        onApplyNow: (edits, reason) => app.applyEdits(edits, reason)
                    }

                    ConfigPage {
                        anchors.fill: parent
                        visible: app.currentPage !== "animations"
                        pageId: app.currentPage
                        model: app.model
                        schemaData: app.schemaData
                        pending: app.pending
                        onChange: (path, value, kind) => app.setPending(path, value, kind)
                        onItemChange: (key, descriptor) => app.stage(key, descriptor)
                    }
                }

                // ── footer ───────────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        text: {
                            if (app.pendingCount > 0)
                                return app.pendingCount + " pending change"
                                     + (app.pendingCount === 1 ? "" : "s")
                                     + " · writes to the owning Lua file";
                            return app.status;
                        }
                        color: app.dirty
                               ? Theme.accent2
                               : (app.status.startsWith("error") ? Theme.danger : Theme.dim)
                        font.pixelSize: Theme.scaled(10)
                        elide: Text.ElideRight
                    }
                    TButton {
                        text: "Reload"
                        enabled: !app.busy
                        onClicked: app.reload()
                    }
                    TButton {
                        text: "Revert"
                        visible: app.dirty
                        onClicked: app.revertAll()
                    }
                    TButton {
                        text: "Save configuration"
                        primary: true
                        enabled: app.dirty && !app.busy
                        onClicked: app.saveConfiguration()
                    }
                    TButton {
                        text: "Close"
                        onClicked: Qt.quit()
                    }
                }
            }
        }

        // Animated accent border on top, same chrome as the bar/dialogs.
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusPanel
            color: "transparent"
            border.width: Theme.borderWidth
            border.color: Theme.accent
            SequentialAnimation on border.color {
                running: Theme.borderAnimation
                loops: Animation.Infinite
                ColorAnimation { to: Theme.accent2; duration: Theme.animationPeriodMs; easing.type: Easing.InOutSine }
                ColorAnimation { to: Theme.accent; duration: Theme.animationPeriodMs; easing.type: Easing.InOutSine }
            }
        }
    }
}
