// Off-screen QA/screenshot host. The real window is a layer-shell panel, which
// cannot load without a Wayland backend; this FloatingWindow is only used when
// HYPRTK_SM_TEST=1.
import QtQuick
import Quickshell
import "../config"

FloatingWindow {
    id: win

    visible: true
    color: "transparent"
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight

    App {
        anchors.fill: parent
    }
}
