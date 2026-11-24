// hyprtk-system-manager — Quickshell entry point.
// HYPRTK_SM_OVERLAY=1 opens the layer-shell overlay used by the bar; the normal
// standalone window is a layer-shell panel too (so the compositor never adds a
// border/shadow). HYPRTK_SM_TEST=1 swaps in a FloatingWindow for off-screen QA,
// because PanelWindow has no backend without Wayland.
import QtQuick
import Quickshell
import "config"
import "surface"

ShellRoot {
    Loader {
        source: Config.testMode
            ? "surface/TestWindow.qml"
            : (Config.overlayMode ? "surface/Overlay.qml" : "surface/MainWindow.qml")
    }
}
