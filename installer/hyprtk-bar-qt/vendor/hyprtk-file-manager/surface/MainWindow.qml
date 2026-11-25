import QtQuick
import QtQuick.Layouts
import Quickshell
import "../theme"
import "../config"
import "../data"

FloatingWindow {
    id: win

    visible: true
    color: Theme.background
    title: Quickshell.env("HYPRTK_FM_TITLE") || "Files"
    implicitWidth: 1200
    implicitHeight: 760
    minimumSize: Qt.size(760, 480)

    // Closing the window must end the process. Quickshell keeps running with an
    // invisible window otherwise, so every launch (Super+F, the bar's Files
    // quick link) left another stray hyprtk-fm process behind.
    onClosed: Qt.quit()

    property var activePane: paneA
    property var renameTarget: null
    property var newTarget: null
    property var deleteTarget: null
    property int sessionId: -1
    property bool sessionLoaded: false
    property bool restoring: false
    property var compressTargets: []
    property string compressDir: ""
    property var smartFolders: []
    property int smartId: -1
    property string pendingTool: ""
    property int toolId: -1

    function setActivePane(pane) {
        win.activePane = pane;
        paneA.active = (pane === paneA);
        paneB.active = (pane === paneB);
        Clipboard.refresh();
        if (pane) {
            pane.forceActiveFocus();
            pane.requestPreview();
        }
    }

    function focusActivePane() {
        if (win.activePane)
            win.activePane.forceActiveFocus();
    }

    function toggleActivePane() {
        if (!Config.dualPane)
            return;
        win.setActivePane(win.activePane === paneA ? paneB : paneA);
    }

    function scheduleSessionSave() {
        if (!win.sessionLoaded || win.restoring)
            return;
        sessionTimer.restart();
    }

    function saveSession() {
        if (!win.sessionLoaded || win.restoring)
            return;
        Backend.call("session.set", {
            session: {
                paneA: paneA.sessionState(),
                paneB: paneB.sessionState()
            }
        });
    }

    function openPalette() {
        const pane = win.activePane;
        if (!pane)
            return;
        const entries = [
            { label: "Go Home", action: function () { pane.navigate(Config.startPath); } },
            { label: "Go Up", action: function () { pane.goUp(); } },
            { label: "Back", action: function () { pane.goBack(); } },
            { label: "Forward", action: function () { pane.goForward(); } },
            { label: "New Tab", action: function () { pane.newTab(); } },
            { label: "Close Tab", action: function () { pane.closeTab(pane.activeIndex); } },
            { label: "Toggle Dual Pane", action: function () { Config.dualPane = !Config.dualPane; } },
            { label: "Toggle Hidden Files", action: function () { Config.showHidden = !Config.showHidden; } },
            { label: "Toggle Preview", action: function () { pane.togglePreview(); } },
            { label: "List View", action: function () { Config.viewMode = "list"; } },
            { label: "Grid View", action: function () { Config.viewMode = "grid"; } },
            { label: "Compact View", action: function () { Config.viewMode = "compact"; } },
            { label: "Filter This Folder", action: function () { pane.startFilter(); } },
            { label: "Search in Folder…", action: function () { searchPanel.open(pane.path); } },
            { label: "New Folder…", action: function () { pane.newFolder(); } },
            { label: "New File…", action: function () { pane.newFile(); } },
            { label: "Rename…", action: function () { pane.renameSelected(); } },
            { label: "Batch Rename…", action: function () { Ui.askBatchRename(pane.selectedPaths()); } },
            { label: "Copy", action: function () { pane.copySelection(); } },
            { label: "Cut", action: function () { pane.cutSelection(); } },
            { label: "Paste", action: function () { pane.pasteClipboard(); } },
            { label: "Move to Trash", action: function () { pane.trashSelection(); } },
            { label: "Delete Permanently…", action: function () { pane.deleteSelection(); } },
            { label: "Undo", action: function () { Jobs.undo(); } },
            { label: "Redo", action: function () { Jobs.redo(); } },
            { label: "Git Diff…", action: function () { Ui.askGitDiff(pane.cursorPath()); } },
            { label: "Disk Usage…", action: function () { toolsDialog.openUsage(pane.path); } },
            { label: "Connect to Server…", action: function () {
                connectDialog.open("Connect to server",
                                   "sftp://user@host/path, smb://host/share or dav://host/path", "");
            } },
            { label: "Mounted Locations", action: function () {
                win.pendingTool = "mounts";
                win.toolId = Backend.call("remote.mounts", {});
            } },
            { label: "Share This Folder…", action: function () {
                win.pendingTool = "share";
                win.toolId = Backend.call("share.start", { path: pane.path });
            } },
            { label: "Stop All Shares", action: function () {
                Backend.call("share.list", {});
            } },
            { label: "Describe with Local LLM", action: function () {
                win.pendingTool = "describe";
                win.toolId = Backend.call("llm.describe", { path: pane.cursorPath() });
            } },
            { label: "Find Duplicates…", action: function () { toolsDialog.openDuplicates(pane.path); } },
            { label: "Compare Folders…", action: function () {
                const other = Config.dualPane ? paneB.path : pane.path;
                compareDialog.open("Compare folders", "Path of the folder to compare with", other);
            } },
            { label: "Tags…", action: function () {
                const paths = pane.selectedPaths();
                Ui.askTags(paths.length > 0 ? paths : [pane.cursorPath()]);
            } },
            { label: "Filter by Tag…", action: function () { Ui.askTagFilter(); } },
            { label: "Clear Tag Filter", action: function () { pane.tagFilter = ""; } },
            { label: "Open Archive…", action: function () { Ui.askArchive(pane.cursorPath()); } },
            { label: "Compress…", action: function () {
                const paths = pane.selectedPaths();
                Ui.askCompress(paths.length > 0 ? paths : [pane.cursorPath()]);
            } },
            { label: "Custom Actions…", action: function () {
                const paths = pane.selectedPaths();
                Ui.askCustomActions(paths.length > 0 ? paths : [pane.cursorPath()]);
            } },
            { label: "Properties…", action: function () { Ui.askProperties(pane.cursorPath()); } },
            { label: "Open Terminal Here", action: function () { pane.openTerminal(); } },
            { label: "Open as Root", action: function () { pane.openAsRoot(); } },
            { label: "Open Trash", action: function () { pane.openTrash(); } },
            { label: "Add to Places", action: function () { pane.addToPlaces(); } },
            { label: "Scan Network", action: function () { Ui.requestNetworkScan(); } },
            { label: "Restore from Trash", action: function () { pane.restoreSelection(); } },
            { label: "Empty Trash", action: function () { Ui.askEmptyTrash(); } },
            { label: "Show/Hide Transfers", action: function () { Config.showTransfers = !Config.showTransfers; } },
            { label: "Select All", action: function () { pane.selectAll(); } },
            { label: "Settings…", action: function () { Ui.askSettings(); } },
            { label: "Quit", action: function () { Qt.quit(); } }
        ];
        for (const item of win.smartFolders) {
            entries.push({
                label: "Search: " + item.name,
                action: function () {
                    searchPanel.openSmart(item.root || pane.path, item.query, item.mode);
                },
            });
        }
        palette.open(entries);
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.background
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Sidebar {
                Layout.preferredWidth: 190
                Layout.fillHeight: true
                pane: win.activePane
                currentPath: win.activePane ? win.activePane.path : ""
                onNavigate: (target) => win.activePane.navigate(target)
                onEmptyTrashRequested: Ui.askEmptyTrash()
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Theme.alpha(Theme.foreground, 0.08)
            }

            Pane {
                id: paneA
                Layout.fillWidth: true
                Layout.fillHeight: true
                initialPath: Config.startPath
                active: true
                watchToken: "paneA"
                onActivated: win.setActivePane(paneA)
            }

            Rectangle {
                visible: Config.dualPane
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Theme.alpha(Theme.foreground, 0.08)
            }

            Pane {
                id: paneB
                visible: Config.dualPane
                Layout.fillWidth: true
                Layout.fillHeight: true
                initialPath: Config.startPath
                active: false
                watchToken: "paneB"
                onActivated: win.setActivePane(paneB)
            }

            Rectangle {
                visible: Config.showPreview
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Theme.alpha(Theme.foreground, 0.08)
            }

            PreviewPanel {
                visible: Config.showPreview
                Layout.preferredWidth: Config.showPreview ? 320 : 0
                Layout.fillHeight: true
            }
        }

        TaskTray {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 96 : 0
        }
    }

    PromptDialog {
        id: renameDialog
        onAccepted: (value) => {
            if (win.renameTarget)
                Backend.call("job.rename", { path: win.renameTarget.path, name: value });
            win.renameTarget = null;
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            win.renameTarget = null;
            Ui.close();
            win.focusActivePane();
        }
    }

    PromptDialog {
        id: newDialog
        onAccepted: (value) => {
            if (win.newTarget)
                Backend.call(win.newTarget.folder ? "job.mkdir" : "job.newfile",
                             { path: win.newTarget.dir, name: value });
            win.newTarget = null;
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            win.newTarget = null;
            Ui.close();
            win.focusActivePane();
        }
    }

    ConfirmDialog {
        id: confirmDialog
        onConfirmed: {
            if (win.deleteTarget)
                Backend.call(win.deleteTarget.permanent ? "job.delete" : "job.trash",
                             { paths: win.deleteTarget.paths });
            win.deleteTarget = null;
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            win.deleteTarget = null;
            Ui.close();
            win.focusActivePane();
        }
    }

    ConflictDialog {
        id: conflictDialog
        onFinished: win.focusActivePane()
    }

    PropertiesDialog {
        id: propertiesDialog
        onClosed: win.focusActivePane()
    }

    OpenWithDialog {
        id: openWithDialog
        onClosed: win.focusActivePane()
    }

    ArchiveDialog {
        id: archiveDialog
        onClosed: win.focusActivePane()
    }

    TagDialog {
        id: tagDialog
        onClosed: win.focusActivePane()
    }

    GitDiffDialog {
        id: gitDiffDialog
        onClosed: win.focusActivePane()
    }

    CustomActionsDialog {
        id: customActionsDialog
        onClosed: win.focusActivePane()
    }

    ToolsDialog {
        id: toolsDialog
        onClosed: win.focusActivePane()
    }

    InfoDialog {
        id: infoDialog
        onClosed: win.focusActivePane()
    }

    PromptDialog {
        id: connectDialog
        title: "Connect to server"
        label: "sftp://user@host/path, smb://host/share or dav://host/path"
        onAccepted: (value) => {
            win.pendingTool = "connect";
            win.toolId = Backend.call("remote.mount", { uri: value.trim() });
            Ui.close();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    PromptDialog {
        id: compareDialog
        title: "Compare folders"
        label: "Path of the folder to compare with"
        onAccepted: (value) => {
            const other = value.trim();
            if (other.length > 0 && win.activePane)
                toolsDialog.openCompare(win.activePane.path, other);
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    PromptDialog {
        id: tagFilterDialog
        title: "Filter by tag"
        label: "Tag name (empty clears the filter)"
        onAccepted: (value) => {
            win.activePane.tagFilter = value.trim();
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    PromptDialog {
        id: saveSearchDialog
        title: "Save this search"
        label: "Name for the smart folder"
        onAccepted: (value) => {
            Backend.call("smart.save", {
                name: value.trim(),
                query: searchPanel.currentQuery(),
                mode: searchPanel.mode,
                root: searchPanel.rootDir,
            });
            win.smartId = Backend.call("smart.list", {});
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    PromptDialog {
        id: compressDialog
        title: "Compress"
        label: "Archive name (.zip, .tar.gz or .tar.xz)"
        onAccepted: (value) => {
            if (win.compressTargets.length === 0)
                return;
            const name = value.trim();
            if (name.length === 0)
                return;
            let format = "zip";
            if (name.endsWith(".tar.gz") || name.endsWith(".tgz"))
                format = "tar.gz";
            else if (name.endsWith(".tar.xz") || name.endsWith(".txz"))
                format = "tar.xz";
            Backend.call("archive.create", {
                paths: win.compressTargets,
                destination: win.compressDir.replace(/\/$/, "") + "/" + name,
                format: format,
            });
            win.compressTargets = [];
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            win.compressTargets = [];
            Ui.close();
            win.focusActivePane();
        }
    }

    SettingsDialog {
        id: settingsDialog
        onClosed: win.focusActivePane()
        onContextMenuRequested: contextMenuDialog.open(win.activePane ? win.activePane.menuCatalog() : [])
    }

    ContextMenuDialog {
        id: contextMenuDialog
        onClosed: settingsDialog.forceActiveFocus()
    }

    NetworkAuthDialog {
        id: networkAuthDialog
        onAccepted: (uri, username, password, domain, anonymous) => {
            Ui.acceptNetworkAuth(uri, username, password, domain, anonymous);
            win.focusActivePane();
        }
        onCancelled: {
            Ui.cancelNetworkAuth();
            win.focusActivePane();
        }
    }

    ConfirmDialog {
        id: emptyTrashDialog
        onConfirmed: {
            Backend.call("job.emptytrash", {});
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    BatchRenameDialog {
        id: batchDialog
        onAccepted: (renames) => {
            Backend.call("job.batchrename", { renames: renames });
            Ui.close();
            win.focusActivePane();
        }
        onCancelled: {
            Ui.close();
            win.focusActivePane();
        }
    }

    SearchPanel {
        id: searchPanel
        onSaveRequested: {
            Ui.askSaveSearch();
            saveSearchDialog.open("Save this search", "Name for the smart folder",
                                  searchPanel.currentQuery());
        }
        onActivated: (entry) => {
            if (entry.dir)
                win.activePane.navigate(entry.path);
            else
                win.activePane.reveal(entry.path);
        }
    }

    CommandPalette {
        id: palette
    }

    Timer {
        id: sessionTimer
        interval: 800
        repeat: false
        onTriggered: win.saveSession()
    }

    Connections {
        target: Backend
        function onResponse(id, result) {
            if (id === win.toolId) {
                win.toolId = -1;
                if (win.pendingTool === "connect") {
                    if (result && result.path && win.activePane)
                        win.activePane.navigate(result.path);
                } else if (win.pendingTool === "share") {
                    infoDialog.show("Folder shared on the local network",
                                    (result && result.url) + "\n\n" +
                                    "Read-only. Anyone on this network can open it " +
                                    "until the app exits or the share is stopped.");
                } else if (win.pendingTool === "describe") {
                    infoDialog.show("Local model description",
                                    (result && result.text) || "No description.");
                } else if (win.pendingTool === "mounts") {
                    const items = (result && result.mounts) || [];
                    const lines = items.map(function (item) {
                        return item.kind + "  " + item.label + "\n    " + item.path;
                    });
                    infoDialog.show("Mounted locations",
                                    lines.length > 0 ? lines.join("\n\n")
                                                     : "Nothing is mounted remotely.");
                }
                win.pendingTool = "";
                return;
            }
            if (id === win.smartId) {
                win.smartId = -1;
                win.smartFolders = (result && result.smart) || [];
                return;
            }
            if (id !== win.sessionId)
                return;
            win.sessionId = -1;
            win.restoring = true;
            if (result && result.session) {
                if (result.session.paneA)
                    paneA.restoreSession(result.session.paneA);
                if (result.session.paneB)
                    paneB.restoreSession(result.session.paneB);
            }
            win.restoring = false;
            win.sessionLoaded = true;
        }
    }

    Connections {
        target: paneA
        function onSessionChanged() { win.scheduleSessionSave(); }
    }

    Connections {
        target: paneB
        function onSessionChanged() { win.scheduleSessionSave(); }
    }

    Component.onCompleted: {
        win.sessionId = Backend.call("session.get", {});
        win.smartId = Backend.call("smart.list", {});
    }

    Connections {
        target: Ui
        function onRenameRequested(path, name) {
            win.renameTarget = { path: path, name: name };
            renameDialog.open("Rename", "New name for " + name, name);
        }
        function onNewRequested(dir, folder) {
            win.newTarget = { dir: dir, folder: folder };
            newDialog.open(folder ? "New folder" : "New file", "Name", folder ? "New Folder" : "untitled.txt");
        }
        function onDeleteRequested(paths, permanent) {
            win.deleteTarget = { paths: paths, permanent: permanent };
            confirmDialog.open(permanent ? "Delete permanently?" : "Move to Trash?",
                               (permanent ? "This cannot be undone. " : "You can restore these from Trash. ")
                               + paths.length + " item(s)");
        }
        function onBatchRenameRequested(paths) {
            batchDialog.open(paths);
        }
        function onPropertiesRequested(path) {
            propertiesDialog.open(path);
        }
        function onOpenWithRequested(path) {
            openWithDialog.open(path);
        }
        function onArchiveRequested(path) {
            archiveDialog.open(path);
        }
        function onCustomActionsRequested(paths) {
            customActionsDialog.open(paths);
        }
        function onGitDiffRequested(path) {
            gitDiffDialog.open(path);
        }
        function onTagsRequested(paths) {
            tagDialog.open(paths);
        }
        function onTagFilterRequested() {
            tagFilterDialog.open("Filter by tag", "Tag name (empty clears the filter)",
                                 win.activePane ? win.activePane.tagFilter : "");
        }
        function onSaveSearchRequested() {
            saveSearchDialog.open("Save this search", "Name for the smart folder",
                                  searchPanel.currentQuery());
        }
        function onCompressRequested(paths) {
            const list = Array.prototype.slice.call(paths || [], 0);
            if (list.length === 0)
                return;
            win.compressTargets = list;
            const dir = list[0].substring(0, list[0].lastIndexOf("/"));
            win.compressDir = dir || "/";
            const base = list[0].substring(list[0].lastIndexOf("/") + 1);
            compressDialog.open("Compress", "Archive name (.zip, .tar.gz or .tar.xz)",
                                (base.replace(/\.[^.]+$/, "") || "archive") + ".zip");
        }
        function onSettingsRequested() {
            settingsDialog.open();
        }
        function onEmptyTrashRequested() {
            emptyTrashDialog.open("Empty Trash?", "Permanently delete all items in the Trash. This cannot be undone.", "Empty Trash");
        }
        function onNetworkAuthRequested(uri, name) {
            networkAuthDialog.open(name || uri, uri);
        }
    }

    Shortcut {
        sequence: "Ctrl+,"
        enabled: !Ui.modalOpen && !Jobs.currentConflict
        onActivated: Ui.askSettings()
    }

    Shortcut {
        sequence: "Ctrl+Shift+F"
        enabled: !Ui.modalOpen && !Jobs.currentConflict
        onActivated: searchPanel.open(win.activePane ? win.activePane.path : Config.startPath)
    }

    Shortcut {
        sequence: "Ctrl+K"
        enabled: !Ui.modalOpen && !Jobs.currentConflict
        onActivated: win.openPalette()
    }

    Shortcut {
        sequence: "Tab"
        enabled: Config.dualPane && !Ui.modalOpen && !Jobs.currentConflict
            && !(win.activePane && (win.activePane.editingPath || win.activePane.filtering))
        onActivated: win.toggleActivePane()
    }

    Shortcut {
        sequence: "Ctrl+J"
        enabled: !Ui.modalOpen
        onActivated: Config.showTransfers = !Config.showTransfers
    }

    Shortcut {
        sequence: "Ctrl+Q"
        onActivated: Qt.quit()
    }
}
