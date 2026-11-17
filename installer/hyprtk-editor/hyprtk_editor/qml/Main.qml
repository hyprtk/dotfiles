import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "theme"
import "theme/util.js" as Util
import "components"

ApplicationWindow {
    id: win

    visible: true
    minimumWidth: 640
    minimumHeight: 420
    color: win.th.background

    readonly property var th: Bridge.palette
    readonly property var cfg: Bridge.config

    property var docs: []
    property var panes: ({})
    property string activeId: ""
    property int rev: 0
    property bool restoring: false
    property bool forceQuit: false
    property string pendingCloseId: ""
    property bool pendingQuit: false
    property var matches: []
    property int matchIndex: -1
    property var pendingOverwrite: null
    property string pendingReloadId: ""
    // Dirty state is owned here, keyed by document id. QML hands the pane a
    // *copy* of the doc object, so the pane cannot mutate this map's source.
    property var dirty: ({})

    title: win.rev >= 0 ? win.titleText() : ""

    Component {
        id: paneComponent
        EditorPane {}
    }

    // -- helpers ---------------------------------------------------------
    function bump() { rev += 1; }

    function docById(id) {
        for (var i = 0; i < docs.length; i++)
            if (docs[i].id === id)
                return docs[i];
        return null;
    }

    function docIndex(id) {
        for (var i = 0; i < docs.length; i++)
            if (docs[i].id === id)
                return i;
        return -1;
    }

    function activeDoc() { return docById(activeId); }
    function activePane() { return panes[activeId] || null; }

    function setDirty(id, value) {
        if (!id)
            return;
        var map = {};
        for (var key in win.dirty)
            map[key] = win.dirty[key];
        map[id] = value === true;
        win.dirty = map;
        win.rev += 1;
    }

    function isDirty(id) {
        return win.dirty[id] === true;
    }

    function tabLabel(doc) {
        return (doc.title || "Untitled") + (win.isDirty(doc.id) ? " ●" : "");
    }

    function cycleTab(step) {
        if (docs.length < 2)
            return;
        var index = win.docIndex(win.activeId);
        if (index < 0)
            index = 0;
        var next = (index + step + docs.length) % docs.length;
        win.activateTab(docs[next].id);
    }

    function titleText() {
        var doc = activeDoc();
        if (!doc)
            return "Text Editor";
        return (win.isDirty(doc.id) ? "● " : "") + (doc.title || "Untitled") + " — Text Editor";
    }

    function info() {
        var doc = activeDoc();
        if (!doc)
            return { line: 0, col: 0, sel: 0, lines: 0, chars: 0, lang: "", enc: "", eol: "", size: 0, path: "", modified: false };
        var pane = panes[doc.id];
        return {
            line: pane ? pane.cursorLine + 1 : 0,
            col: pane ? pane.cursorColumn + 1 : 0,
            sel: pane ? pane.selectionLength : 0,
            lines: pane ? pane.lineCount : 0,
            chars: pane ? pane.charCount : 0,
            lang: doc.languageName || doc.language || "Plain Text",
            enc: Bridge.encodingLabel(doc.encoding),
            eol: (doc.eol || "lf").toUpperCase(),
            size: doc.size || 0,
            path: doc.path || "",
            modified: win.isDirty(doc.id)
        };
    }

    readonly property var status: win.rev >= 0 ? win.info() : ({})

    // -- documents -------------------------------------------------------
    function addDocument(data, activate) {
        if (!data)
            return "";
        if (!data.id)
            data.id = Bridge.newId();

        if (data.path) {
            for (var i = 0; i < docs.length; i++) {
                if (docs[i].path === data.path && data.path !== "") {
                    activateTab(docs[i].id);
                    return docs[i].id;
                }
            }
        }

        data.modified = data.modified === true;
        if (data.savedText === undefined)
            data.savedText = data.text || "";
        data.language = data.language || "text";
        data.languageName = data.languageName || "Plain Text";
        data.comment = Bridge.commentPrefix(data.language);
        data.cursor = data.cursor || 0;
        data.scroll = data.scroll || 0;

        docs = docs.concat([data]);
        // Assign doc *after* creation: initial properties go through QVariant
        // and hand the pane a copy, so dirty/title state would never reach the
        // tab strip. A direct JS assignment keeps the same object.
        var pane = paneComponent.createObject(editorHost);
        if (pane) {
            pane.doc = data;
            pane.anchors.fill = editorHost;
            // Dirty state lives in the document object: bump the revision so
            // the tab strip and title re-evaluate.
            pane.edited.connect(function () { win.bump(); });
            pane.dirtyChanged.connect(function (value) { win.setDirty(data.id, value); });
            pane.initialize();
        }
        panes[data.id] = pane;
        if (data.modified === true)
            win.setDirty(data.id, true);
        if (activate !== false)
            activateTab(data.id);
        win.bump();
        win.updateWelcome();
        win.scheduleSessionSave();
        return data.id;
    }

    function activateTab(id) {
        if (!panes[id])
            return;
        activeId = id;
        for (var key in panes)
            panes[key].visible = (key === id);
        var pane = panes[id];
        pane.visible = true;
        pane.focusEditor();
        win.bump();
        win.updateWelcome();
        win.scheduleSessionSave();
    }

    function updateWelcome() {
        welcome.visible = docs.length === 0;
    }

    function closeTab(id) {
        var doc = docById(id);
        if (!doc)
            return;
        if (win.isDirty(id) && !doc.readonly) {
            win.pendingCloseId = id;
            closeConfirm.detail = doc.path ? doc.path : "Untitled document";
            closeConfirm.message = "Save your changes before closing?";
            closeConfirm.open();
            return;
        }
        doClose(id);
    }

    function doClose(id) {
        var pane = panes[id];
        Bridge.clearDraft(id);
        Bridge.detach(id);
        if (pane)
            pane.destroy();
        delete panes[id];
        if (win.dirty[id] !== undefined) {
            var clean = {};
            for (var key in win.dirty)
                if (key !== id)
                    clean[key] = win.dirty[key];
            win.dirty = clean;
        }
        var index = docIndex(id);
        docs = docs.filter(function (item) { return item.id !== id; });
        if (activeId === id) {
            var next = docs[Math.min(index, docs.length - 1)];
            activeId = next ? next.id : "";
            if (next)
                activateTab(next.id);
        }
        win.bump();
        win.updateWelcome();
        win.scheduleSessionSave();
    }

    function newDocument() {
        addDocument({
            id: Bridge.newId(),
            path: "",
            title: "Untitled",
            text: "",
            encoding: "utf-8",
            eol: "lf",
            bom: false,
            language: "text",
            languageName: "Plain Text",
            modified: false,
            readonly: false,
            size: 0,
            mtime: 0
        }, true);
    }

    function openPath(path) {
        if (!path)
            return;
        var data = Bridge.load(path);
        if (!data.ok) {
            toast.show(data.error || "Could not open " + path, "error");
            return;
        }
        win.addDocument(data, true);
    }

    function openFiles() {
        var files = Bridge.openDialog();
        for (var i = 0; i < files.length; i++)
            win.openPath(files[i]);
    }

    function saveDoc(id, saveAs, thenClose) {
        var doc = docById(id);
        var pane = panes[id];
        if (!doc || !pane)
            return false;

        var path = doc.path;
        if (saveAs || !path) {
            path = Bridge.saveDialog(path || (doc.title + ".txt"));
            if (!path)
                return false;
        }

        var result = Bridge.save(path, pane.area.text, doc.encoding || "utf-8",
                                 doc.eol || "lf", doc.bom === true, doc.mtime || 0);
        if (!result.ok) {
            if (result.stale) {
                win.pendingOverwrite = { id: id, path: path, thenClose: thenClose };
                overwriteConfirm.open();
                return false;
            }
            toast.show(result.error || "Save failed", "error");
            return false;
        }

        doc.path = path;
        doc.title = result.title || doc.title;
        doc.mtime = result.mtime || 0;
        doc.size = result.size || 0;
        doc.readonly = false;
        if (typeof result.text === "string")
            pane.applySavedText(result.text);
        doc.modified = false;
        win.setDirty(id, false);
        Bridge.setPath(id, path);
        Bridge.clearDraft(id);
        Bridge.addRecent(path);
        win.bump();
        win.scheduleSessionSave();
        toast.show("Saved " + doc.title, "ok");
        if (thenClose)
            win.doClose(id);
        return true;
    }

    function saveActive(saveAs) {
        if (activeId)
            saveDoc(activeId, saveAs, false);
    }

    function overwriteNow() {
        var item = win.pendingOverwrite;
        if (!item)
            return;
        var doc = docById(item.id);
        if (doc)
            doc.mtime = 0;
        win.pendingOverwrite = null;
        win.saveDoc(item.id, false, item.thenClose);
    }

    // -- session and drafts ---------------------------------------------
    function scheduleSessionSave() {
        if (!win.restoring)
            sessionTimer.restart();
    }

    function saveSession() {
        if (win.restoring)
            return;
        var list = [];
        for (var i = 0; i < docs.length; i++) {
            var doc = docs[i];
            var pane = panes[doc.id];
            list.push({
                id: doc.id,
                path: doc.path || "",
                cursor: pane ? pane.area.cursorPosition : 0,
                scroll: pane && pane.scroll ? pane.scroll.contentY : 0,
                language: doc.language || "text",
                encoding: doc.encoding || "utf-8"
            });
        }
        Bridge.saveSession({ active: activeId, docs: list });
    }

    function autosaveDrafts() {
        var seconds = cfg.autosave_seconds || 0;
        if (seconds <= 0)
            return;
        for (var i = 0; i < docs.length; i++) {
            var doc = docs[i];
            var pane = panes[doc.id];
            if (win.isDirty(doc.id) && pane)
                Bridge.saveDraft(doc.id, doc.path || "", doc.title || "Untitled", pane.area.text);
        }
    }

    function restoreSession() {
        var session = Bridge.loadSession();
        if (!cfg.restore_session || !session.docs || session.docs.length === 0) {
            win.updateWelcome();
            win.reportDrafts();
            return;
        }
        win.restoring = true;
        var lastActive = session.active || "";
        for (var i = 0; i < session.docs.length; i++) {
            var entry = session.docs[i];
            if (entry.path) {
                var data = Bridge.load(entry.path);
                if (!data.ok)
                    continue;
                data.id = entry.id || data.id;
                data.cursor = entry.cursor || 0;
                data.scroll = entry.scroll || 0;
                data.language = entry.language || data.language;
                data.languageName = Bridge.detect(entry.path, "").name;
                var draft = Bridge.loadDraft(data.id);
                if (draft && typeof draft.text === "string" && (draft.ts || 0) >= (data.mtime || 0)) {
                    data.savedText = data.text;
                    data.text = draft.text;
                    data.modified = true;
                }
                win.addDocument(data, false);
            } else {
                var draftOnly = Bridge.loadDraft(entry.id);
                if (!draftOnly || typeof draftOnly.text !== "string")
                    continue;
                win.addDocument({
                    id: entry.id,
                    path: "",
                    title: draftOnly.title || "Untitled",
                    text: draftOnly.text,
                    savedText: "",
                    encoding: "utf-8",
                    eol: "lf",
                    bom: false,
                    language: entry.language || "text",
                    languageName: "Plain Text",
                    modified: true,
                    readonly: false,
                    size: 0,
                    mtime: 0
                }, false);
            }
        }
        win.restoring = false;
        if (panes[lastActive])
            win.activateTab(lastActive);
        else if (docs.length > 0)
            win.activateTab(docs[0].id);
        win.updateWelcome();
        win.reportDrafts();
    }

    function reportDrafts() {
        var open = {};
        for (var i = 0; i < docs.length; i++)
            open[docs[i].id] = true;
        var list = Bridge.drafts;
        var extra = 0;
        for (var j = 0; j < list.length; j++)
            if (!open[list[j].id])
                extra++;
        if (extra > 0)
            toast.show(extra + " unsaved document(s) — Ctrl+K → Recover unsaved documents", "info");
    }

    function recoverDrafts() {
        var list = Bridge.drafts;
        var opened = 0;
        for (var i = 0; i < list.length; i++) {
            var entry = list[i];
            if (panes[entry.id])
                continue;
            var draft = Bridge.loadDraft(entry.id);
            if (!draft || typeof draft.text !== "string")
                continue;
            win.addDocument({
                id: entry.id,
                path: draft.path || "",
                title: draft.title || "Recovered",
                text: draft.text,
                savedText: "",
                encoding: "utf-8",
                eol: "lf",
                bom: false,
                language: "text",
                languageName: "Plain Text",
                modified: true,
                readonly: false,
                size: 0,
                mtime: 0
            }, opened === 0);
            opened++;
        }
        if (opened === 0)
            toast.show("Nothing to recover", "info");
        else
            toast.show("Recovered " + opened + " document(s)", "ok");
    }

    // -- search ----------------------------------------------------------
    function openFind(replaceMode) {
        if (!activePane())
            return;
        findBar.replaceMode = replaceMode;
        findBar.visible = true;
        findBar.focusQuery();
        win.runSearch(false);
    }

    function closeFind() {
        findBar.visible = false;
        win.matches = [];
        win.matchIndex = -1;
        if (activeId)
            Bridge.setSearch(activeId, []);
        var pane = activePane();
        if (pane)
            pane.refreshHighlight();
    }

    function runSearch(selectFirst) {
        var pane = activePane();
        if (!pane)
            return;
        var query = findBar.query;
        if (!query) {
            win.matches = [];
            win.matchIndex = -1;
            findBar.matchCount = 0;
            findBar.matchIndex = -1;
            Bridge.setSearch(activeId, []);
            pane.refreshHighlight();
            return;
        }
        win.matches = Bridge.findAll(pane.area.text, query, findBar.caseSensitive,
                                     findBar.wholeWord, findBar.regex);
        win.matchIndex = win.matches.length > 0 ? 0 : -1;
        findBar.matchCount = win.matches.length;
        if (selectFirst !== false && win.matchIndex >= 0)
            win.selectMatch(0);
        win.applyMatchHighlight();
    }

    function applyMatchHighlight() {
        var ranges = [];
        for (var i = 0; i < win.matches.length; i++) {
            ranges.push({
                start: win.matches[i].start,
                length: win.matches[i].length,
                current: i === win.matchIndex
            });
        }
        Bridge.setSearch(activeId, ranges);
        findBar.matchIndex = win.matchIndex;
        var pane = activePane();
        if (pane)
            pane.refreshHighlight();
    }

    function selectMatch(index) {
        var pane = activePane();
        if (!pane || win.matches.length === 0)
            return;
        win.matchIndex = ((index % win.matches.length) + win.matches.length) % win.matches.length;
        var match = win.matches[win.matchIndex];
        pane.selectRange(match.start, match.length);
        win.applyMatchHighlight();
    }

    function findStep(backwards) {
        if (!activePane())
            return;
        if (findBar.query !== "" && win.matches.length === 0)
            win.runSearch(true);
        if (win.matches.length === 0)
            return;
        win.selectMatch(win.matchIndex + (backwards ? -1 : 1));
    }

    function replaceOne() {
        var pane = activePane();
        if (!pane || win.matchIndex < 0 || win.matchIndex >= win.matches.length)
            return;
        var match = win.matches[win.matchIndex];
        pane.area.remove(match.start, match.length);
        pane.area.insert(match.start, findBar.replacement);
        win.runSearch(true);
    }

    function replaceAll() {
        var pane = activePane();
        if (!pane || findBar.query === "")
            return;
        var result = Bridge.replaceAll(pane.area.text, findBar.query, findBar.replacement,
                                       findBar.caseSensitive, findBar.wholeWord, findBar.regex);
        if (result.count > 0) {
            pane.area.text = result.text;
            toast.show("Replaced " + result.count + " occurrence(s)", "ok");
        } else {
            toast.show("No matches", "info");
        }
        win.runSearch(true);
    }

    function gotoLinePrompt() {
        linePrompt.open();
    }

    // -- editing ---------------------------------------------------------
    function lineAction(op) {
        var pane = activePane();
        if (!pane)
            return;
        pane.lineAction(op);
    }

    function setLanguage(alias, name) {
        var pane = activePane();
        if (!pane)
            return;
        pane.setLanguage(alias, name);
        win.bump();
    }

    function setEncoding(encoding) {
        var doc = activeDoc();
        if (!doc)
            return;
        doc.encoding = encoding;
        win.setDirty(doc.id, true);
        win.bump();
        toast.show("Will save as " + encoding.toUpperCase(), "info");
    }

    function setEol(eol) {
        var doc = activeDoc();
        if (!doc)
            return;
        doc.eol = eol;
        win.setDirty(doc.id, true);
        win.bump();
        toast.show("Line endings: " + eol.toUpperCase(), "info");
    }

    function zoom(delta) {
        var size = (cfg.font_size || 13) + delta;
        Bridge.updateSettings({ font_size: Math.max(9, Math.min(32, size)) });
    }

    // -- command palette -------------------------------------------------
    function buildActions() {
        var doc = activeDoc();
        var pane = activePane();
        var actions = [];

        function add(label, hint, run, keywords) {
            actions.push({ label: label, hint: hint || "", run: run, keywords: keywords || "" });
        }

        add("New file", "Ctrl+N", function () { win.newDocument(); });
        add("Open file…", "Ctrl+O", function () { win.openFiles(); });
        add("Save", "Ctrl+S", function () { win.saveActive(false); });
        add("Save as…", "Ctrl+Shift+S", function () { win.saveActive(true); });
        add("Reload from disk", "", function () {
            if (doc && doc.path)
                win.reloadDoc(doc.id);
        });
        add("Close tab", "Ctrl+W", function () { if (activeId) win.closeTab(activeId); });
        add("Recover unsaved documents", "", function () { win.recoverDrafts(); });

        add("Find", "Ctrl+F", function () { win.openFind(false); });
        add("Find and replace", "Ctrl+H", function () { win.openFind(true); });
        add("Find next", "F3", function () { win.findStep(false); });
        add("Find previous", "Shift+F3", function () { win.findStep(true); });
        add("Go to line…", "Ctrl+G", function () { win.gotoLinePrompt(); });

        add("Duplicate line", "Ctrl+Shift+D", function () { win.lineAction("duplicate"); });
        add("Move line up", "Alt+Up", function () { win.lineAction("moveUp"); });
        add("Move line down", "Alt+Down", function () { win.lineAction("moveDown"); });
        add("Delete line", "Ctrl+Shift+K", function () { win.lineAction("deleteLines"); });
        add("Toggle comment", "Ctrl+/", function () { win.lineAction("toggleComment"); });
        add("Sort lines", "", function () { win.lineAction("sortAsc"); });
        add("Sort lines descending", "", function () { win.lineAction("sortDesc"); });
        add("Remove duplicate lines", "", function () { win.lineAction("sortUnique"); });
        add("Trim trailing whitespace", "", function () { win.lineAction("trimTrailing"); });
        add("Join lines", "", function () { win.lineAction("joinLines"); });
        add("Uppercase selection", "", function () { win.lineAction("upper"); });
        add("Lowercase selection", "", function () { win.lineAction("lower"); });
        add("Indent", "Tab", function () { win.lineAction("indent"); });
        add("Outdent", "Shift+Tab", function () { win.lineAction("outdent"); });
        add("Convert indentation to spaces", "", function () { win.lineAction("toSpaces"); });
        add("Convert indentation to tabs", "", function () { win.lineAction("toTabs"); });

        add("Toggle word wrap", "Alt+Z", function () { Bridge.updateSettings({ wrap: !cfg.wrap }); });
        add("Toggle line numbers", "", function () { Bridge.updateSettings({ line_numbers: !cfg.line_numbers }); });
        add("Toggle minimap", "", function () { Bridge.updateSettings({ minimap: !cfg.minimap }); });
        add("Toggle current-line highlight", "", function () { Bridge.updateSettings({ highlight_current_line: !cfg.highlight_current_line }); });
        add("Toggle bracket matching", "", function () { Bridge.updateSettings({ match_brackets: !cfg.match_brackets }); });
        add("Toggle syntax highlighting", "", function () { Bridge.updateSettings({ syntax: !cfg.syntax }); });
        add("Zoom in", "Ctrl+=", function () { win.zoom(1); });
        add("Zoom out", "Ctrl+-", function () { win.zoom(-1); });
        add("Reset zoom", "Ctrl+0", function () { Bridge.updateSettings({ font_size: 13 }); });

        var encodings = ["utf-8", "utf-16-le", "utf-16-be", "iso-8859-1", "cp1252"];
        function addEncoding(enc) {
            add("Encoding: " + Bridge.encodingLabel(enc), "", function () { win.setEncoding(enc); });
        }
        for (var i = 0; i < encodings.length; i++)
            addEncoding(encodings[i]);
        add("Line endings: LF", "", function () { win.setEol("lf"); });
        add("Line endings: CRLF", "", function () { win.setEol("crlf"); });
        add("Line endings: CR", "", function () { win.setEol("cr"); });

        var langs = Bridge.languages;
        function addLanguage(lang) {
            add("Language: " + lang.name, "", function () { win.setLanguage(lang.alias, lang.name); });
        }
        for (var j = 0; j < langs.length; j++)
            addLanguage(langs[j]);

        add("Open containing folder", "", function () {
            if (doc && doc.path)
                Bridge.openInFileManager(doc.path);
        });
        add("Open terminal here", "", function () {
            if (doc && doc.path)
                Bridge.openTerminal(doc.path);
        });
        add("Copy file path", "", function () {
            if (doc && doc.path)
                Bridge.copyToClipboard(doc.path);
        });
        add("Preferences…", "Ctrl+,", function () { settingsDialog.open(); });
        add("About hyprtk-editor", "", function () {
            toast.show("hyprtk-editor " + Bridge.version + " — Qt " + Qt.application.version, "info");
        });

        return actions;
    }

    function openPalette() {
        palette.open(win.buildActions());
    }

    function openSettings() {
        settingsDialog.open();
    }

    function reloadDoc(id) {
        var doc = docById(id);
        var pane = panes[id];
        if (!doc || !pane || !doc.path)
            return;
        var data = Bridge.load(doc.path);
        if (!data.ok) {
            toast.show(data.error || "Reload failed", "error");
            return;
        }
        pane.applySavedText(data.text);
        doc.mtime = data.mtime;
        doc.size = data.size;
        doc.modified = false;
        win.setDirty(id, false);
        pane.doc.language = data.language;
        pane.doc.languageName = Bridge.detect(doc.path, "").name;
        pane.doc.comment = Bridge.commentPrefix(data.language);
        Bridge.setLanguage(id, data.language);
        Bridge.setPath(id, doc.path);
        Bridge.clearDraft(id);
        win.bump();
        toast.show("Reloaded " + doc.title, "ok");
    }

    // -- window state ----------------------------------------------------
    function anyModified() {
        for (var i = 0; i < docs.length; i++)
            if (win.isDirty(docs[i].id))
                return true;
        return false;
    }

    Component.onCompleted: {
        width = (cfg.window && cfg.window.width) || 1100;
        height = (cfg.window && cfg.window.height) || 720;
        var initial = Bridge.initialFiles;
        for (var i = 0; i < initial.length; i++)
            win.openPath(initial[i]);
        if (docs.length === 0)
            win.restoreSession();
        win.updateWelcome();
        win.reportDrafts();
    }

    onClosing: function (close) {
        if (!win.forceQuit && win.anyModified()) {
            close.accepted = false;
            win.pendingQuit = true;
            quitConfirm.open();
            return;
        }
        win.autosaveDrafts();
        win.saveSession();
        Bridge.updateSettings({ window: { width: win.width, height: win.height } });
    }

    // -- layout ----------------------------------------------------------
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Tab strip
        Rectangle {
            Layout.fillWidth: true
            height: 40
            color: Util.alpha(win.th.surface, 0.72)
            visible: win.docs.length > 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                Flickable {
                    Layout.fillWidth: true
                    height: 32
                    clip: true
                    contentWidth: tabsRow.implicitWidth
                    flickableDirection: Flickable.HorizontalFlick
                    boundsBehavior: Flickable.StopAtBounds

                    Row {
                        id: tabsRow
                        height: parent.height
                        spacing: 2

                        Repeater {
                            model: win.docs
                            delegate: Rectangle {
                                id: tab

                                width: Math.min(220, Math.max(110, tabLabel.implicitWidth + 46))
                                height: 32
                                radius: 7
                                color: modelData.id === win.activeId
                                    ? win.th.background
                                    : (tabMouse.containsMouse ? Util.alpha(win.th.surfaceAlt, 0.7) : "transparent")
                                border.width: modelData.id === win.activeId ? 1 : 0
                                border.color: Util.alpha(win.th.accent, 0.35)

                                Text {
                                    id: tabLabel
                                    anchors.left: parent.left
                                    anchors.leftMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 44
                                    text: win.rev >= 0 ? win.tabLabel(modelData) : ""
                                    color: modelData.id === win.activeId ? win.th.foreground : win.th.muted
                                    font.pixelSize: 12
                                    elide: Text.ElideMiddle
                                }

                                MouseArea {
                                    id: tabMouse
                                    anchors.fill: parent
                                    anchors.rightMargin: 24
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: win.activateTab(modelData.id)
                                }

                                IconButton {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 2
                                    anchors.verticalCenter: parent.verticalCenter
                                    glyph: Glyph.close
                                    size: 22
                                    visible: modelData.id === win.activeId || tabMouse.containsMouse
                                    onClicked: win.closeTab(modelData.id)
                                }
                            }
                        }

                        Rectangle {
                            width: 30
                            height: 30
                            radius: 6
                            color: plusMouse.containsMouse ? Util.alpha(win.th.accent2, 0.18) : "transparent"
                            Text {
                                anchors.centerIn: parent
                                text: Glyph.plus
                                color: win.th.muted
                                font.family: Glyph.family
                                font.pixelSize: 12
                            }
                            MouseArea {
                                id: plusMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: win.newDocument()
                            }
                        }
                    }
                }

                FlatButton { text: "Save"; visible: win.docs.length > 0; onClicked: win.saveActive(false) }
                FlatButton { text: "Find"; visible: win.docs.length > 0; onClicked: win.openFind(false) }
                FlatButton { text: "Commands"; onClicked: win.openPalette() }
                IconButton { glyph: Glyph.settings; hint: "Preferences (Ctrl+,)"; onClicked: settingsDialog.open() }
            }
        }

        // Editor area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                id: editorHost
                anchors.fill: parent
            }

            Welcome {
                id: welcome
                anchors.fill: parent
                visible: win.docs.length === 0
                onNewRequested: win.newDocument()
                onOpenRequested: win.openFiles()
                onOpenPath: function (path) { win.openPath(path); }
                onRecoverRequested: win.recoverDrafts()
            }
        }

        // Status bar
        Rectangle {
            Layout.fillWidth: true
            height: 26
            color: Util.alpha(win.th.surface, 0.82)

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: win.status.path || "No document"
                    color: Util.alpha(win.th.muted, 0.9)
                    font.pixelSize: 10
                    elide: Text.ElideMiddle
                }

                Text {
                    visible: win.status.line > 0
                    text: "Ln " + win.status.line + ", Col " + win.status.col
                    color: win.th.muted
                    font.pixelSize: 10
                }
                Text {
                    visible: win.status.sel > 0
                    text: "Sel " + win.status.sel
                    color: win.th.accent2
                    font.pixelSize: 10
                }
                Text {
                    visible: win.status.line > 0
                    text: win.status.lang
                    color: win.th.accent
                    font.pixelSize: 10
                }
                Text {
                    visible: win.status.line > 0
                    text: win.status.enc + " · " + win.status.eol
                    color: Util.alpha(win.th.muted, 0.85)
                    font.pixelSize: 10
                }
                Text {
                    visible: win.status.line > 0
                    text: win.status.lines + " lines"
                    color: Util.alpha(win.th.muted, 0.85)
                    font.pixelSize: 10
                }
                Text {
                    visible: win.docs.length > 0
                    text: win.cfg.wrap ? "wrap" : "no wrap"
                    color: Util.alpha(win.th.muted, 0.7)
                    font.pixelSize: 10
                }
            }
        }
    }

    // -- overlays --------------------------------------------------------
    FindBar {
        id: findBar
        visible: false
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 54
        anchors.rightMargin: 28
        onQueryEdited: searchTimer.restart()
        onNextRequested: win.findStep(false)
        onPreviousRequested: win.findStep(true)
        onReplaceOneRequested: win.replaceOne()
        onReplaceAllRequested: win.replaceAll()
        onClosed: win.closeFind()
    }

    CommandPalette {
        id: palette
        anchors.fill: parent
    }

    SettingsDialog {
        id: settingsDialog
        anchors.fill: parent
    }

    ConfirmDialog {
        id: closeConfirm
        title: "Unsaved changes"
        acceptText: "Save"
        cancelText: "Cancel"
        onAccepted: win.saveDoc(win.pendingCloseId, false, true)
        onCancelled: win.pendingCloseId = ""
    }

    ConfirmDialog {
        id: overwriteConfirm
        title: "File changed on disk"
        message: "This file was modified by another program after you opened it."
        detail: "Saving now overwrites those changes."
        acceptText: "Overwrite"
        danger: true
        onAccepted: win.overwriteNow()
        onCancelled: win.pendingOverwrite = null
    }

    ConfirmDialog {
        id: reloadConfirm
        objectName: "reloadConfirm"
        title: "File changed on disk"
        message: "This file was modified by another program."
        detail: "Reload it and discard the buffer's current contents?"
        acceptText: "Reload"
        onAccepted: {
            if (win.pendingReloadId)
                win.reloadDoc(win.pendingReloadId);
            win.pendingReloadId = "";
        }
        onCancelled: win.pendingReloadId = ""
    }

    ConfirmDialog {
        id: quitConfirm
        title: "Quit with unsaved changes?"
        message: "Drafts are kept in the cache, so nothing is lost — but your tabs will not be restored as modified buffers."
        acceptText: "Quit"
        danger: true
        onAccepted: { win.forceQuit = true; win.close(); }
        onCancelled: win.pendingQuit = false
    }

    PromptDialog {
        id: linePrompt
        title: "Go to line"
        placeholder: "Line number"
        acceptText: "Go"
        onAccepted: function (text) {
            var number = parseInt(text, 10);
            var pane = win.activePane();
            if (pane && !isNaN(number))
                pane.gotoLine(number);
        }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 44
    }

    DropArea {
        anchors.fill: parent
        onDropped: function (drop) {
            for (var i = 0; i < drop.urls.length; i++) {
                var url = drop.urls[i].toString();
                if (url.indexOf("file://") === 0)
                    win.openPath(decodeURIComponent(url.substring(7)));
            }
        }
    }

    Connections {
        target: Bridge
        function onFileChanged(path) {
            for (var i = 0; i < win.docs.length; i++) {
                var doc = win.docs[i];
                if (doc.path !== path)
                    continue;
                var current = Bridge.mtime(path);
                if (!current || Math.abs(current - (doc.mtime || 0)) < 0.001)
                    return;
                if (win.isDirty(doc.id)) {
                    toast.show("Changed on disk — save to overwrite, or Ctrl+K → Reload", "info");
                } else {
                    win.pendingReloadId = doc.id;
                    reloadConfirm.open();
                }
                return;
            }
        }
    }

    Timer {
        id: searchTimer
        interval: 140
        onTriggered: win.runSearch(true)
    }

    Timer {
        id: sessionTimer
        interval: 900
        onTriggered: win.saveSession()
    }

    Timer {
        id: autosaveTimer
        interval: Math.max(1000, (win.cfg.autosave_seconds || 0) * 1000)
        running: (win.cfg.autosave_seconds || 0) > 0
        repeat: true
        onTriggered: win.autosaveDrafts()
    }

    // -- shortcuts -------------------------------------------------------
    Shortcut { sequence: "Ctrl+N"; onActivated: win.newDocument() }
    Shortcut { sequence: "Ctrl+O"; onActivated: win.openFiles() }
    Shortcut { sequence: "Ctrl+S"; onActivated: win.saveActive(false) }
    Shortcut { sequence: "Ctrl+Shift+S"; onActivated: win.saveActive(true) }
    Shortcut { sequence: "Ctrl+W"; onActivated: { if (win.activeId) win.closeTab(win.activeId); } }
    Shortcut { sequence: "Ctrl+F"; onActivated: win.openFind(false) }
    Shortcut { sequence: "Ctrl+H"; onActivated: win.openFind(true) }
    Shortcut { sequence: "F3"; onActivated: win.findStep(false) }
    Shortcut { sequence: "Shift+F3"; onActivated: win.findStep(true) }
    Shortcut { sequence: "Ctrl+G"; onActivated: win.gotoLinePrompt() }
    Shortcut { sequence: "Ctrl+K"; onActivated: win.openPalette() }
    Shortcut { sequence: "Ctrl+Shift+P"; onActivated: win.openPalette() }
    Shortcut { sequence: "Ctrl+,"; onActivated: settingsDialog.open() }
    Shortcut { sequence: "Ctrl+Shift+D"; onActivated: win.lineAction("duplicate") }
    Shortcut { sequence: "Ctrl+Shift+K"; onActivated: win.lineAction("deleteLines") }
    Shortcut { sequence: "Ctrl+/"; onActivated: win.lineAction("toggleComment") }
    Shortcut { sequence: "Alt+Up"; onActivated: win.lineAction("moveUp") }
    Shortcut { sequence: "Alt+Down"; onActivated: win.lineAction("moveDown") }
    Shortcut { sequence: "Alt+Z"; onActivated: Bridge.updateSettings({ wrap: !win.cfg.wrap }) }
    Shortcut { sequence: "Ctrl+="; onActivated: win.zoom(1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: win.zoom(-1) }
    Shortcut { sequence: "Ctrl+0"; onActivated: Bridge.updateSettings({ font_size: 13 }) }
    Shortcut { sequence: "Ctrl+Tab"; onActivated: win.cycleTab(1) }
    Shortcut { sequence: "Ctrl+Shift+Tab"; onActivated: win.cycleTab(-1) }
    Shortcut { sequence: "Esc"; enabled: findBar.visible; onActivated: win.closeFind() }
}
