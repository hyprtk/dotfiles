// App-local preferences (independent of the bar's config.json).
// M0 keeps these in memory; persistence lands with the app state work.
pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    readonly property bool overlayMode: Quickshell.env("HYPR_CM_OVERLAY") === "1"
    property string page: Quickshell.env("HYPR_CM_PAGE") || "animations"
    property int windowWidth: 900
    property int windowHeight: 640
    property real previewSpeedScale: 1.0
}
