// The application shell: sidebar, page stack, footer apply model, dialogs and
// the JSON-lines connection to the Python backend.
import QtQuick
import Quickshell
import Quickshell.Io
import "../theme"
import "../config"
import "../components"
import "pages"

Item {
    id: app

    // ── backend state ─────────────────────────────────────────────────
    property var catalogData: ({ groups: [], panels: [] })
    property var backend: ({})
    property var pageModel: ({})
    property var pageCache: ({})
    property var pending: ({})
    property var inflight: ({})
    property int reqId: 0
    property bool loading: true
    property bool applyRunning: false
    property var applyQueue: []
    property var applyResults: []
    property string status: "Connecting to the backend…"
    property string searchText: ""
    property var searchResults: []
    property var recentIds: []
    property bool searchIndexing: false
    property string shotPath: Quickshell.env("HYPRTK_SM_SHOT") || ""

    readonly property var groups: catalogData.groups || []
    readonly property var panels: catalogData.panels || []
    readonly property string pageId: Config.page
    readonly property var currentMeta: metaFor(pageId)
    readonly property int pendingCount: Object.keys(pending).length
    readonly property bool dirty: pendingCount > 0
    readonly property string backendDir:
        Qt.resolvedUrl("../backend").toString().replace("file://", "")
    readonly property string pageKind: {
        if (pageId === "displays") return "displays";
        if (pageId === "users") return "users";
        return "form";
    }

    // dialogs
    property var confirmState: ({})
    property var passwordState: ({})
    property var groupsState: ({})
    property var selectedGroups: []
    property var shellState: ({})
    property string selectedShell: ""
    property var wifiState: ({})
    property var pickerState: ({})
    property string pickerPath: ""
    property string pickerParent: ""
    property string pickerSelected: ""
    property var pickerEntries: []

    // ── helpers ───────────────────────────────────────────────────────
    function metaFor(id) {
        for (let i = 0; i < panels.length; i++) {
            if (panels[i].id === id)
                return panels[i];
        }
        return { id: id, title: id, description: "", icon: "\uf05a",
                 status: "read", statusLabel: "read only", group: "", keywords: [] };
    }
    function toneFor(status) {
        if (status === "full") return "ok";
        if (status === "live") return "info";
        if (status === "partial") return "warn";
        if (status === "link") return "accent";
        return "neutral";
    }
    function statusLabelFor(status) {
        if (status === "full") return "functional";
        if (status === "live") return "live only";
        if (status === "partial") return "partial";
        if (status === "read") return "read only";
        if (status === "link") return "external";
        if (status === "planned") return "planned";
        return status || "read only";
    }
    function invalidate(id) {
        const cache = Object.assign({}, pageCache);
        delete cache[id];
        pageCache = cache;
    }
    function pendingFor(panelId) {
        const out = {};
        for (const key in pending) {
            const bits = key.split("::");
            if (bits[0] === panelId)
                out[bits.slice(1).join("::")] = pending[key];
        }
        return out;
    }
    function setPending(panelId, key, value) {
        const map = Object.assign({}, pending);
        map[panelId + "::" + key] = value;
        pending = map;
        status = pendingCount + 1 + " pending change" + ((pendingCount + 1) === 1 ? "" : "s");
    }
    function revertAll() {
        pending = ({});
        status = "Changes discarded";
        toast.show("Pending changes discarded", "info");
        if (pageId) openPage(pageId, true);
    }

    // ── RPC ───────────────────────────────────────────────────────────
    function call(method, params, tag) {
        const id = ++reqId;
        const map = Object.assign({}, inflight);
        map[id] = tag || method;
        inflight = map;
        rpc.write(JSON.stringify({ id: id, method: method, params: params || ({}) }) + "\n");
    }

    function handleLine(line) {
        let res = null;
        try { res = JSON.parse(line); }
        catch (e) { console.warn("system-manager: bad line", line); return; }

        const tag = inflight[res.id] || "";
        const map = Object.assign({}, inflight);
        delete map[res.id];
        inflight = map;

        if (res.error) {
            if (tag === "apply") {
                applyResults.push({ ok: false, message: res.error });
                applyQueue = [];
                finishApply();
            } else {
                status = "Error: " + res.error;
                toast.show(res.error, "danger");
                if (Config.testMode)
                    Qt.exit(1);
            }
            return;
        }

        const r = res.result;

        if (tag === "hello") {
            backend = r || ({});
            catalogData = (r && r.catalog) || ({ groups: [], panels: [] });
            app.recentIds = (r && r.ui && r.ui.recent) || [];
            const envPage = Quickshell.env("HYPRTK_SM_PAGE") || "";
            let start = envPage || (r && r.ui && r.ui.last_page) || "about";
            if (!panels.some(p => p.id === start))
                start = "about";
            status = "Ready · " + ((r && r.hostname) || "this device");
            openPage(start, true);
            return;
        }

        if (tag === "panel") {
            if (!r || r.id !== app.pageId)
                return;
            pageModel = r;
            loading = false;
            status = (r.title || pageId) + " · " + (r.statusLabel || "");
            const cache = Object.assign({}, pageCache);
            cache[r.id] = { model: r, at: Date.now() };
            pageCache = cache;
            if (Config.testMode) {
                if (app.shotPath.length > 0)
                    shotTimer.restart();
                else
                    Qt.exit(0);
            }
            return;
        }

        if (tag === "apply") {
            handleApply(r);
            return;
        }

        if (tag.indexOf("action:") === 0) {
            const pid = tag.split(":")[1] || pageId;
            const message = r.message || "Done";
            status = message;
            toast.show(message, r.ok ? "ok" : (r.requires === "root" ? "warn" : "danger"));
            if (r.details && r.details.length)
                console.log("system-manager: " + r.details.join(" · "));
            if (r.ok && r.refresh) {
                invalidate(pid);
                if (pageId === pid)
                    openPage(pid, true);
            }
            return;
        }

        if (tag === "search") {
            if (!r || r.query !== app.searchText.trim())
                return;
            searchResults = r.results || [];
            searchIndexing = !!r.indexing;
            if (searchIndexing)
                reindexTimer.restart();
            else
                reindexTimer.stop();
            return;
        }

        if (tag === "fs") {
            pickerPath = r.path || "";
            pickerParent = r.parent || "";
            pickerEntries = r.entries || [];
            return;
        }
    }

    // ── navigation ────────────────────────────────────────────────────
    function openPage(id, force) {
        if (!id)
            return;
        Config.page = id;
        Config.lastPage = id;
        app.recentIds = [id].concat(app.recentIds.filter(other => other !== id)).slice(0, 5);
        call("ui.set", { values: { last_page: id } });
        sidebar.clearSearch();
        const cached = pageCache[id];
        if (!force && cached && (Date.now() - cached.at) < 60000) {
            pageModel = cached.model;
            loading = false;
            status = cached.model.title + " · " + cached.model.statusLabel;
            return;
        }
        loading = true;
        pageModel = ({});
        status = "Reading " + metaFor(id).title + "…";
        call("panel", { id: id });
    }

    function reloadPage() {
        if (pageId) {
            invalidate(pageId);
            openPage(pageId, true);
        }
    }

    function searchFor(text) {
        searchText = text;
        if (!text || text.trim().length === 0) {
            searchResults = [];
            searchIndexing = false;
            reindexTimer.stop();
            return;
        }
        searchTimer.restart();
    }

    // ── apply model ───────────────────────────────────────────────────
    function applyAll() {
        if (!dirty || applyRunning)
            return;
        const ids = [];
        for (const key in pending) {
            const pid = key.split("::")[0];
            if (ids.indexOf(pid) < 0)
                ids.push(pid);
        }
        applyQueue = ids.map(pid => ({ id: pid, changes: pendingFor(pid) }));
        applyResults = [];
        applyRunning = true;
        status = "Applying…";
        sendNextApply();
    }

    function sendNextApply() {
        if (applyQueue.length === 0) {
            finishApply();
            return;
        }
        const job = applyQueue[0];
        call("apply", { id: job.id, changes: job.changes }, "apply");
    }

    function handleApply(result) {
        const job = applyQueue[0];
        applyResults.push(result || ({ ok: false, message: "no response" }));
        if (!result || !result.ok) {
            applyQueue = [];
            finishApply();
            return;
        }
        const map = Object.assign({}, pending);
        for (const key in map) {
            if (key.indexOf(job.id + "::") === 0)
                delete map[key];
        }
        pending = map;
        invalidate(job.id);
        applyQueue.shift();
        if (applyQueue.length === 0)
            finishApply();
        else
            sendNextApply();
    }

    function finishApply() {
        applyRunning = false;
        applyQueue = [];
        const failed = applyResults.filter(r => !r.ok);
        if (failed.length > 0) {
            status = failed[0].message || "Apply failed";
            toast.show(status, failed[0].requires === "root" ? "warn" : "danger");
        } else {
            const message = applyResults.length > 0
                ? applyResults.map(r => r.message).join(" · ")
                : "Nothing to apply";
            status = message;
            toast.show(message, "ok");
        }
        if (pageId)
            openPage(pageId, true);
    }

    // ── actions ───────────────────────────────────────────────────────
    function requestAction(panelId, actionObj) {
        if (!actionObj || !actionObj.action)
            return;
        if (actionObj.needs === "wifi") {
            wifiState = { panelId: panelId, actionObj: actionObj };
            wifiField.text = "";
            wifiDialog.open = true;
            return;
        }
        if (actionObj.needs === "file") {
            pickerState = { panelId: panelId, actionObj: actionObj, mode: "file" };
            pickerSelected = "";
            picker.open = true;
            call("fs.list", { path: Quickshell.env("HOME") || "/" }, "fs");
            return;
        }
        if (actionObj.needs === "groups") {
            groupsState = { panelId: panelId, actionObj: actionObj };
            const current = (actionObj.args && actionObj.args.groups) || [];
            selectedGroups = current.slice();
            groupsDialog.open = true;
            return;
        }
        if (actionObj.needs === "shell") {
            shellState = { panelId: panelId, actionObj: actionObj };
            selectedShell = (actionObj.args && actionObj.args.shell) || "";
            shellDialog.open = true;
            return;
        }
        if (actionObj.needs === "password") {
            passwordState = { panelId: panelId, actionObj: actionObj };
            passwordField.text = "";
            passwordRepeat.text = "";
            passwordError.text = "";
            passwordDialog.open = true;
            return;
        }
        if (actionObj.danger) {
            confirmState = {
                panelId: panelId,
                actionObj: actionObj,
                title: actionObj.label || "Confirm",
                message: actionObj.message || "This cannot be undone.",
                confirmText: actionObj.label || "Confirm",
                required: actionObj.confirm || "",
            };
            confirmField.text = "";
            confirmDialog.open = true;
            return;
        }
        runAction(panelId, actionObj, {});
    }

    function runAction(panelId, actionObj, extra) {
        const args = Object.assign({}, actionObj.args || {}, extra || {});
        status = (actionObj.label || "Working") + "…";
        call("action", { id: panelId, action: actionObj.action, args: args },
             "action:" + panelId);
    }

    // ── file picker ───────────────────────────────────────────────────
    function browse(panelId, key, mode, current) {
        pickerState = { panelId: panelId, key: key, mode: mode };
        pickerSelected = "";
        let start = current || Quickshell.env("HOME") || "/";
        if (mode === "file" && start.length > 1) {
            const cut = start.lastIndexOf("/");
            if (cut > 0)
                start = start.substring(0, cut);
        }
        picker.open = true;
        call("fs.list", { path: start }, "fs");
    }

    function pickerNavigate(path) {
        if (path)
            call("fs.list", { path: path }, "fs");
    }

    function pickerChoose(entry) {
        if (entry.dir) {
            pickerNavigate(entry.path);
        } else {
            pickerSelected = entry.path;
        }
    }

    function pickerAccept() {
        const value = pickerState.mode === "dir" ? pickerPath : pickerSelected;
        if (!value)
            return;
        if (pickerState.actionObj)
            runAction(pickerState.panelId, pickerState.actionObj, { path: value });
        else
            setPending(pickerState.panelId, pickerState.key, value);
        picker.open = false;
    }

    function pickerBase(entry) {
        return entry.name;
    }

    // ── lifecycle ─────────────────────────────────────────────────────
    Component.onCompleted: Config.completed = true

    Process {
        id: rpc
        running: true
        stdinEnabled: true
        command: ["python3", "-m", "system_manager.cli", "serve"]
        clearEnvironment: false
        environment: ({ "PYTHONPATH": app.backendDir })
        stdout: SplitParser { onRead: line => app.handleLine(line) }
        stderr: SplitParser { onRead: line => console.warn("system-manager:", line) }
        onStarted: {
            console.log("system-manager: backend started");
            app.call("hello", {});
        }
        onExited: (code, exitStatus) => {
            app.status = "Backend stopped (" + code + ")";
            app.toast.show("The settings backend stopped", "danger");
            if (Config.testMode)
                Qt.exit(1);
        }
    }

    Timer {
        id: searchTimer
        interval: 150
        onTriggered: app.call("search", { query: app.searchText }, "search")
    }

    // The background index keeps warming after the first search; re-run the
    // active query so row matches appear without retyping.
    Timer {
        id: reindexTimer
        interval: 1200
        onTriggered: {
            if (app.searchText.trim().length > 0 && app.searchIndexing)
                app.call("search", { query: app.searchText }, "search");
        }
    }

    Timer {
        id: shotTimer
        interval: 700
        onTriggered: app.captureShot()
    }

    function captureShot() {
        app.grabToImage(function(result) {
            const saved = result.saveToFile(app.shotPath);
            console.log("SHOT " + (saved ? "SAVED" : "FAILED") + " " + app.shotPath);
            Qt.exit(saved ? 0 : 1);
        }, Qt.size(app.width, app.height));
    }

    Timer {
        id: bootGuard
        interval: 30000
        running: Config.testMode
        onTriggered: {
            console.log("BOOTCHECK TIMEOUT");
            Qt.exit(1);
        }
    }

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: sidebar.focusSearch()
    }
    Shortcut {
        sequence: "Ctrl+S"
        onActivated: app.applyAll()
    }
    Shortcut {
        sequence: "Ctrl+Z"
        onActivated: app.revertAll()
    }
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (confirmDialog.open) { confirmDialog.open = false; return; }
            if (groupsDialog.open) { groupsDialog.open = false; return; }
            if (shellDialog.open) { shellDialog.open = false; return; }
            if (wifiDialog.open) { wifiDialog.open = false; return; }
            if (passwordDialog.open) { passwordDialog.open = false; return; }
            if (picker.open) { picker.open = false; return; }
            if (app.searchText.length > 0) { sidebar.clearSearch(); return; }
            Qt.quit();
        }
    }

    // ── chrome ────────────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusLg
        color: Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b,
                       Theme.panelOpacityStrong)
        clip: true

        Row {
            anchors.fill: parent
            spacing: 0

            Sidebar {
                id: sidebar
                width: Config.sidebarWidth
                height: parent.height
                groups: app.groups
                panels: app.panels
                searchResults: app.searchResults
                recent: app.recentIds
                searchIndexing: app.searchIndexing
                currentPage: app.pageId
                hostname: (app.backend && app.backend.hostname) || ""
                version: (app.backend && app.backend.version) || "0.1.0"
                privilege: (app.backend && app.backend.capabilities &&
                            app.backend.capabilities.can_escalate) ? "admin" : "user"
                onSelect: (id) => app.openPage(id, false)
                onSearchChanged: (text) => app.searchFor(text)
                onSubmitted: {
                    if (app.searchResults.length > 0)
                        app.openPage(app.searchResults[0].id, false);
                }
            }

            Rectangle { width: 1; height: parent.height; color: Theme.alpha(Theme.foreground, 0.10) }

            Item {
                width: parent.width - Config.sidebarWidth - 1
                height: parent.height

                // header
                Item {
                    id: header
                    width: parent.width
                    height: 60

                    Row {
                        x: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        Glyph {
                            glyph: app.currentMeta.icon || "\uf05a"
                            pixelSize: 18
                            color: Theme.accent
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1
                            Text {
                                text: app.currentMeta.title || "Settings"
                                color: Theme.foreground
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.size(3)
                                font.bold: true
                            }
                            Text {
                                text: app.currentMeta.description || ""
                                color: Theme.dim
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.size(0)
                                elide: Text.ElideRight
                                width: Math.min(implicitWidth, 560)
                            }
                        }
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        StatusPill {
                            anchors.verticalCenter: parent.verticalCenter
                            text: app.currentMeta.statusLabel ||
                                  app.statusLabelFor(app.currentMeta.status)
                            tone: app.toneFor(app.currentMeta.status)
                        }
                        TButton {
                            text: "Reload"
                            small: true
                            enabled: !app.loading
                            onClicked: app.reloadPage()
                        }
                    }

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.alpha(Theme.foreground, 0.10)
                    }
                }

                // pages
                Item {
                    id: pageHost
                    anchors.top: header.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: footer.top

                    FormPage {
                        anchors.fill: parent
                        visible: app.pageKind === "form"
                        model: app.pageModel
                        panelId: app.pageId
                        pending: app.pending
                        onChange: (panelId, key, value) => app.setPending(panelId, key, value)
                        onInvoke: (panelId, action) => app.requestAction(panelId, action)
                        onBrowse: (panelId, key, mode, value) => app.browse(panelId, key, mode, value)
                    }

                    DisplaysPage {
                        anchors.fill: parent
                        visible: app.pageKind === "displays"
                        model: app.pageModel
                        panelId: app.pageId
                        pending: app.pending
                        onChange: (panelId, key, value) => app.setPending(panelId, key, value)
                        onInvoke: (panelId, action) => app.requestAction(panelId, action)
                        onBrowse: (panelId, key, mode, value) => app.browse(panelId, key, mode, value)
                    }

                    UsersPage {
                        anchors.fill: parent
                        visible: app.pageKind === "users"
                        model: app.pageModel
                        panelId: app.pageId
                        pending: app.pending
                        onChange: (panelId, key, value) => app.setPending(panelId, key, value)
                        onInvoke: (panelId, action) => app.requestAction(panelId, action)
                        onBrowse: (panelId, key, mode, value) => app.browse(panelId, key, mode, value)
                    }

                    // loading
                    Item {
                        anchors.fill: parent
                        visible: app.loading
                        Rectangle {
                            anchors.centerIn: parent
                            width: 220
                            height: 58
                            radius: Theme.radiusCard
                            color: Qt.rgba(Theme.background.r, Theme.background.g,
                                           Theme.background.b, Theme.panelOpacityStrong)
                            border.width: 1
                            border.color: Theme.alpha(Theme.accent2, 0.25)
                            Row {
                                anchors.centerIn: parent
                                spacing: 10
                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: Theme.accent
                                    SequentialAnimation on opacity {
                                        loops: Animation.Infinite
                                        NumberAnimation { to: 0.2; duration: 500 }
                                        NumberAnimation { to: 1.0; duration: 500 }
                                    }
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Reading settings…"
                                    color: Theme.dim
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.size(1)
                                }
                            }
                        }
                    }
                }

                // footer
                Rectangle {
                    id: footer
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 48
                    color: "transparent"

                    Rectangle {
                        anchors.top: parent.top
                        width: parent.width
                        height: 1
                        color: Theme.alpha(Theme.foreground, 0.10)
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        Rectangle {
                            width: 7; height: 7; radius: 3.5
                            anchors.verticalCenter: parent.verticalCenter
                            color: app.applyRunning ? Theme.warn
                                 : app.dirty ? Theme.accent
                                 : (app.status.indexOf("rror") >= 0 ? Theme.danger : Theme.ok)
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.min(implicitWidth, pageHost.width - 340)
                            text: app.dirty
                                ? app.pendingCount + " pending change" +
                                  (app.pendingCount === 1 ? "" : "s") +
                                  (app.applyRunning ? " · applying…" : " · press Apply to write")
                                : app.status
                            color: app.dirty ? Theme.accent2 : Theme.dim
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.size(0)
                            elide: Text.ElideRight
                        }
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        TButton {
                            text: "Revert"
                            visible: app.dirty
                            enabled: !app.applyRunning
                            onClicked: app.revertAll()
                        }
                        TButton {
                            text: app.applyRunning ? "Applying…" : "Apply"
                            primary: true
                            visible: app.dirty || app.applyRunning
                            enabled: app.dirty && !app.applyRunning
                            onClicked: app.applyAll()
                        }
                        TButton {
                            text: "Close"
                            onClicked: Qt.quit()
                        }
                    }
                }
            }
        }

        // animated accent border, same chrome as the bar and dialogs
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusLg
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

    // ── dialogs ───────────────────────────────────────────────────────
    Modal {
        id: confirmDialog
        title: app.confirmState.title || "Confirm"
        message: app.confirmState.message || ""
        confirmText: app.confirmState.confirmText || "Confirm"
        danger: true
        confirmEnabled: !app.confirmState.required ||
                        confirmField.text === app.confirmState.required
        onAccepted: {
            const state = app.confirmState;
            confirmDialog.open = false;
            app.runAction(state.panelId, state.actionObj, {});
        }
        onRejected: confirmDialog.open = false

        Text {
            visible: (app.confirmState.required || "").length > 0
            width: parent.width
            text: "Type “" + (app.confirmState.required || "") + "” to continue."
            color: Theme.dim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            wrapMode: Text.WordWrap
        }
        TTextField {
            id: confirmField
            visible: (app.confirmState.required || "").length > 0
            preferredWidth: parent.width
            placeholder: app.confirmState.required || ""
        }
    }

    Modal {
        id: passwordDialog
        title: "Change password"
        message: "For " + ((app.passwordState.actionObj &&
                            app.passwordState.actionObj.args &&
                            app.passwordState.actionObj.args.username) || "this account") +
                 ". The password is sent once to chpasswd and never stored."
        confirmText: "Change password"
        confirmEnabled: passwordField.text.length > 0 &&
                        passwordField.text === passwordRepeat.text
        onAccepted: {
            const state = app.passwordState;
            passwordDialog.open = false;
            app.runAction(state.panelId, state.actionObj,
                          { password: passwordField.text });
            passwordField.text = "";
            passwordRepeat.text = "";
        }
        onRejected: {
            passwordDialog.open = false;
            passwordField.text = "";
            passwordRepeat.text = "";
        }

        TTextField {
            id: passwordField
            preferredWidth: parent.width
            placeholder: "New password"
            echoMode: TextInput.Password
        }
        TTextField {
            id: passwordRepeat
            preferredWidth: parent.width
            placeholder: "Repeat password"
            echoMode: TextInput.Password
        }
        Text {
            id: passwordError
            width: parent.width
            visible: text.length > 0
            color: Theme.danger
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(1)
            text: passwordField.text.length > 0 &&
                  passwordRepeat.text.length > 0 &&
                  passwordField.text !== passwordRepeat.text
                  ? "Passwords do not match." : ""
        }
    }

    Modal {
        id: groupsDialog
        title: "Groups"
        message: "Supplementary groups for " + ((app.groupsState.actionObj &&
                 app.groupsState.actionObj.args &&
                 app.groupsState.actionObj.args.username) || "this account") + "."
        confirmText: "Save groups"
        onAccepted: {
            const state = app.groupsState;
            groupsDialog.open = false;
            app.runAction(state.panelId, state.actionObj,
                          { groups: app.selectedGroups.join(",") });
        }
        onRejected: groupsDialog.open = false

        Flickable {
            width: parent.width
            height: Math.min(300, groupColumn.implicitHeight + 4)
            contentHeight: groupColumn.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: groupColumn
                width: parent.width
                spacing: 2

                Repeater {
                    model: app.pageId === "users" ? (app.pageModel.groups || []) : []
                    delegate: SettingRow {
                        required property var modelData
                        width: groupColumn.width
                        label: String(modelData)
                        ToggleSwitch {
                            checked: app.selectedGroups.indexOf(String(modelData)) >= 0
                            onToggled: (on) => {
                                let next = app.selectedGroups.slice();
                                if (on) {
                                    if (next.indexOf(String(modelData)) < 0)
                                        next.push(String(modelData));
                                } else {
                                    next = next.filter(name => name !== String(modelData));
                                }
                                app.selectedGroups = next;
                            }
                        }
                    }
                }
                Text {
                    visible: (app.pageModel.groups || []).length === 0
                    width: parent.width
                    text: "No groups available."
                    color: Theme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.size(1)
                }
            }
        }
    }

    Modal {
        id: shellDialog
        title: "Login shell"
        message: "For " + ((app.shellState.actionObj &&
                 app.shellState.actionObj.args &&
                 app.shellState.actionObj.args.username) || "this account") + "."
        confirmText: "Change shell"
        confirmEnabled: app.selectedShell.length > 0
        onAccepted: {
            const state = app.shellState;
            shellDialog.open = false;
            app.runAction(state.panelId, state.actionObj, { shell: app.selectedShell });
        }
        onRejected: shellDialog.open = false

        Dropdown {
            width: parent.width
            value: app.selectedShell
            choices: ((app.pageId === "users" ? app.pageModel.shells : []) || [])
                     .map(item => ({ value: item, label: item }))
            onSelected: (value) => app.selectedShell = value
        }
    }

    Modal {
        id: wifiDialog
        title: "Connect to Wi-Fi"
        message: ((app.wifiState.actionObj && app.wifiState.actionObj.args &&
                   app.wifiState.actionObj.args.ssid) || "Network") +
                 " · " + ((app.wifiState.actionObj && app.wifiState.actionObj.args &&
                           app.wifiState.actionObj.args.security) || "secured")
        confirmText: "Connect"
        confirmEnabled: wifiField.text.length > 0
        onAccepted: {
            const state = app.wifiState;
            wifiDialog.open = false;
            app.runAction(state.panelId, state.actionObj,
                          { password: wifiField.text });
            wifiField.text = "";
        }
        onRejected: {
            wifiDialog.open = false;
            wifiField.text = "";
        }

        TTextField {
            id: wifiField
            preferredWidth: parent.width
            placeholder: "Wi-Fi password"
            echoMode: TextInput.Password
        }
        Text {
            width: parent.width
            text: "The password is handed to NetworkManager through a private 0600 file and is never stored by this app."
            color: Theme.dim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.size(0)
            wrapMode: Text.WordWrap
        }
    }

    Modal {
        id: picker
        title: app.pickerState.mode === "dir" ? "Choose a folder" : "Choose a file"
        message: app.pickerPath
        confirmText: app.pickerState.mode === "dir" ? "Use this folder" : "Use this file"
        confirmEnabled: app.pickerState.mode === "dir"
                        ? app.pickerPath.length > 0
                        : app.pickerSelected.length > 0
        onAccepted: app.pickerAccept()
        onRejected: picker.open = false

        Row {
            width: parent.width
            spacing: 8
            TButton {
                text: "Up"
                small: true
                enabled: app.pickerParent.length > 0
                onClicked: app.pickerNavigate(app.pickerParent)
            }
            TButton {
                text: "Home"
                small: true
                onClicked: app.pickerNavigate(Quickshell.env("HOME") || "/")
            }
            Text {
                width: parent.width - 180
                anchors.verticalCenter: parent.verticalCenter
                text: app.pickerPath
                color: Theme.textFaint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.size(1)
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            width: parent.width
            height: 300
            radius: Theme.radiusCard
            color: Theme.cardFill
            border.width: 1
            border.color: Theme.cardBorder

            ListView {
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                model: app.pickerEntries

                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    height: 30
                    radius: 6
                    color: modelData.path === app.pickerSelected ? Theme.alpha(Theme.accent, 0.25)
                         : (entryHover.hovered ? Theme.hoverTint : "transparent")

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        Glyph {
                            glyph: modelData.dir ? "\uf07b" : "\uf15b"
                            pixelSize: Theme.size(2)
                            color: modelData.dir ? Theme.accent : Theme.textFaint
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width - 30
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name
                            color: modelData.dir ? Theme.foreground : Theme.dim
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.size(2)
                            elide: Text.ElideRight
                        }
                    }
                    HoverHandler { id: entryHover }
                    TapHandler { onTapped: app.pickerChoose(modelData) }
                }
            }
        }
    }

    Toast {
        id: toast
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 74
    }
}
