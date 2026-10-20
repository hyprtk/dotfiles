/*
 * Copyright (c) 2026 Ronin-CK
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Widgets
import "components"

Scope {
    id: root

    property var hyprlandMonitor: Hyprland.focusedMonitor
    property string activeScreenName: hyprlandMonitor ? hyprlandMonitor.name : (Quickshell.screens.length > 0 ? Quickshell.screens[0].name : "")
    property string mode: ["region", "window"].indexOf(Quickshell.env("HQF_MODE")) !== -1 ? Quickshell.env("HQF_MODE") : "region"
    property var modes: ["edit", "region", "window", "temp"]
    property bool tempActive: Quickshell.env("HQF_ACTION") === "temp"
    property bool editActive: Quickshell.env("HQF_ACTION") === "edit"
    property bool shareActive: Quickshell.env("HQF_ACTION") === "share"
    property int connectivityStatus: 0
    property string lastSavedPath: ""
    property string lastTimestamp: ""
    readonly property real targetMenuWidth: (availableModes.length - (editActive ? 1 : 0) - (tempActive ? 1 : 0)) * 100 + 8
    property var theme: themeObj
    property bool capturing: false
    property bool overlaysVisible: true
    // Capture without the frozen overlay. Forced by HQF_FORCE_FALLBACK=1, or
    // used automatically when ScreencopyView never produces a frame (NVIDIA /
    // screencopy failures). HQF_FALLBACK_GEOM is an escape hatch for scripts
    // and tests: when set, slurp is skipped and that geometry is captured.
    readonly property bool fallbackMode: Quickshell.env("HQF_FORCE_FALLBACK") === "1"
    property bool fallbackStarted: false

    // Capabilities probed at startup: the edit tab only exists when an editor
    // is installed, and the share toggle only when kdeconnect-cli is present.
    property var editors: []
    readonly property bool hasEditor: root.editors.length > 0
    property bool kdeconnectAvailable: false
    readonly property var availableModes: root.modes.filter(m => m !== "edit" || root.hasEditor)
    function resolveEditor() {
        const preferred = root.theme && root.theme.annotationTool ? root.theme.annotationTool : "";
        if (preferred && root.editors.indexOf(preferred) >= 0)
            return preferred;
        if (root.editors.indexOf("satty") >= 0)
            return "satty";
        if (root.editors.indexOf("swappy") >= 0)
            return "swappy";
        if (root.editors.indexOf("gradia") >= 0)
            return "gradia";
        return "";
    }
    function parseTOML(text) {
        let result = {
        };
        let section = "";
        const lines = text.split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (!line || line.startsWith("#"))
                continue;

            const secMatch = line.match(/^\[(\w+)\]$/);
            if (secMatch) {
                section = secMatch[1];
                continue;
            }
            const quotedMatch = line.match(/^(\w+)\s*=\s*"([^"]*)"/);
            if (quotedMatch) {
                const rawKey = quotedMatch[1];
                const key = section ? section + rawKey.charAt(0).toUpperCase() + rawKey.slice(1) : rawKey;
                result[key] = quotedMatch[2];
                continue;
            }
            const unquotedMatch = line.match(/^(\w+)\s*=\s*([^\s#]+)/);
            if (unquotedMatch) {
                const rawKey = unquotedMatch[1];
                const key = section ? section + rawKey.charAt(0).toUpperCase() + rawKey.slice(1) : rawKey;
                let val = unquotedMatch[2];
                if (val === "true") {
                    val = true;
                } else if (val === "false") {
                    val = false;
                } else {
                    const num = parseFloat(val);
                    if (!isNaN(num))
                        val = num;

                }
                result[key] = val;
                continue;
            }
        }
        return result;
    }

    function shellEscape(s) {
        return "'" + s.replace(/'/g, "'\\''") + "'";
    }

    function grimGeometry(x, y, width, height, screenName) {
        let target = null;
        for (const m of Hyprland.monitors.values) {
            if (m.name === screenName) { target = m; break; }
        }
        if (!target) target = hyprlandMonitor;
        if (!target || !target.lastIpcObject)
            return "";
        const mx = target.lastIpcObject.x;
        const my = target.lastIpcObject.y;
        return `${Math.round(x + mx)},${Math.round(y + my)} ${Math.round(width)}x${Math.round(height)}`;
    }

    function postSaveHookCmd(filePath) {
        const hook = theme.postSaveHook;
        if (!hook || !filePath)
            return "";

        const fileName = filePath.substring(filePath.lastIndexOf('/') + 1);
        const dirPath = filePath.substring(0, filePath.lastIndexOf('/'));
        let cmd = hook;
        cmd = cmd.replace(/%f/g, shellEscape(filePath));
        cmd = cmd.replace(/%n/g, shellEscape(fileName));
        cmd = cmd.replace(/%d/g, shellEscape(dirPath));
        cmd = cmd.replace(/%t/g, shellEscape(root.lastTimestamp));
        return cmd;
    }

    function runPostSaveHook() {
        const cmd = root.postSaveHookCmd(root.lastSavedPath);
        if (cmd)
            Quickshell.execDetached(["sh", "-c", cmd]);
    }

    function saveScreenshot(x, y, width, height, screenName) {
        const geom = grimGeometry(x, y, width, height, screenName);
        const picturesBase = Quickshell.env("XDG_PICTURES_DIR") || (Quickshell.env("HOME") + "/Pictures");
        const picturesDir = picturesBase + "/Screenshots";
        const timestamp = Qt.formatDateTime(new Date(), "yyyy-MM-dd_hh-mm-ss");
        const outputPath = `${picturesDir}/screenshot-${timestamp}.png`;
        root.lastTimestamp = timestamp;
        root.lastSavedPath = root.tempActive ? "" : outputPath;
        const ePicturesDir = shellEscape(picturesDir);
        const eOutputPath = shellEscape(outputPath);
        const eGeom = geom ? shellEscape(geom) : "";
        const eScreen = root.activeScreenName ? shellEscape(root.activeScreenName) : "";

        const grimRegion = geom
            ? `timeout 5 grim -l 1 -g ${eGeom}`
            : (eScreen ? `timeout 5 grim -l 1 -o ${eScreen}` : `timeout 5 grim -l 1`);

        const shareCmd = "kdeconnect-cli -l 2>/dev/null "
            + "| awk '/reachable/ { for (i = 1; i <= NF; i++) "
            + "if ($i ~ /^[0-9a-f]+$/ && length($i) >= 8) { print $i; exit } }'"
            + " | head -1 | xargs -I{} sh -c"
            + " 'kdeconnect-cli -d {} --share \"$1\" && sleep 0.2"
            + " && kdeconnect-cli -d {} --send-clipboard' --";
        const maybeShare = (escapedPath) => root.shareActive ? ` && ${shareCmd} ${escapedPath}` : "";
        const shareTag = root.shareActive ? " & phone" : "";
        const mkdirCmd = `mkdir -p ${ePicturesDir}`;

        const sattyCommand =
            `${mkdirCmd} && ${grimRegion} - `
            + `| satty --filename - --output-filename ${eOutputPath} --early-exit --init-tool brush --copy-command "wl-copy --type image/png" `
            + `; if [ -f ${eOutputPath} ]; then wl-copy --type image/png < ${eOutputPath}${maybeShare(eOutputPath)}; fi`;
        const swappyCommand =
            `${mkdirCmd} && ${grimRegion} ${eOutputPath} `
            + `&& swappy -f ${eOutputPath} -o ${eOutputPath} `
            + `; if [ -f ${eOutputPath} ]; then wl-copy --type image/png < ${eOutputPath}${maybeShare(eOutputPath)}; fi`;
        // Hyprland 0.55+ (Lua) rejects `hyprctl dispatch exec -- ...`; launch
        // the GUI detached instead and don't block the capture pipeline on it.
        const gradiaCommand =
            `${mkdirCmd} && ${grimRegion} ${eOutputPath} `
            + `&& setsid sh -c 'command -v gradia >/dev/null 2>&1 `
            + `&& exec gradia "$1" || exec flatpak run be.alexandervanhee.gradia "$1"' sh ${eOutputPath} `
            + `>/dev/null 2>&1 < /dev/null &`;
        const defaultSaveCommand =
            `${mkdirCmd} && ${grimRegion} ${eOutputPath} `
            + `&& wl-copy --type image/png < ${eOutputPath}`
            + `${maybeShare(eOutputPath)} `
            + `&& notify-send -a "HyprQuickFrame" -i ${eOutputPath} `
            + `-h string:image-path:${eOutputPath} "Screenshot Saved" `
            + `"Saved to ${picturesDir}"`;
        const eTempSnip = shellEscape(Quickshell.cachePath(`snip-${timestamp}.png`));
        const tempShareCommand =
            `${grimRegion} ${eTempSnip} `
            + `&& wl-copy --type image/png < ${eTempSnip}`
            + `${maybeShare(eTempSnip)} `
            + `&& notify-send -a "HyprQuickFrame" "Screenshot Copied" "Copied to clipboard${shareTag}"; `
            + `rm -f ${eTempSnip}`;
        const tempPlainCommand =
            `${grimRegion} - | wl-copy --type image/png `
            + `&& notify-send -a "HyprQuickFrame" "Screenshot Copied" "Copied to clipboard"`;
        const defaultTempCommand = root.shareActive ? tempShareCommand : tempPlainCommand;

        let cmd;
        if (root.editActive) {
            const editor = root.resolveEditor();
            if (editor === "gradia")
                cmd = gradiaCommand;
            else if (editor === "swappy")
                cmd = swappyCommand;
            else if (editor === "satty")
                cmd = sattyCommand;
            else
                cmd = defaultSaveCommand;
        } else if (root.tempActive)
            cmd = defaultTempCommand;
        else
            cmd = defaultSaveCommand;

        root._pendingCmd = cmd;
        root.capturing = true;
        captureDelayTimer.start();
        
        if (root.editActive)
            hideOverlaysTimer.start();
    }

    // ── no-freeze fallback ─────────────────────────────────────────────
    // A live-screen slurp selection (or the focused output when slurp is not
    // installed). Used when the frozen overlay cannot capture: NVIDIA /
    // screencopy failures, or HQF_FORCE_FALLBACK=1.
    function fallbackCapture() {
        // Leaves the selection in $geom (empty = focused output). Cancelling
        // slurp exits the whole pipeline without capturing.
        return `if command -v slurp >/dev/null 2>&1; then `
            + `geom=$(slurp -b '#00000080' -c '#888888ff' -w 1) || exit 0; `
            + `else geom=""; fi; `;
    }

    function runFallback(reason) {
        if (root.fallbackStarted)
            return;
        root.fallbackStarted = true;
        root.overlaysVisible = false;
        console.warn("HyprQuickFrame: using no-freeze fallback" + (reason ? " (" + reason + ")" : ""));

        const picturesBase = Quickshell.env("XDG_PICTURES_DIR") || (Quickshell.env("HOME") + "/Pictures");
        const picturesDir = picturesBase + "/Screenshots";
        const timestamp = Qt.formatDateTime(new Date(), "yyyy-MM-dd_hh-mm-ss");
        const outputPath = `${picturesDir}/screenshot-${timestamp}.png`;
        root.lastTimestamp = timestamp;
        root.lastSavedPath = root.tempActive ? "" : outputPath;

        const ePicturesDir = shellEscape(picturesDir);
        const eOutputPath = shellEscape(outputPath);
        const eScreen = root.activeScreenName ? shellEscape(root.activeScreenName) : "";
        const forcedGeom = Quickshell.env("HQF_FALLBACK_GEOM") || "";
        const eForcedGeom = forcedGeom ? shellEscape(forcedGeom) : "";
        const mkdirCmd = `mkdir -p ${ePicturesDir}`;

        const selectCmd = forcedGeom
            ? `geom=${eForcedGeom};`
            : root.fallbackCapture();
        const captureCmd = (toStdout) => {
            const out = toStdout ? "-" : eOutputPath;
            return `if [ -n "$geom" ]; then timeout 5 grim -l 1 -g "$geom" ${out}; `
                + `else ${eScreen ? `timeout 5 grim -l 1 -o ${eScreen} ${out}` : `timeout 5 grim -l 1 ${out}`}; fi`;
        };

        const notify = `notify-send -a "HyprQuickFrame"`;
        let cmd;
        if (root.tempActive) {
            cmd = `set -e; ${selectCmd} ${captureCmd(true)} | wl-copy --type image/png `
                + `&& ${notify} "Screenshot Copied" "Copied to clipboard"`;
        } else {
            const hookCmd = root.postSaveHookCmd(outputPath);
            cmd = `set -e; ${mkdirCmd}; ${selectCmd} ${captureCmd(false)} `
                + `&& wl-copy --type image/png < ${eOutputPath} `
                + `&& ${notify} -i ${eOutputPath} -h string:image-path:${eOutputPath} `
                + `"Screenshot Saved" "Saved to ${picturesDir}"`
                + (hookCmd ? ` && ${hookCmd}` : "");
        }

        root._fallbackCmd = cmd;
        // Let the overlay surfaces unmap before slurp grabs the pointer.
        fallbackStartTimer.start();
    }

    property string _fallbackCmd: ""

    Timer {
        id: fallbackStartTimer
        interval: 150
        repeat: false
        onTriggered: {
            Quickshell.execDetached(["sh", "-c", root._fallbackCmd]);
            fallbackQuitTimer.start();
        }
    }

    Timer {
        id: fallbackQuitTimer
        interval: 400
        repeat: false
        onTriggered: Qt.quit()
    }

    property string _pendingCmd: ""

    Timer {
        id: captureDelayTimer
        interval: 100
        repeat: false
        onTriggered: {
            screenshotProcess.command = ["sh", "-c", root._pendingCmd];
            screenshotProcess.running = true;
        }
    }

    Timer {
        id: hideOverlaysTimer
        interval: 300
        repeat: false
        onTriggered: root.overlaysVisible = false
    }

    Component.onCompleted: {
        if (root.fallbackMode) {
            root.runFallback("HQF_FORCE_FALLBACK");
            return;
        }
        editorProbe.running = true;
        shareProbe.running = true;
        readyWatchdog.start();
    }

    Process {
        id: editorProbe
        command: ["sh", "-c", "for t in satty swappy gradia; do command -v \"$t\" >/dev/null 2>&1 && echo \"$t\"; done"]
        stdout: StdioCollector {
            onStreamFinished: {
                const out = this.text.trim();
                root.editors = out ? out.split(/\s+/) : [];
                console.log("HyprQuickFrame: editors:", root.editors.join(",") || "none");
                // Only clear an env-requested edit mode once the probe is final;
                // a transient empty probe must not cancel HQF_ACTION=edit.
                if (root.editors.length === 0)
                    root.editActive = false;
            }
        }
    }

    Process {
        id: shareProbe
        command: ["sh", "-c", "command -v kdeconnect-cli >/dev/null 2>&1"]
        onExited: (code) => {
            root.kdeconnectAvailable = (code === 0);
            if (!root.kdeconnectAvailable)
                root.shareActive = false;
            else
                connectivityProcess.running = true;
        }
    }

    Timer {
        id: readyWatchdog
        interval: 2000
        repeat: false
        onTriggered: {
            for (const w of overlayVariants.instances) {
                if (w && w.isReady) return;
            }
            console.warn("HyprQuickFrame: screencopy never produced a frame.");
            root.runFallback("screencopy unavailable");
        }
    }

    Theme {
        id: themeObj
    }

    FileView {
        id: themeFile

        property string configHome: Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")
        property string userPath1: configHome + "/hyprquickframe/theme.toml"
        property string userPath2: configHome + "/quickshell/HyprQuickFrame/theme.toml"
        property string defaultPath: Quickshell.shellDir.toString().replace(/^file:\/\//, "") + "/theme.toml"

        path: defaultPath
        Component.onCompleted: {
            themePathCheck.command = ["sh", "-c", `if [ -f "${userPath1}" ]; then echo "${userPath1}";
                 elif [ -f "${userPath2}" ]; then echo "${userPath2}";
                 else echo "${defaultPath}"; fi`];
            themePathCheck.running = true;
        }
        onTextChanged: {
            try {
                let rawText = (typeof text === 'function') ? text() : text;
                themeObj.source = root.parseTOML(rawText);
            } catch (e) {
                console.warn("Failed to parse theme.toml:", e);
            }
        }
    }

    Process {
        id: themePathCheck

        running: false

        stdout: StdioCollector {
            onStreamFinished: {
                themeFile.path = this.text.trim();
                console.log("Theme loaded from:", themeFile.path);
            }
        }

    }

    Process {
        id: screenshotProcess

        running: false
        onExited: (code) => {
            if (code !== 0)
                console.error("Screenshot pipeline failed with exit code:", code);
            else
                root.runPostSaveHook();
            Qt.quit();
        }

        stdout: StdioCollector {
            onStreamFinished: {
                if (this.text.trim())
                    console.log(this.text);

            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                if (this.text.trim())
                    console.warn(this.text);

            }
        }

    }

    Process {
        id: connectivityProcess

        command: ["sh", "-c", "timeout 5 kdeconnect-cli -l | grep 'reachable'"]
        onExited: (code) => {
            root.connectivityStatus = (code === 0 ? 1 : 2);
        }
    }

    Variants {
        id: overlayVariants
        model: Quickshell.screens

        FreezeScreen {
            id: overlay

            required property var modelData
            property bool isFocused: modelData.name === root.activeScreenName
            property var themeRef: root.theme
            property var hyprMonitor: {
                const monitors = Hyprland.monitors;
                const monitorsList = (typeof monitors.values === 'function') ? Array.from(monitors.values()) : (monitors.values || monitors);
                for (let i = 0; i < monitorsList.length; i++) {
                    const m = monitorsList[i];
                    if (m && m.name === modelData.name)
                        return m;
                }
                return null;
            }

            targetScreen: modelData
            visible: root.overlaysVisible
            Component.onCompleted: {
                if (isFocused)
                    cursorPosProcess.running = true;
            }

            Process {
                id: cursorPosProcess

                command: ["hyprctl", "cursorpos", "-j"]
                running: false

                stdout: StdioCollector {
                    onStreamFinished: {
                        try {
                            const pos = JSON.parse(this.text.trim());
                            const monitorPos = Qt.point(pos.x - modelData.x, pos.y - modelData.y);
                            regionSelector.mouseX = monitorPos.x;
                            regionSelector.mouseY = monitorPos.y;
                            windowSelector.mouseX = monitorPos.x;
                            windowSelector.mouseY = monitorPos.y;
                        } catch (e) {
                            console.warn("Failed to parse cursorpos:", e);
                        }
                    }
                }

            }

            Shortcut {
                sequences: ["Escape", "q"]
                onActivated: Qt.quit()
            }

            Shortcut {
                sequence: "r"
                onActivated: root.mode = "region"
            }

            Shortcut {
                sequence: "w"
                onActivated: root.mode = "window"
            }

            Shortcut {
                sequence: "s"
                onActivated: {
                    let targetMon = overlay.modelData;
                    if (root.activeScreenName && root.activeScreenName !== targetMon.name) {
                        const screens = Quickshell.screens;
                        for (let i = 0; i < screens.length; i++) {
                            if (screens[i].name === root.activeScreenName) {
                                targetMon = screens[i];
                                break;
                            }
                        }
                    }
                    root.saveScreenshot(0, 0, targetMon.width, targetMon.height, targetMon.name);
                }
            }

            Shortcut {
                sequence: "e"
                onActivated: {
                    root.editActive = !root.editActive;
                    if (root.editActive)
                        root.tempActive = false;

                }
            }

            Shortcut {
                sequence: "t"
                onActivated: {
                    root.tempActive = !root.tempActive;
                    if (root.tempActive)
                        root.editActive = false;

                }
            }

            Shortcut {
                sequence: "k"
                onActivated: {
                    root.shareActive = !root.shareActive;
                    if (root.shareActive && !connectivityProcess.running && root.connectivityStatus !== 0)
                        connectivityProcess.running = true;

                }
            }

            RegionSelector {
                id: regionSelector

                visible: root.mode === "region" && overlay.isReady && !root.capturing
                anchors.fill: parent
                dimOpacity: overlay.themeRef.dimOpacity
                borderRadius: overlay.themeRef.borderRadius
                outlineThickness: overlay.themeRef.outlineThickness
                globalAnimations: overlay.themeRef.animations
                onRegionSelected: (x, y, width, height) => {
                    root.saveScreenshot(x, y, width, height, overlay.modelData.name);
                }
            }

            WindowSelector {
                id: windowSelector

                visible: root.mode === "window" && !root.capturing
                anchors.fill: parent
                monitor: overlay.hyprMonitor
                dimOpacity: overlay.themeRef.dimOpacity
                borderRadius: overlay.themeRef.borderRadius
                outlineThickness: overlay.themeRef.outlineThickness
                animateSelection: overlay.themeRef.animations
                onRegionSelected: (x, y, width, height) => {
                    root.saveScreenshot(x, y, width, height, overlay.modelData.name);
                }
            }

            ControlBar {
                id: segmentedControl

                visible: overlay.isFocused && overlay.isReady && !root.capturing
                modes: root.availableModes
                mode: root.mode
                tempActive: root.tempActive
                editActive: root.editActive
                theme: overlay.themeRef
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: overlay.themeRef ? overlay.themeRef.bottomMargin : 60
                onModeSelected: (m) => {
                    return root.mode = m;
                }
                onTempToggled: {
                    root.tempActive = true;
                    root.editActive = false;
                }
                onEditToggled: {
                    root.editActive = true;
                    root.tempActive = false;
                }
            }

            QuickToggle {
                id: editToggleButton

                visible: overlay.isFocused && !root.capturing && root.hasEditor
                active: root.editActive
                icon: "" // "󰏫"
                imageSource: Qt.resolvedUrl("assets/icons/edit.svg")
                iconColor: overlay.themeRef.toggleEdit
                backgroundColor: overlay.themeRef.toggleBackground
                shadowColor: overlay.themeRef.toggleShadow
                borderColor: overlay.themeRef.barBorder
                borderWidth: 1
                targetX: (overlay.width - root.targetMenuWidth) / 2 - 15 - width
                targetY: segmentedControl.y + segmentedControl.height / 2
                sourceX: overlay.width / 2 - 204 + 32
                onClicked: root.editActive = false
            }

            QuickToggle {
                id: tempToggleButton

                visible: overlay.isFocused && !root.capturing
                active: root.tempActive
                icon: "" // "󰏫"
                imageSource: Qt.resolvedUrl("assets/icons/temp.svg")
                iconColor: overlay.themeRef.toggleTemp
                backgroundColor: overlay.themeRef.toggleBackground
                shadowColor: overlay.themeRef.toggleShadow
                borderColor: overlay.themeRef.barBorder
                borderWidth: 1
                targetX: (overlay.width + root.targetMenuWidth) / 2 + 15
                targetY: segmentedControl.y + segmentedControl.height / 2
                sourceX: overlay.width / 2 - 204 + 332
                onClicked: root.tempActive = false
            }

            QuickToggle {
                id: shareToggleButton

                visible: overlay.isFocused && !root.capturing && root.kdeconnectAvailable
                active: root.shareActive
                icon: ""
                imageSource: root.connectivityStatus === 2 ? Qt.resolvedUrl("assets/icons/share-error.svg") : Qt.resolvedUrl("assets/icons/share.svg")
                iconColor: {
                    if (root.connectivityStatus === 1)
                        return overlay.themeRef.shareConnected;

                    if (root.connectivityStatus === 2)
                        return overlay.themeRef.shareErrorIcon;

                    return overlay.themeRef.sharePending;
                }
                backgroundColor: root.connectivityStatus === 2 ? overlay.themeRef.shareErrorBackground : overlay.themeRef.toggleBackground
                shadowColor: overlay.themeRef.toggleShadow
                borderColor: overlay.themeRef.barBorder
                borderWidth: 1
                pulse: root.connectivityStatus === 0
                targetX: (overlay.width + root.targetMenuWidth) / 2 + 15 + (root.tempActive ? 44 + 10 : 0)
                targetY: segmentedControl.y + segmentedControl.height / 2
                sourceX: overlay.width / 2 + (root.targetMenuWidth / 2) - 22
                onClicked: root.shareActive = false
            }

            Item {
                visible: !root.capturing
                anchors.fill: parent
                z: 999

                HoverHandler {
                    onPointChanged: {
                        root.activeScreenName = overlay.modelData.name;
                        if (root.mode === "region" && !regionSelector.pressed) {
                            regionSelector.mouseX = point.position.x;
                            regionSelector.mouseY = point.position.y;
                        }
                        if (root.mode === "window" && !windowSelector.pressed) {
                            windowSelector.mouseX = point.position.x;
                            windowSelector.mouseY = point.position.y;
                        }
                    }
                }

            }

        }

    }

}
