// hyprtk-config-manager — Quickshell entry point.
// HYPR_CM_OVERLAY=1 opens the layer-shell overlay used by bar-qt Settings;
// otherwise the standalone floating window is used.
import QtQuick
import Quickshell
import "surface"
import "config"

ShellRoot {
    Loader {
        sourceComponent: Config.overlayMode ? overlayComponent : floatingComponent
    }

    Component { id: floatingComponent; Main {} }
    Component { id: overlayComponent; Overlay {} }
}
