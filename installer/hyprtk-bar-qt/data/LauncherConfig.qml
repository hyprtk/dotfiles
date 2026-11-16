// Application-launcher configuration, read from the bar's own `launcher` block.
//
// Defaults mirror the rofi apps menu the launcher replaces
// (configs/rofi/config-apps-menu.rasi): 700x450, 4x4 icon grid, Papirus-Dark,
// drun/run/filebrowser/window/categories modes, pywal theme via bar Theme.
pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    readonly property string home: Quickshell.env("HOME") || ""
    property var cfg: ({})

    FileView {
        id: cfgFile
        path: root.home + "/.config/hyprtk-bar-qt/config.json"
        watchChanges: true
        blockLoading: true
        printErrors: false
        onLoaded: root._parse()
        onTextChanged: root._parse()
        onFileChanged: reload()
    }
    Component.onCompleted: root._parse()
    function _parse() {
        try {
            root.cfg = (JSON.parse(cfgFile.text()).launcher) || ({});
        } catch (e) {
            root.cfg = ({});
        }
    }

    function _list(name, fallback) {
        const v = root.cfg[name];
        return (Array.isArray(v) && v.length) ? v : fallback;
    }
    function _num(name, fallback) {
        const v = Number(root.cfg[name]);
        return isFinite(v) && v > 0 ? v : fallback;
    }

    readonly property bool enabled: cfg.enabled !== false
    // auto = follow the bar Theme; otherwise a legacy rofi-variant name
    // ported by data/LauncherTheme.qml (no rofi files are read).
    readonly property string theme: cfg.theme || "auto"

    // ── geometry / grid ────────────────────────────────────────────────
    readonly property int width: root._num("width", 700)
    readonly property int height: root._num("height", 450)
    readonly property int columns: root._num("columns", 4)
    readonly property int lines: root._num("lines", 4)
    readonly property int iconSize: root._num("icon_size", 40)
    readonly property int maxResults: {
        const v = Number(root.cfg.max_results);
        return isFinite(v) && v >= 0 ? v : 0; // 0 = unlimited (rofi parity)
    }

    // ── appearance ─────────────────────────────────────────────────────
    readonly property bool showIcons: cfg.show_icons !== false
    readonly property string iconTheme: cfg.icon_theme || "Papirus-Dark"
    readonly property string fallbackIcon: cfg.application_fallback_icon
        || cfg.fallback_icon || "application-x-executable"
    readonly property string placeholder: cfg.placeholder || "Search"
    readonly property bool showModeSwitcher: cfg.show_mode_switcher !== false

    // ── modes ──────────────────────────────────────────────────────────
    readonly property var modes: root._list("modes", ["apps", "categories", "run", "files", "windows"])
    readonly property string defaultMode: {
        const m = cfg.default_mode || "apps";
        return root.modes.indexOf(m) >= 0 ? m : root.modes[0];
    }

    // ── matching / selection ───────────────────────────────────────────
    readonly property bool hoverSelect: cfg.hover_select !== false
    readonly property bool clickToExit: cfg.click_to_exit !== false
    readonly property bool cycle: cfg.cycle !== false
    readonly property bool caseSensitive: cfg.case_sensitive === true
    readonly property bool caseSmart: cfg.case_smart === true
    readonly property bool sort: cfg.sort === true
    readonly property bool tokenize: cfg.tokenize !== false
    readonly property string matching: cfg.matching || "normal"
    readonly property string sortingMethod: cfg.sorting_method || "normal"

    // ── mode-specific formats ──────────────────────────────────────────
    readonly property string drunDisplayFormat: cfg.drun_display_format || "{name}"
    readonly property var drunMatchFields: root._list("drun_match_fields",
        ["name", "generic", "exec", "categories", "keywords"])
    readonly property var drunCategories: root._list("drun_categories", [])
    readonly property var drunExcludeCategories: root._list("drun_exclude_categories", [])
    readonly property string windowFormat: cfg.window_format || "{w} · {c} · {t}"
    readonly property string windowCommand: cfg.window_command || ""
    readonly property bool drunShowActions: cfg.drun_show_actions === true
    readonly property string urlLauncher: cfg.drun_url_launcher || cfg.url_launcher || "xdg-open"

    // ── run mode ───────────────────────────────────────────────────────
    readonly property string terminal: cfg.terminal || "alacritty"
    readonly property string runCommand: cfg.run_command || "{cmd}"
    readonly property string runInTerminal: cfg.run_shell_command
        || cfg.run_in_terminal || "{terminal} -e {cmd}"
    readonly property string runListCommand: cfg.run_list_command || ""
    readonly property bool disableHistory: cfg.disable_history === true
    readonly property int maxHistory: root._num("max_history", 25)

    // ── apps ordering ──────────────────────────────────────────────────
    // Rofi orders drun alphabetically; frecency ranking is opt-in.
    readonly property bool rankByUsage: cfg.rank_by_usage === true

    // ── categories (rofi custom modi's 10 raw desktop categories) ──────
    readonly property var categories: root._list("categories", [
        "AudioVideo", "Development", "Education", "Game", "Graphics",
        "Network", "Office", "Settings", "System", "Utility"
    ])
    readonly property var categoryIcons: cfg.category_icons || ({
        "AudioVideo": "applications-multimedia",
        "Development": "applications-engineering",
        "Education": "accessories-dictionary",
        "Game": "applications-games",
        "Graphics": "applications-graphics",
        "Network": "network-workgroup",
        "Office": "applications-office",
        "Settings": "preferences-system",
        "System": "emblem-system",
        "Utility": "applications-utilities"
    })

    // ── filebrowser ────────────────────────────────────────────────────
    readonly property string filesStart: cfg.files_start || "~"
    readonly property string filesCommand: cfg.files_command || "xdg-open"
    readonly property bool filesShowHidden: cfg.files_show_hidden === true
}
