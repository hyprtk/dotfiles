// Overlay mode: a layer-shell panel used when the bar hands off to System
// Settings. Keeps the bar's own Settings window usable underneath.
import QtQuick
import Quickshell
import Quickshell.Wayland
import "."
import "../config"

PanelWindow {
    id: win

    visible: true
    color: "transparent"
    focusable: true
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Overlay
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight

    App {
        anchors.fill: parent
    }
}
