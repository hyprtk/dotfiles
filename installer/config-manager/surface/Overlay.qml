// Overlay settings window used when hyprtk-bar-qt launches config-manager from
// its own Settings dialogue. Layer-shell Overlay sits above the bar settings
// (Top layer), keeping both apps independent.
import QtQuick
import Quickshell
import Quickshell.Wayland
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
