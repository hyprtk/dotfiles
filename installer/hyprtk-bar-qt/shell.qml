// hyprtk-bar-qt — Quickshell entry point.
//
// QML presentation layer of the Qt rewrite. One layer-shell PanelWindow per
// screen, each rendering Bar.qml, plus the surfaces (quick settings, settings,
// arc menu, bar menu, start menu, themer). Heavy logic lives in the Python
// backend (backend/hyprtk_bar_qt) and is streamed in over Quickshell Process.
import Quickshell
import Quickshell.Io
import QtQuick
import "bar"
import "surface"
import "config"
import "state"
import "data"

ShellRoot {
    id: shell

    // Instantiate the keybind signal bridge (menu/arc/clipboard toggles) and the
    // theme writer (persists bar theme changes).
    readonly property var signalBridge: SignalBridge
    readonly property var themeSync: ThemeSync
    readonly property var lockSync: LockSync

    // Screens that should show the bar, per the `monitors` selector in the Qt
    // bar's config ("primary" | "all" | ["CONNECTOR", ...]).
    function _screens() {
        const screens = Quickshell.screens;
        const m = BarConfig.monitors;
        if (Array.isArray(m))
            return screens.filter(s => m.indexOf(s.name) >= 0);
        if (m === "all")
            return screens;
        return screens.length ? [screens[0]] : [];
    }

    // Bar width / insets are shared with the popups (data/BarGeom.qml).
    function _insets(screenW) {
        return BarGeom.insets(screenW);
    }

    Variants {
        model: shell._screens()

        PanelWindow {
            id: panel
            required property var modelData
            screen: modelData

            readonly property var insets: shell._insets(modelData.width)

            anchors.top: BarConfig.barPosition === "top"
            anchors.bottom: BarConfig.barPosition === "bottom"
            anchors.left: true
            anchors.right: true
            margins.top: BarConfig.barPosition === "top" ? BarConfig.gapOut : 0
            margins.bottom: BarConfig.barPosition === "bottom" ? BarConfig.gapOut : 0
            margins.left: panel.insets.left
            margins.right: panel.insets.right
            implicitHeight: BarConfig.barHeight
            // Reserve the bar plus its windows-side (gap_in) and edge-side
            // (gap_out) breathing space, matching the GTK surface height.
            exclusiveZone: BarConfig.barHeight + BarConfig.gapIn + BarConfig.gapOut
            color: "transparent"

            Bar {
                anchors.fill: parent
            }
        }
    }

    // Transient surfaces are built on first open instead of at startup. All 12
    // used to be instantiated eagerly, which cost ~140 MB of RSS and a longer
    // launch for windows that are closed almost all the time. Each loader stays
    // active once it has fired, so a reopen is instant after the first time.
    component SurfaceLoader: Loader {
        property bool want: false
        active: false
        onWantChanged: if (want) active = true
        Component.onCompleted: if (want) active = true
    }

    // The IPC toggles live here, not in the surfaces: a keybind must work before
    // the surface it opens has ever been created.
    IpcHandler { target: "quicksettings"
        function toggle() { UiState.quickSettingsOpen = !UiState.quickSettingsOpen; }
        function open() { UiState.quickSettingsOpen = true; }
        function close() { UiState.quickSettingsOpen = false; }
    }
    IpcHandler { target: "settings"
        function toggle() { UiState.settingsOpen = !UiState.settingsOpen; }
        function open() { UiState.settingsOpen = true; }
        function close() { UiState.settingsOpen = false; }
        function configManager() { UiState.settingsOpen = true; UiState.configManagerRequested = true; }
    }
    IpcHandler { target: "launcher"
        function toggle() { UiState.launcherOpen = !UiState.launcherOpen; }
        function open() { UiState.launcherOpen = true; }
        function close() { UiState.launcherOpen = false; }
    }
    IpcHandler { target: "themer"
        function toggle() { UiState.themerOpen = !UiState.themerOpen; }
        function open() { UiState.themerOpen = true; }
        function close() { UiState.themerOpen = false; }
    }
    IpcHandler { target: "clipboard"
        function toggle() { UiState.clipboardOpen = !UiState.clipboardOpen; }
        function open() { UiState.clipboardOpen = true; }
        function close() { UiState.clipboardOpen = false; }
    }
    IpcHandler { target: "notifications"
        function toggle() { UiState.notificationCenterOpen = !UiState.notificationCenterOpen; }
        function open() { UiState.notificationCenterOpen = true; }
        function close() { UiState.notificationCenterOpen = false; }
    }
    IpcHandler { target: "startmenu"
        function toggle() { UiState.startMenuOpen = !UiState.startMenuOpen; }
        function open() { UiState.startMenuOpen = true; }
        function close() { UiState.startMenuOpen = false; }
    }
    IpcHandler { target: "arcmenu"
        function toggle() { UiState.arcMenuOpen = !UiState.arcMenuOpen; }
        function open() { UiState.arcMenuOpen = true; }
        function close() { UiState.arcMenuOpen = false; }
    }
    IpcHandler { target: "sysmon"
        function toggle() { UiState.sysMonitorOpen = !UiState.sysMonitorOpen; }
        function open() { UiState.sysMonitorOpen = true; }
        function close() { UiState.sysMonitorOpen = false; }
    }
    IpcHandler { target: "about"
        function toggle() { UiState.aboutOpen = !UiState.aboutOpen; }
        function open() { UiState.aboutOpen = true; }
        function close() { UiState.aboutOpen = false; }
    }
    IpcHandler { target: "barMenu"
        function toggle() { UiState.barMenuOpen = !UiState.barMenuOpen; }
        function open() { UiState.barMenuOpen = true; }
        function close() { UiState.barMenuOpen = false; }
    }

    SurfaceLoader { want: UiState.quickSettingsOpen; source: "surface/QuickSettings.qml" }
    SurfaceLoader { want: UiState.settingsOpen; source: "surface/Settings.qml" }
    SurfaceLoader { want: UiState.widgetSettingsOpen; source: "surface/WidgetSettings.qml" }
    // The arc menu's FAB is always on screen when the menu is enabled, so its
    // surface has to exist from the start in that case (it renders/inputs
    // through a mask that is just the FAB while collapsed).
    SurfaceLoader { want: BarConfig.arcmenu.enabled !== false; source: "surface/ArcMenu.qml" }
    SurfaceLoader { want: UiState.barMenuOpen; source: "surface/BarMenu.qml" }
    SurfaceLoader { want: UiState.startMenuOpen; source: "surface/StartMenu.qml" }
    SurfaceLoader { want: UiState.launcherOpen; source: "surface/Launcher.qml" }
    SurfaceLoader { want: UiState.themerOpen; source: "surface/Themer.qml" }
    SurfaceLoader { want: UiState.sysMonitorOpen; source: "surface/SysMonitor.qml" }
    SurfaceLoader { want: UiState.notificationCenterOpen; source: "surface/NotificationCenter.qml" }
    SurfaceLoader { want: UiState.clipboardOpen; source: "surface/Clipboard.qml" }
    SurfaceLoader { want: UiState.aboutOpen; source: "surface/About.qml" }
    DesktopWidgets {}

    Loader {
        active: Quickshell.env("HYPRTK_BAR_QT_NOTIFICATIONS") !== "0"
        source: "surface/Notifications.qml"
    }

    IpcHandler {
        target: "shell"
        function reload() { Quickshell.reload(true); }
    }
}
