// Shared UI state (which transient surface is open). A singleton so the bar's
// buttons and the popup surfaces can talk without nesting.
//
// Named UiState, not State, to avoid clashing with the QtQuick State type.
pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property bool quickSettingsOpen: false
    property bool settingsOpen: false
    property bool widgetSettingsOpen: false
    property string widgetSettingsId: ""
    property bool arcMenuOpen: false
    property bool startMenuOpen: false
    property bool themerOpen: false
    property bool sysMonitorOpen: false
    property bool notificationCenterOpen: false
    property bool clipboardOpen: false
    property bool launcherOpen: false
    property bool aboutOpen: false
    property bool barMenuOpen: false
    property real barMenuX: 40      // cursor x within the bar window (for the context menu)

    // The Settings surface owns the config-manager launch (it needs the window's
    // own process/state), but its IPC handler now lives in shell.qml so the
    // keybind keeps working before the surface has been created. A flag, not a
    // signal: the surface may be created by the same IPC call that sets it.
    property bool configManagerRequested: false
}
