// Application launcher — the in-bar replacement for the rofi apps menu.
//
// Modes mirror configs/rofi/config-apps-menu.rasi + the custom categories modi:
//   apps (drun), categories, run, files (filebrowser), windows.
// Behaviour follows rofi 2.1.1's documented keybindings and mode semantics
// (see PLAN-LAUNCHER.md): run lists $PATH executables, Ctrl+Return runs the
// literal input, Shift+Delete removes history (or closes a window, or toggles
// hidden files), Ctrl+L completes with a file, Shift+Return alt-accepts.
//
// Toggle from a keybind via `hyprtk-bar-qt-launcher-toggle` or:
//   qs ipc call launcher toggle
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Widgets
import "../theme"
import "../config"
import "../data"
import "../state"
import "../components"

PanelWindow {
    id: l

    visible: UiState.launcherOpen && LauncherConfig.enabled
    color: "transparent"
    focusable: true
    exclusionMode: ExclusionMode.Ignore
    anchors.top: true
    anchors.bottom: true
    anchors.left: true
    anchors.right: true

    readonly property string home: Quickshell.env("HOME") || ""
    readonly property string backend:
        Qt.resolvedUrl("../backend/hyprtk_bar_qt/launcher.py").toString().replace("file://", "")
    readonly property string filesBackend:
        Qt.resolvedUrl("../backend/hyprtk_bar_qt/files.py").toString().replace("file://", "")

    // ── state ──────────────────────────────────────────────────────────
    property string query: ""
    property string mode: LauncherConfig.defaultMode
    property string category: ""        // categories drill-down ("" = none)
    property int index: 0
    property var usage: ({})            // appId -> launch count
    property var runHistory: []
    property var runExecutables: []     // $PATH, rofi run-mode list
    property string filePath: LauncherConfig.filesStart
    property string fileParent: ""
    property var fileEntries: []
    property bool fileHidden: LauncherConfig.filesShowHidden
    property bool filesDirty: false

    // Toggles that rofi exposes at runtime.
    property var caseForced: -1         // -1 = config, true/false = forced
    property bool sortEnabled: LauncherConfig.sort
    property int ellipsize: Text.ElideRight
    property int historyCursor: -1

    // Ctrl+L "mode complete" (pick a file for the app/command).
    property bool completeActive: false
    property string completeFrom: ""
    property var completeEntry: null
    property string completeQuery: ""

    readonly property var allApps: DesktopEntries.applications.values
    readonly property var modes: LauncherConfig.modes
    readonly property int cols: Math.max(1, LauncherConfig.columns)
    readonly property int rows: Math.max(1, LauncherConfig.lines)
    readonly property string glyphFont: "Symbols Nerd Font"

    // Rofi display glyphs (config-apps-menu.rasi display-* values).
    readonly property var modeMeta: ({
        apps:       { glyph: "\uf009", label: "Applications" },
        categories: { glyph: "\uf00b", label: "Categories" },
        run:        { glyph: "\uf120", label: "Run" },
        files:      { glyph: "\uf07b", label: "Files" },
        windows:    { glyph: "\uf2d0", label: "Windows" }
    })

    // ── lifecycle ──────────────────────────────────────────────────────
    onVisibleChanged: {
        if (!visible)
            return;
        l.query = "";
        l.mode = LauncherConfig.defaultMode;
        l.category = "";
        l.index = 0;
        l.caseForced = -1;
        l.sortEnabled = LauncherConfig.sort;
        l.ellipsize = Text.ElideRight;
        l.historyCursor = -1;
        l.completeActive = false;
        l.completeFrom = "";
        l.completeEntry = null;
        l.completeQuery = "";
        l.fileHidden = LauncherConfig.filesShowHidden;
        l.filePath = l.expandHome(LauncherConfig.filesStart);
        l.fileParent = "";
        l.fileEntries = [];
        l.reloadState();
        l.reloadRunList();
        if (l.mode === "files")
            l.reloadFiles();
        focusTimer.restart();
    }
    Timer { id: focusTimer; interval: 30; onTriggered: entry.forceActiveFocus() }

    function close() { UiState.launcherOpen = false; }

    Shortcut {
        sequence: "Escape"
        enabled: l.visible
        onActivated: l.close()
    }

    // ── generic helpers ────────────────────────────────────────────────
    function norm(s) { return String(s || "").toLowerCase(); }
    function caseNow() {
        if (l.caseForced !== -1)
            return !!l.caseForced;
        if (LauncherConfig.caseSmart) {
            const q = l.query;
            return q !== q.toLowerCase();
        }
        return LauncherConfig.caseSensitive;
    }
    function prep(s) { return l.caseNow() ? String(s || "") : l.norm(s); }
    function cats(e) {
        const c = e ? e.categories : null;
        return Array.isArray(c) ? c : String(c || "").split(/[;,]/).filter(Boolean);
    }
    function keys(e) {
        const k = e ? e.keywords : null;
        return Array.isArray(k) ? k : String(k || "").split(/[;,]/).filter(Boolean);
    }
    function expandHome(p) {
        const s = String(p || "~");
        return s === "~" ? l.home : (s.indexOf("~/") === 0 ? l.home + s.slice(1) : s);
    }
    function fill(fmt, map) {
        let out = String(fmt || "");
        for (const k in map)
            out = out.split("{" + k + "}").join(String(map[k] || ""));
        return out;
    }
    function shq(s) {
        return "'" + String(s || "").replace(/'/g, "'\\''") + "'";
    }
    function iconFor(name) {
        const n = String(name || "").trim();
        return Quickshell.iconPath(n.length ? n : LauncherConfig.fallbackIcon,
                                   LauncherConfig.fallbackIcon);
    }
    function windowIcon(appId) {
        let e = null;
        try {
            e = DesktopEntries.byId(appId)
                || DesktopEntries.byId(appId + ".desktop")
                || DesktopEntries.heuristicLookup(appId);
        } catch (err) {}
        return (e && e.icon) ? e.icon : LauncherConfig.fallbackIcon;
    }
    function nameCmp(a, b) { return l.norm(a.name).localeCompare(l.norm(b.name)); }
    function usageCount(e) { return (l.usage || {})[e.id] || 0; }

    // ── navigation / modes ─────────────────────────────────────────────
    function setMode(m) {
        l.mode = m;
        l.category = "";
        l.index = 0;
        if (m === "files")
            l.reloadFiles();
    }
    function cycleMode(delta) {
        const ms = l.modes;
        if (!ms.length)
            return;
        let i = ms.indexOf(l.mode);
        if (i < 0)
            i = 0;
        i = (i + (delta < 0 ? -1 : 1) + ms.length) % ms.length;
        l.setMode(ms[i]);
    }
    function move(dx, dy) {
        const n = l.results.length;
        if (!n) {
            l.index = 0;
            return;
        }
        let i = l.index + dx + dy * l.cols;
        if (LauncherConfig.cycle)
            i = ((i % n) + n) % n;
        else
            i = Math.max(0, Math.min(n - 1, i));
        l.index = i;
    }

    // ── matching (rofi: normal / regex / glob / fuzzy / prefix) ───────
    function buildPattern(q) {
        const m = LauncherConfig.matching;
        if (m !== "regex" && m !== "glob")
            return null;
        let body = q;
        if (m === "glob") {
            body = "^" + q.replace(/[.+^${}()|[\]\\]/g, "\\$&")
                .replace(/\*/g, ".*").replace(/\?/g, ".") + "$";
        }
        try {
            return new RegExp(body, l.caseNow() ? "" : "i");
        } catch (e) {
            return null;
        }
    }
    function fuzzyScore(text, q) {
        let i = 0, start = -1, last = -1, gaps = 0;
        for (let k = 0; k < text.length && i < q.length; k++) {
            if (text[k] !== q[i])
                continue;
            if (start < 0)
                start = k;
            if (last >= 0)
                gaps += k - last - 1;
            last = k;
            i++;
        }
        return i === q.length ? Math.max(50, 400 - start * 2 - gaps * 4) : -1;
    }
    function scoreText(text, q, rx) {
        if (!q)
            return 1;
        const t = l.prep(text);
        if (rx)
            return rx.test(t) ? 500 : -1;
        if (LauncherConfig.matching === "prefix")
            return t.indexOf(q) === 0 ? 900 - Math.min(t.length, 100) : -1;
        if (t === q)
            return 1000;
        if (t.indexOf(q) === 0)
            return 900 - Math.min(t.length, 100);
        const word = t.indexOf(" " + q);
        if (word >= 0)
            return 800 - Math.min(word, 100);
        const at = t.indexOf(q);
        if (at >= 0)
            return 700 - Math.min(at, 100);
        if (LauncherConfig.matching === "fuzzy" || LauncherConfig.sortingMethod === "fzf")
            return l.fuzzyScore(t, q);
        if (LauncherConfig.tokenize) {
            const toks = q.split(/\s+/).filter(Boolean);
            if (toks.length > 1 && toks.every(tok => t.indexOf(tok) >= 0))
                return 200;
        }
        return -1;
    }
    function appFields(e) {
        const f = LauncherConfig.drunMatchFields;
        const parts = [];
        if (f.indexOf("name") >= 0) parts.push(e.name);
        if (f.indexOf("generic") >= 0) parts.push(e.genericName);
        if (f.indexOf("exec") >= 0) parts.push(e.execString);
        if (f.indexOf("categories") >= 0) parts.push(l.cats(e).join(" "));
        if (f.indexOf("keywords") >= 0) parts.push(l.keys(e).join(" "));
        if (f.indexOf("comment") >= 0) parts.push(e.comment);
        return parts.join(" ");
    }
    function scoreApp(e, q, rx) {
        const s = l.scoreText(e.name, q, rx);
        if (s > 0)
            return s;
        const f = l.scoreText(l.appFields(e), q, rx);
        return f > 0 ? f - 100 : -1;
    }
    function appInCategory(e, cat) {
        return l.cats(e).indexOf(cat) >= 0;
    }

    // ── result lists ───────────────────────────────────────────────────
    readonly property var results: l.buildResults()
    onResultsChanged: {
        if (l.index >= l.results.length)
            l.index = Math.max(0, l.results.length - 1);
    }

    function buildResults() {
        const q = l.prep(l.query.trim());
        const rx = l.buildPattern(q);
        let out = [];
        if (l.mode === "apps")
            out = l.appRows(l.filteredApps(), q, rx);
        else if (l.mode === "categories")
            out = l.categoryResults(q, rx);
        else if (l.mode === "run")
            out = l.runResults(q, rx);
        else if (l.mode === "files")
            out = l.fileResults(q);
        else if (l.mode === "windows")
            out = l.windowResults(q, rx);
        const cap = LauncherConfig.maxResults;
        return cap > 0 ? out.slice(0, cap) : out;
    }

    function filteredApps() {
        let apps = (l.allApps || []).filter(e => !e.noDisplay);
        const inc = LauncherConfig.drunCategories;
        const exc = LauncherConfig.drunExcludeCategories;
        if (inc.length)
            apps = apps.filter(e => inc.some(c => l.appInCategory(e, c)));
        if (exc.length)
            apps = apps.filter(e => !exc.some(c => l.appInCategory(e, c)));
        return apps;
    }

    function appRows(apps, q, rx) {
        let list = apps;
        if (q) {
            list = apps.map(e => ({ e: e, score: l.scoreApp(e, q, rx) }))
                .filter(x => x.score > 0)
                .sort((a, b) => {
                    const d = l.sortEnabled ? b.score - a.score : 0;
                    return d || l.nameCmp(a.e, b.e);
                })
                .map(x => x.e);
        } else {
            // Rofi lists drun alphabetically; usage ranking is opt-in.
            list = apps.slice().sort((a, b) => {
                const d = LauncherConfig.rankByUsage ? l.usageCount(b) - l.usageCount(a) : 0;
                return d || l.nameCmp(a, b);
            });
        }
        return list.map(e => ({
            kind: "app",
            entry: e,
            label: l.fill(LauncherConfig.drunDisplayFormat, {
                name: e.name || "",
                generic: e.genericName || "",
                comment: e.comment || "",
                exec: e.execString || "",
                categories: l.cats(e).join(", ")
            }),
            icon: e.icon || LauncherConfig.fallbackIcon,
            sub: e.genericName || ""
        }));
    }

    function categoryResults(q, rx) {
        if (!l.category) {
            return LauncherConfig.categories
                .filter(c => !q || l.scoreText(c, q, rx) > 0)
                .map(c => ({
                    kind: "category",
                    category: c,
                    label: c,
                    icon: LauncherConfig.categoryIcons[c] || LauncherConfig.fallbackIcon,
                    sub: ""
                }));
        }
        const apps = l.filteredApps().filter(e => l.appInCategory(e, l.category));
        const rows = l.appRows(apps, q, rx);
        rows.unshift({ kind: "back", label: "← Back", icon: "go-previous", sub: l.category });
        return rows;
    }

    function runResults(q, rx) {
        const raw = l.query.trim();
        const out = [];
        const seen = ({});
        for (const cmd of (LauncherConfig.disableHistory ? [] : l.runHistory)) {
            const s = q ? l.scoreText(cmd, q, rx) : 1;
            if (q && s < 0)
                continue;
            seen[cmd] = true;
            out.push({ kind: "run", label: cmd, icon: "utilities-terminal",
                       sub: "History", history: true, _s: s + 1000 });
        }
        for (const exe of l.runExecutables) {
            if (seen[exe])
                continue;
            const s = q ? l.scoreText(exe, q, rx) : 1;
            if (q && s < 0)
                continue;
            seen[exe] = true;
            out.push({ kind: "run", label: exe, icon: "utilities-terminal",
                       sub: "Program", history: false, _s: s });
        }
        if (q)
            out.sort((a, b) => b._s - a._s || String(a.label).localeCompare(String(b.label)));
        // Rofi only runs literal input via Ctrl+Return; show a convenience row
        // when nothing matches so Enter has something to do.
        if (raw && out.length === 0)
            out.push({ kind: "run", label: raw, icon: "utilities-terminal",
                       sub: "Run command", history: false, _s: 0 });
        return out;
    }

    function fileResults(q) {
        const out = [];
        if (l.fileParent && l.fileParent !== l.filePath)
            out.push({ kind: "file", path: l.fileParent, isDir: true, label: "..",
                       icon: "go-up", sub: "" });
        for (const f of l.fileEntries) {
            if (q && l.prep(f.name).indexOf(q) < 0)
                continue;
            out.push({
                kind: "file",
                path: f.path,
                isDir: !!f.is_dir,
                label: f.name,
                icon: f.is_dir ? "folder" : "text-x-generic",
                sub: ""
            });
        }
        return out;
    }

    function windowResults(q, rx) {
        const out = [];
        for (const t of (Hyprland.toplevels.values || [])) {
            const appId = (t.wayland && t.wayland.appId) ? String(t.wayland.appId) : "";
            const ws = t.workspace ? t.workspace.id : "";
            const title = t.title || "";
            const hay = ws + " " + appId + " " + title;
            if (q && l.scoreText(hay, q, rx) < 0)
                continue;
            out.push({
                kind: "window",
                addr: t.address,
                label: l.fill(LauncherConfig.windowFormat,
                              { w: ws, c: appId, t: title, n: appId, r: "" }),
                icon: l.windowIcon(appId),
                sub: t.activated ? "Focused" : ""
            });
        }
        return out;
    }

    // ── actions ────────────────────────────────────────────────────────
    function accept(alt) {
        const it = l.results[l.index];
        if (!it)
            return;
        if (it.kind === "app") {
            l.acceptApp(it, alt);
        } else if (it.kind === "category") {
            l.category = it.category;
            l.query = "";
            l.index = 0;
            entry.forceActiveFocus();
        } else if (it.kind === "back") {
            l.category = "";
            l.query = "";
            l.index = 0;
            entry.forceActiveFocus();
        } else if (it.kind === "run") {
            l.runCommand(it.label, alt);
        } else if (it.kind === "file") {
            if (l.completeActive && !it.isDir) {
                l.finishComplete(it.path);
            } else if (it.isDir) {
                l.filePath = it.path;
                l.query = "";
                l.index = 0;
                l.reloadFiles();
                entry.forceActiveFocus();
            } else {
                l.close();
                l.openFile(it.path);
            }
        } else if (it.kind === "window") {
            if (alt)
                l.windowAlt(it);
            else {
                l.close();
                l.focusWindow(it);
            }
        }
    }

    function acceptApp(it, alt) {
        const e = it.entry;
        l.close();
        if (alt) {
            l.runInTerminalApp(e);
        } else {
            const hasExec = (e.execString && e.execString.length)
                || (e.command && e.command.length);
            if (!hasExec) {
                l.openEntryInfo(e.id);       // rofi: Link entries -> url launcher
            } else {
                try {
                    e.execute();
                } catch (err) {
                    l.openEntryInfo(e.id);
                }
            }
        }
        l.recordApp(e.id);
    }

    function acceptCustom(altTerminal) {
        const raw = l.query.trim();
        if (!raw)
            return;
        if (altTerminal) {
            l.close();
            l.execInTerminal(raw);
            l.recordRun(raw);
        } else {
            l.runCommand(raw, false);
        }
    }

    function readCommand(e) {
        try {
            return (e.command && e.command.length)
                ? e.command.join(" ") : (e.execString || "");
        } catch (err) {
            return e.execString || "";
        }
    }
    function runInTerminalApp(e) {
        const cmd = l.readCommand(e).replace(/%[a-zA-Z]/g, "").trim();
        if (cmd)
            l.execInTerminal(cmd);
    }
    function execInTerminal(cmd) {
        const line = l.fill(LauncherConfig.runInTerminal,
                            { terminal: LauncherConfig.terminal, cmd: cmd });
        Quickshell.execDetached(["sh", "-c", line + " &"]);
    }
    function runCommand(cmd, alt) {
        if (!cmd)
            return;
        l.close();
        if (alt) {
            l.execInTerminal(cmd);
        } else {
            const line = l.fill(LauncherConfig.runCommand, { cmd: cmd });
            const bg = /[&;]\s*$/.test(line) ? "" : " &";
            Quickshell.execDetached(["sh", "-c", line + bg]);
        }
        l.recordRun(cmd);
    }
    function openFile(path) {
        const cmd = LauncherConfig.filesCommand;
        const line = cmd.indexOf("{file}") >= 0
            ? cmd.split("{file}").join(l.shq(path))
            : cmd + " " + l.shq(path);
        Quickshell.execDetached(["sh", "-c", line]);
    }

    function focusWindow(it) {
        if (!it || !it.addr)
            return;
        // Restore windows parked on a special workspace, like the tasklist.
        for (const t of (Hyprland.toplevels.values || [])) {
            if (String(t.address) !== String(it.addr))
                continue;
            const ws = t.workspace ? t.workspace.id : 0;
            if (ws < 0) {
                const aw = Hyprland.focusedWorkspace;
                if (aw)
                    Hyprland.dispatch(Hypr.moveWindowTo(aw.name || String(aw.id), it.addr));
            }
            break;
        }
        Hyprland.dispatch(Hypr.focusWindow(it.addr));
    }
    function windowAlt(it) {
        l.close();
        if (!it || !it.addr)
            return;
        if (LauncherConfig.windowCommand) {
            const id = "0x" + String(it.addr).replace(/^0x/, "");
            Quickshell.execDetached(["sh", "-c",
                LauncherConfig.windowCommand.split("{window}").join(id)]);
            return;
        }
        // Wayland has no wmctrl; rofi's default action is "raise the window".
        l.focusWindow(it);
    }

    function openEntryInfo(id) {
        if (!id)
            return;
        infoProc.command = ["python3", l.backend, "entry-info", String(id)];
        infoProc.running = true;
    }

    // Shift+Delete: history removal / close window / toggle hidden files.
    function deleteEntry() {
        if (l.mode === "files") {
            l.fileHidden = !l.fileHidden;
            l.reloadFiles();
            return;
        }
        const it = l.results[l.index];
        if (!it)
            return;
        if (it.kind === "window") {
            Hyprland.dispatch(Hypr.closeWindow(it.addr));
        } else if (it.kind === "app") {
            l.forgetApp(it.entry.id);
        } else if (it.kind === "run" && it.history) {
            l.forgetRun(it.label);
        }
    }

    // Ctrl+space: put the selected entry into the input (rofi kb-row-select).
    function rowSelect() {
        const it = l.results[l.index];
        if (!it)
            return;
        let text = it.label || "";
        if (it.kind === "app")
            text = it.entry.name || "";
        entry.text = text;
        entry.cursorPosition = entry.text.length;
    }

    function toggleCase() { l.caseForced = !l.caseNow(); }
    function toggleSort() { l.sortEnabled = !l.sortEnabled; }
    function cycleEllipsize() {
        if (l.ellipsize === Text.ElideRight)
            l.ellipsize = Text.ElideMiddle;
        else if (l.ellipsize === Text.ElideMiddle)
            l.ellipsize = Text.ElideLeft;
        else if (l.ellipsize === Text.ElideLeft)
            l.ellipsize = Text.ElideNone;
        else
            l.ellipsize = Text.ElideRight;
    }

    function entryHistory(dir) {
        if (l.mode !== "run" || LauncherConfig.disableHistory || l.runHistory.length === 0)
            return;
        l.historyCursor = Math.max(-1, Math.min(l.runHistory.length - 1,
                                                l.historyCursor + (dir < 0 ? 1 : -1)));
        const text = l.historyCursor >= 0 ? l.runHistory[l.historyCursor] : "";
        entry.text = text;
        entry.cursorPosition = text.length;
    }

    // Ctrl+L: rofi mode-complete — pick a file, launch the app with it.
    function startComplete() {
        if (l.mode !== "apps" && l.mode !== "run")
            return;
        const it = l.results[l.index];
        l.completeActive = true;
        l.completeFrom = l.mode;
        l.completeEntry = (l.mode === "apps" && it && it.kind === "app") ? it.entry : null;
        l.completeQuery = l.query;
        l.query = "";
        l.setMode("files");
        entry.forceActiveFocus();
    }
    function finishComplete(path) {
        const from = l.completeFrom;
        const entryObj = l.completeEntry;
        const q = l.completeQuery;
        l.completeActive = false;
        l.completeFrom = "";
        l.completeEntry = null;
        l.completeQuery = "";
        l.close();
        if (from === "apps" && entryObj) {
            let cmd = l.readCommand(entryObj);
            const hasField = /%[fFuU]/.test(cmd);
            cmd = cmd.replace(/%[fFuU]/g, path).replace(/%[a-zA-Z]/g, "");
            if (!hasField)
                cmd += " " + l.shq(path);
            if (cmd.trim())
                Quickshell.execDetached(["sh", "-c", cmd + " &"]);
            l.recordApp(entryObj.id);
        } else if (q) {
            Quickshell.execDetached(["sh", "-c", q + " " + l.shq(path) + " &"]);
        } else if (from === "run") {
            Quickshell.execDetached(["sh", "-c", l.shq(path) + " &"]);
        }
    }

    // ── backend state (frecency + run history) ─────────────────────────
    Process {
        id: stateLoadProc
        command: ["python3", l.backend, "get"]
        running: false
        stdout: SplitParser {
            onRead: line => {
                try {
                    const s = JSON.parse(line);
                    l.usage = s.apps || ({});
                    l.runHistory = s.run || [];
                } catch (e) {}
            }
        }
    }
    Process {
        id: mutateProc
        onExited: (code, status) => {
            if (code !== 0)
                console.warn("hyprtk-bar-qt launcher: state write failed (" + code + ")");
        }
    }
    function reloadState() {
        if (!stateLoadProc.running)
            stateLoadProc.running = true;
    }
    function recordApp(id) {
        if (!id || LauncherConfig.disableHistory)
            return;
        mutateProc.command = ["python3", l.backend, "record-app", String(id)];
        mutateProc.running = true;
    }
    function recordRun(cmd) {
        if (!cmd || LauncherConfig.disableHistory)
            return;
        mutateProc.command = ["python3", l.backend, "record-run", String(cmd),
                              "--max", String(LauncherConfig.maxHistory)];
        mutateProc.running = true;
    }
    function forgetApp(id) {
        if (!id)
            return;
        const u = Object.assign({}, l.usage);
        delete u[id];
        l.usage = u;
        mutateProc.command = ["python3", l.backend, "forget-app", String(id)];
        mutateProc.running = true;
    }
    function forgetRun(cmd) {
        l.runHistory = l.runHistory.filter(c => c !== cmd);
        mutateProc.command = ["python3", l.backend, "forget-run", String(cmd)];
        mutateProc.running = true;
    }

    // ── run-mode executable list (rofi scans $PATH) ───────────────────
    Process {
        id: runListProc
        stdout: StdioCollector {
            onStreamFinished: {
                const out = String(text || "").trim();
                if (!out) {
                    l.runExecutables = [];
                    return;
                }
                if (LauncherConfig.runListCommand) {
                    l.runExecutables = out.split(/\n/).map(s => s.trim()).filter(Boolean);
                    return;
                }
                try {
                    const v = JSON.parse(out);
                    l.runExecutables = Array.isArray(v) ? v : [];
                } catch (e) {
                    l.runExecutables = [];
                }
            }
        }
    }
    function reloadRunList() {
        if (runListProc.running)
            return;
        runListProc.command = LauncherConfig.runListCommand
            ? ["sh", "-c", LauncherConfig.runListCommand]
            : ["python3", l.backend, "run-list"];
        runListProc.running = true;
    }

    // ── filebrowser data ───────────────────────────────────────────────
    Process {
        id: filesProc
        stdout: SplitParser {
            onRead: line => {
                try {
                    const d = JSON.parse(line);
                    l.filePath = d.path || l.filePath;
                    l.fileParent = d.parent || "";
                    l.fileEntries = d.entries || [];
                } catch (e) {}
            }
        }
        onExited: (code, status) => {
            if (l.filesDirty)
                l.reloadFiles();
        }
    }
    function reloadFiles() {
        if (filesProc.running) {
            l.filesDirty = true;
            return;
        }
        l.filesDirty = false;
        const args = ["python3", l.filesBackend, "list", l.filePath];
        if (l.fileHidden)
            args.push("--hidden");
        filesProc.command = args;
        filesProc.running = true;
    }

    // Link/URL entries: Quickshell's DesktopEntry does not expose Type/URL.
    Process {
        id: infoProc
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const d = JSON.parse(String(text || ""));
                    if (d && d.url)
                        Quickshell.execDetached([LauncherConfig.urlLauncher, d.url]);
                    else if (d && d.exec)
                        Quickshell.execDetached(["sh", "-c", d.exec + " &"]);
                } catch (e) {}
            }
        }
    }

    // ── scrim (rofi click-to-exit + right-click cancel) ────────────────
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: (mouse) => {
                if (mouse.button === Qt.RightButton || LauncherConfig.clickToExit)
                    l.close();
            }
        }
    }

    // ── panel ──────────────────────────────────────────────────────────
    Rectangle {
        id: panel
        width: Math.min(LauncherConfig.width, l.width - 40)
        height: Math.min(LauncherConfig.height, l.height - 80)
        anchors.centerIn: parent
        radius: 16
        color: LauncherTheme.panelColor
        border.width: Math.max(1, BarConfig.borderWidth)
        border.color: LauncherTheme.borderColor

        // Right-click inside the panel cancels like rofi (MouseSecondary).
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            onClicked: l.close()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            // ── input bar + mode switcher ─────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                // Category drill-down prompt (rofi's custom modi prompt).
                ChipButton {
                    visible: l.mode === "categories" && l.category.length > 0
                    label: l.category
                    implicitHeight: 32
                    baseColor: LauncherTheme.chipBg
                    hoverColor: LauncherTheme.chipHover
                    textColor: LauncherTheme.foreground
                    onTapped: {
                        l.category = "";
                        l.query = "";
                        l.index = 0;
                        entry.forceActiveFocus();
                    }
                }

                TTextField {
                    id: entry
                    Layout.preferredWidth: 300
                    Layout.maximumWidth: 300
                    Layout.minimumWidth: 180
                    implicitHeight: 40
                    radius: 100
                    font.pixelSize: BarConfig.scaled(14)
                    leftPadding: 16
                    rightPadding: 16
                    color: LauncherTheme.foreground
                    placeholderTextColor: LauncherTheme.dim
                    backgroundColor: LauncherTheme.inputBg
                    focusBorderColor: LauncherTheme.accent
                    idleBorderColor: LauncherTheme.inputBorder
                    placeholderText: LauncherConfig.placeholder
                    onTextChanged: {
                        l.query = text;
                        l.index = 0;
                    }

                    // rofi 2.1.1 keybindings (PLAN-LAUNCHER.md §1).
                    Keys.onPressed: (event) => {
                        const mod = event.modifiers;
                        const ctrl = (mod & Qt.ControlModifier) !== 0;
                        const shift = (mod & Qt.ShiftModifier) !== 0;
                        const alt = (mod & Qt.AltModifier) !== 0;
                        const meta = (mod & Qt.MetaModifier) !== 0;

                        // kb-select-1..10 (Super+1..0)
                        if (meta && ((event.key >= Qt.Key_1 && event.key <= Qt.Key_9)
                                     || event.key === Qt.Key_0)) {
                            const n = event.key === Qt.Key_0 ? 9 : event.key - Qt.Key_1;
                            if (n < l.results.length) {
                                l.index = n;
                                l.accept(false);
                            }
                            event.accepted = true;
                            return;
                        }

                        switch (event.key) {
                        case Qt.Key_Escape:
                            l.close();
                            break;
                        case Qt.Key_G:
                            if (!ctrl) return;
                            l.close();
                            break;
                        case Qt.Key_BracketLeft:
                            if (!ctrl) return;
                            l.close();
                            break;
                        case Qt.Key_Up:
                            if (ctrl) l.entryHistory(-1);
                            else l.move(0, -1);
                            break;
                        case Qt.Key_Down:
                            if (ctrl) l.entryHistory(1);
                            else l.move(0, 1);
                            break;
                        case Qt.Key_P:
                            if (!ctrl) return;
                            l.move(0, -1);
                            break;
                        case Qt.Key_N:
                            if (!ctrl) return;
                            l.move(0, 1);
                            break;
                        case Qt.Key_PageUp:
                            if (ctrl) l.move(-1, 0);
                            else l.move(0, -l.rows);
                            break;
                        case Qt.Key_PageDown:
                            if (ctrl) l.move(1, 0);
                            else l.move(0, l.rows);
                            break;
                        case Qt.Key_Home:
                            l.index = 0;
                            break;
                        case Qt.Key_End:
                            l.index = Math.max(0, l.results.length - 1);
                            break;
                        case Qt.Key_Tab:
                            if (ctrl) l.cycleMode(1);
                            else l.move(1, 0);
                            break;
                        case Qt.Key_Backtab:
                            if (ctrl) l.cycleMode(-1);
                            else l.move(-1, 0);
                            break;
                        case Qt.Key_Right:
                            if (shift) l.cycleMode(1);
                            else return;    // text cursor (rofi parity)
                            break;
                        case Qt.Key_Left:
                            if (shift) l.cycleMode(-1);
                            else return;
                            break;
                        case Qt.Key_Delete:
                            if (!shift) return;
                            l.deleteEntry();
                            break;
                        case Qt.Key_Space:
                            if (!ctrl) return;
                            l.rowSelect();
                            break;
                        case Qt.Key_L:
                            if (!ctrl) return;
                            l.startComplete();
                            break;
                        case Qt.Key_W:
                            if (!ctrl) return;
                            entry.text = "";
                            break;
                        case Qt.Key_U:
                            if (!ctrl) return;
                            entry.text = entry.text.slice(entry.cursorPosition);
                            entry.cursorPosition = 0;
                            break;
                        case Qt.Key_K:
                            if (!ctrl) return;
                            entry.text = entry.text.slice(0, entry.cursorPosition);
                            break;
                        case Qt.Key_QuoteLeft:
                            if (alt) l.toggleSort();
                            else l.toggleCase();
                            break;
                        case Qt.Key_Period:
                            if (!alt) return;
                            l.cycleEllipsize();
                            break;
                        case Qt.Key_Return:
                        case Qt.Key_Enter:
                            if (ctrl) l.acceptCustom(false);
                            else l.accept(shift);
                            break;
                        case Qt.Key_J:
                        case Qt.Key_M:
                            if (!ctrl) return;
                            l.accept(shift);
                            break;
                        default:
                            return;
                        }
                        event.accepted = true;
                    }
                }

                Item { Layout.fillWidth: true; Layout.minimumWidth: 0 }

                Repeater {
                    model: LauncherConfig.showModeSwitcher ? l.modes : []
                    Rectangle {
                        id: modeBtn
                        required property string modelData
                        readonly property var meta: l.modeMeta[modelData] || ({ glyph: "?", label: modelData })
                        implicitWidth: 36
                        implicitHeight: 36
                        radius: 5
                        color: l.mode === modelData ? LauncherTheme.selectedBg : LauncherTheme.buttonBg
                        border.width: 1
                        border.color: LauncherTheme.borderColor

                        Text {
                            anchors.centerIn: parent
                            text: modeBtn.meta.glyph
                            color: l.mode === modeBtn.modelData ? LauncherTheme.selectedFg : LauncherTheme.foreground
                            font.family: l.glyphFont
                            font.pixelSize: BarConfig.scaled(15)
                        }
                        ToolTip.visible: modeHover.hovered
                        ToolTip.text: modeBtn.meta.label
                        ToolTip.delay: 400
                        HoverHandler { id: modeHover }
                        TapHandler { onTapped: l.setMode(modeBtn.modelData) }
                    }
                }
            }

            // ── result grid ───────────────────────────────────────────
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                GridView {
                    id: grid
                    anchors.fill: parent
                    cellWidth: Math.floor(width / l.cols)
                    cellHeight: Math.floor(height / l.rows)
                    model: l.visible ? l.results : []
                    currentIndex: l.index
                    // selection is driven by l.index (rofi keeps the entry
                    // focused, so the grid must not steal keyboard focus)
                    interactive: false
                    focus: false
                    clip: true

                    delegate: Rectangle {
                        id: cell
                        required property int index
                        required property var modelData
                        width: grid.cellWidth - 10
                        height: grid.cellHeight - 10
                        radius: 5
                        color: cell.index === l.index ? LauncherTheme.selectedBg : LauncherTheme.cellBg
                        border.width: cell.index === l.index ? 0 : 1
                        border.color: LauncherTheme.cellBorder

                        Column {
                            anchors.centerIn: parent
                            width: cell.width - 8
                            spacing: 3

                            Image {
                                anchors.horizontalCenter: parent.horizontalCenter
                                visible: LauncherConfig.showIcons
                                source: l.iconFor(cell.modelData.icon)
                                sourceSize.width: LauncherConfig.iconSize
                                sourceSize.height: LauncherConfig.iconSize
                                asynchronous: true
                            }
                            Text {
                                width: parent.width
                                text: cell.modelData.label || ""
                                color: cell.index === l.index ? LauncherTheme.selectedFg : LauncherTheme.foreground
                                font.family: Theme.fontFamily
                                font.pixelSize: BarConfig.scaled(11)
                                horizontalAlignment: Text.AlignHCenter
                                elide: l.ellipsize
                                wrapMode: Text.NoWrap
                            }
                            Text {
                                width: parent.width
                                visible: text.length > 0 && cell.index !== l.index
                                text: cell.modelData.sub || ""
                                color: LauncherTheme.dim
                                font.pixelSize: BarConfig.scaled(9)
                                horizontalAlignment: Text.AlignHCenter
                                elide: l.ellipsize
                            }
                        }

                        HoverHandler {
                            id: cellHover
                            onHoveredChanged: {
                                if (hovered && LauncherConfig.hoverSelect)
                                    l.index = cell.index;
                            }
                        }
                        TapHandler {
                            onTapped: {
                                l.index = cell.index;
                                l.accept(false);
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: l.results.length === 0
                    text: l.mode === "run" ? "Type a command…"
                        : l.mode === "files" ? "Empty folder"
                        : l.mode === "windows" ? "No matching windows"
                        : "No matches"
                    color: LauncherTheme.dim
                    font.family: Theme.fontFamily
                    font.pixelSize: BarConfig.scaled(12)
                }

                WheelHandler {
                    onWheel: (event) => {
                        const ax = Math.abs(event.angleDelta.x);
                        const ay = Math.abs(event.angleDelta.y);
                        if (ax > ay)
                            l.move(event.angleDelta.x > 0 ? 1 : -1, 0);
                        else
                            l.move(0, event.angleDelta.y > 0 ? -1 : 1);
                        event.accepted = true;
                    }
                }
            }
        }
    }

    // Keep the selected cell visible when moving past the 4×4 page.
    onIndexChanged: {
        if (l.index >= 0 && grid.count > 0 && l.index < grid.count)
            grid.positionViewAtIndex(l.index, GridView.Contain);
    }
}
