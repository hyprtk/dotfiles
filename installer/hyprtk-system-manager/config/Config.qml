// Shared UI state: which page is open, window metrics and the app version.
pragma Singleton

import QtQuick
import Quickshell

Singleton {
    readonly property bool overlayMode: Quickshell.env("HYPRTK_SM_OVERLAY") === "1"
    readonly property bool testMode: Quickshell.env("HYPRTK_SM_TEST") === "1"
    readonly property int windowWidth: 1180
    readonly property int windowHeight: 800
    readonly property int sidebarWidth: 200

    property string page: Quickshell.env("HYPRTK_SM_PAGE") || "about"
    property var lastPage: "about"
    property bool completed: false
}
