// Standalone settings window: a normal floating toplevel so Hyprland's
// SUPER+drag/resize binds work. The UI itself lives in App.qml.
import QtQuick
import Quickshell
import Quickshell.Hyprland
import "../config"

FloatingWindow {
    id: win

    visible: true
    color: "transparent"
    title: "Hyprland Settings"
    implicitWidth: Config.windowWidth
    implicitHeight: Config.windowHeight
    minimumSize: Qt.size(Config.windowWidth, Config.windowHeight)
    maximumSize: Qt.size(Config.windowWidth, Config.windowHeight)

    property bool selfFloated: false

    // Float/centre once the toplevel appears; also pin opacity so hyprtk's
    // inactive_opacity 0.7 cannot wash the settings window out when unfocused.
    function floatSelf() {
        if (selfFloated || !Hyprland.toplevels)
            return;
        const list = Hyprland.toplevels.values || [];
        for (const t of list) {
            if (t.title !== "Hyprland Settings")
                continue;
            let addr = String(t.address || "");
            if (addr.length > 0 && addr.indexOf("0x") !== 0)
                addr = "0x" + addr;
            Hyprland.dispatch('hl.dsp.window.float({ window = "address:' + addr + '", action = "enable" })');
            Hyprland.dispatch('hl.dsp.window.center({ window = "address:' + addr + '" })');
            Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "opacity", value = "1.0", window = "address:' + addr + '" })');
            Hyprland.dispatch('hl.dsp.window.set_prop({ prop = "opacity_inactive", value = "1.0", window = "address:' + addr + '" })');
            selfFloated = true;
            return;
        }
    }

    Connections {
        target: Hyprland.toplevels
        function onValuesChanged() { win.floatSelf(); }
    }

    Timer {
        interval: 400
        running: true
        repeat: false
        onTriggered: win.floatSelf()
    }

    App {
        anchors.fill: parent
    }
}
