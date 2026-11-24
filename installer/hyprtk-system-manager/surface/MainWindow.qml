// Standalone settings window: a layer-shell panel, exactly like the bar's own
// Settings and Quick Settings dialogs. Layer surfaces are not decorated by the
// compositor — no border, shadow or rounding — so the only edge is the app's
// animated accent border. No anchors means wlr-layer-shell centres it.
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "../config"

PanelWindow {
    id: win

    visible: true
    color: "transparent"
    focusable: true
    exclusionMode: ExclusionMode.Ignore
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight

    // Open on the monitor that had focus when the app started. Quickshell has
    // no focused-screen accessor in this build, so ask Hyprland once and map
    // the name onto a Quickshell screen. Captured once: the panel must not jump
    // between monitors as focus changes.
    property string focusedName: ""
    function screenByName(name) {
        const list = Quickshell.screens || [];
        for (let i = 0; i < list.length; i++) {
            if (list[i].name === name)
                return list[i];
        }
        return null;
    }
    screen: win.focusedName.length > 0 ? win.screenByName(win.focusedName) : null

    Process {
        id: focusProc
        command: ["hyprctl", "-j", "monitors"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const monitors = JSON.parse(text) || [];
                    for (const monitor of monitors) {
                        if (monitor.focused) {
                            win.focusedName = String(monitor.name || "");
                            break;
                        }
                    }
                } catch (e) {
                    // Not on Hyprland: leave the default screen.
                }
            }
        }
    }

    App {
        anchors.fill: parent
    }
}
