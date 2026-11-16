// Applies a bar theme — writes the nested `theme` block plus the Qt overrides.
// Every theme change (Themer / Settings) goes through `apply()` so both config
// representations stay in lock-step. The launcher reads the same Theme tokens,
// so it follows the bar theme without any separate theme files.
pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "../config"

Singleton {
    id: root

    readonly property string backend:
        Qt.resolvedUrl("../backend/hyprtk_bar_qt/barsettings.py").toString().replace("file://", "")

    // source: "pywal" | "imported" | "manual" ("" follows pywal); colours optional.
    function apply(source, name, background, foreground, accent) {
        const src = source || "";
        // Live Qt overrides — Theme.qml reads these properties directly (its
        // config FileView does not watch the file), so this is what re-themes
        // the bar immediately.
        Config.themeSource = src;
        Config.themeName = name || "";
        Config.themeBackground = background || "";
        Config.themeForeground = foreground || "";
        Config.themeAccent = accent || "";
        // Persist BOTH representations in one atomic write (barsettings does a
        // whole-file read-modify-write, so two separate writers — Config.save()
        // and a nested patch — race and clobber each other):
        //   • top-level `themeSource`/`themeName`/… = the Qt overrides;
        //   • nested `theme` block = the persisted bar theme.
        const patch = {
            themeSource: src,
            themeName: name || "",
            themeBackground: background || "",
            themeForeground: foreground || "",
            themeAccent: accent || "",
            theme: {
                source: src || "pywal",
                theme_name: name || "",
                background: background || "",
                foreground: foreground || "",
                accent: accent || ""
            }
        };
        setProc.command = ["python3", root.backend, "set", "--json", JSON.stringify(patch)];
        setProc.running = true;
    }

    Process { id: setProc }
}
