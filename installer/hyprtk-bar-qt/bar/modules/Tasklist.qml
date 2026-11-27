// Window list (tasklist): one button per app, grouped by appId, with optional
// pinned apps from the `center.pinned` config.
//
// Left-click activates the app's most-recent window, or minimises it when it is
// already focused; middle-click closes it; a pinned app with no window launches
// its command. Backed by the Quickshell Hyprland service (HyprlandToplevel:
// title / activated / address / workspace), with actions dispatched by address.
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Widgets
import "../../theme"
import "../../data"

RowLayout {
    id: root
    spacing: 4
    readonly property int fs: BarConfig.fontSize(11)
    readonly property var pinned: (BarConfig.center.pinned || [])

    // A missed Hyprland `closewindow` event (the event socket reconnecting loses
    // whatever closed while it was down) leaves its toplevel in
    // Hyprland.toplevels for the life of the process, because Quickshell's
    // refreshToplevels() only ever adds or updates — it never prunes. The bar
    // then draws a button for a window that no longer exists, and neither
    // killing the app nor reloading the QML clears it: the Hyprland singleton
    // outlives a reload, and only a new `qs` process starts from a clean poll.
    // So cross-check the model against the live client list (and re-poll it, to
    // catch a missed *open* as well) on a slow timer. Only a toplevel that was
    // already in the model when the poll started may be pruned: one that opened
    // while the snapshot was in flight is not in it yet, and hiding it would
    // make a fresh window's button vanish for a whole interval.
    property var live: null      // address set from `hyprctl clients`; null = unknown
    property var atPollStart: null // model addresses when that poll began
    property int liveEpoch: 0    // re-runs groups() when a poll lands

    function _addrSet(list) {
        const set = {};
        for (const a of list)
            set[String(a || "").toLowerCase().replace(/^0x/, "")] = true;
        return set;
    }
    function _modelAddrs() {
        return (Hyprland.toplevels.values || []).map(t => t.address);
    }

    // groups() only re-evaluates when the toplevel *list* changes, but a window's
    // appId/title arrive after it is mapped (XWayland especially late). A window
    // grouped before its appId was known used to leave a phantom, iconless button
    // behind, and the real button then appeared next to it — one app looked
    // duplicated. `_sig` is a binding over exactly the fields the grouping uses,
    // so any of them changing re-runs groups(), which reads it.
    readonly property string _sig: (Hyprland.toplevels.values || []).map(t =>
        t.address + "|" + root._appId(t) + "|"
        + (t.workspace ? t.workspace.id : "") + "|" + (t.activated ? 1 : 0)).join(";")

    function _appId(t) {
        const id = (t.wayland && t.wayland.appId) ? String(t.wayland.appId) : "";
        return id || String(t.title || "");
    }
    // Grouping key: one app must never split into two buttons just because its
    // appId differs in case, spacing or a `.desktop` suffix ("GitHub Desktop"
    // vs "github-desktop"). The raw appId is kept for the icon lookup.
    function _appKey(t) {
        return root._appId(t)
            .toLowerCase().replace(/\.desktop$/, "").replace(/[\s_-]+/g, "");
    }
    // Resolve an appId to a theme icon (desktop entry, symbolic preferred).
    function iconFor(appId) {
        let e = null;
        try {
            e = DesktopEntries.byId(appId)
                || DesktopEntries.byId(appId + ".desktop")
                || DesktopEntries.heuristicLookup(appId);
        } catch (err) {}
        let name = (e && e.icon) ? e.icon : appId;
        if (name && Quickshell.hasThemeIcon(name + "-symbolic"))
            name = name + "-symbolic";
        return Quickshell.iconPath(name, "application-x-executable");
    }
    function _match(a, b) {
        a = String(a || "").toLowerCase().replace(/\.desktop$/, "");
        b = String(b || "").toLowerCase().replace(/\.desktop$/, "");
        return a.length > 0 && b.length > 0 && (a === b || a.includes(b) || b.includes(a));
    }
    function groups() {
        const _rev = root._sig + "|" + root.liveEpoch; // regroup when a toplevel's fields change (above)
        const map = {};
        const label = {};
        for (const t of (Hyprland.toplevels.values || [])) {
            const raw = root._appId(t);
            if (!raw) continue; // appId/title not known yet — nothing to show
            // Skip a toplevel Hyprland no longer lists (see `live` above). Only
            // filter on a good poll, and only for a toplevel that predates it —
            // an unreadable poll or a just-opened window must never hide the
            // bar's whole window list.
            const a = String(t.address || "").toLowerCase().replace(/^0x/, "");
            if (root.live && root.atPollStart && root.atPollStart[a] && !root.live[a])
                continue;
            const k = root._appKey(t);
            if (!map[k]) { map[k] = []; label[k] = raw; }
            map[k].push(t);
        }
        const out = [];
        const seen = {};
        for (const p of root.pinned) {
            let key = null;
            for (const k in map)
                if (root._match(p.class, label[k])) { key = k; break; }
            out.push({ pinned: p, appId: key ? label[key] : (p.class || ""), wins: key ? map[key] : [] });
            if (key)
                seen[key] = true;
        }
        for (const k in map)
            if (!seen[k])
                out.push({ pinned: null, appId: label[k], wins: map[k] });
        return out;
    }
    function _recent(wins) {
        return wins.find(w => w.activated) || wins[0];
    }
    // Focus a window, restoring it first if it is parked on a special
    // (negative-id) workspace such as special:minimized — matches the GTK bar.
    function _focusWindow(w) {
        if (!w || !w.address)
            return;
        if (w.workspace && w.workspace.id < 0) {
            const aw = Hyprland.focusedWorkspace;
            if (aw)
                Hyprland.dispatch(Hypr.moveWindowTo(aw.name || String(aw.id), w.address));
        }
        Hyprland.dispatch(Hypr.focusWindow(w.address));
    }
    function _menu(grp) {
        const w = root._recent(grp.wins);
        const items = [];
        if (w) {
            items.push({ label: "Minimise", action: () => {
                if (w.address) Hyprland.dispatch(Hypr.moveWindowTo("special:minimized", w.address));
            } });
            items.push({ label: "Close window", action: () => {
                if (w.address) Hyprland.dispatch(Hypr.closeWindow(w.address));
            } });
        } else if (grp.modelData.pinned && grp.modelData.pinned.command) {
            items.push({ label: "Launch", action: () => Quickshell.execDetached(["sh", "-c", grp.modelData.pinned.command]) });
        }
        PopupMenu.open(grp, items);
    }

    Repeater {
        model: root.groups()

        delegate: Rectangle {
            id: grp
            required property var modelData

            readonly property var wins: grp.modelData.wins
            readonly property var pin: grp.modelData.pinned
            readonly property string appId: grp.modelData.appId
            readonly property bool act: grp.wins.some(w => w.activated)
            readonly property bool running: grp.wins.length > 0
            readonly property var recent: root._recent(grp.wins)
            readonly property string title: grp.running
                ? (grp.recent.title || grp.appId)
                : (grp.pin && grp.pin.class ? grp.pin.class : "?")

            implicitWidth: 26
            implicitHeight: 22
            radius: 6
            color: grp.act
                ? Theme.alpha(Theme.accent, 0.85)
                : (grp.running ? Theme.alpha(Theme.accent2, 0.12) : Theme.alpha(Theme.dim, 0.18))

            IconImage {
                anchors.centerIn: parent
                implicitSize: 16
                source: root.iconFor(grp.appId)
                opacity: grp.running ? 1.0 : 0.6
            }

            // running indicator (bottom-right)
            Rectangle {
                visible: grp.running
                width: 4
                height: 4
                radius: 2
                anchors.right: parent.right
                anchors.rightMargin: 2
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 2
                color: grp.act ? Theme.textOnAccent : Theme.accent2
            }

            HoverHandler {
                id: grpHover
                onHoveredChanged: grpHover.hovered
                    ? Tooltips.showTip(grp, grp.title)
                    : Tooltips.hideTip()
            }
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                cursorShape: Qt.PointingHandCursor
                onClicked: (mouse) => {
                    if (mouse.button === Qt.RightButton) {
                        root._menu(grp);
                        return;
                    }
                    const wins = grp.wins;
                    if (!wins.length) {
                        if (mouse.button === Qt.LeftButton && grp.pin && grp.pin.command)
                            Quickshell.execDetached(["sh", "-c", grp.pin.command]);
                        return;
                    }
                    const focused = wins.find(w => w.activated);
                    if (mouse.button === Qt.MiddleButton) {
                        const w = focused || root._recent(wins);
                        if (w.address)
                            Hyprland.dispatch(Hypr.closeWindow(w.address));
                        return;
                    }
                    if (focused) {
                        if (focused.address)
                            Hyprland.dispatch(Hypr.moveWindowTo("special:minimized", focused.address));
                        return;
                    }
                    root._focusWindow(root._recent(wins));
                }
            }
        }
    }

    Process {
        id: clientsPoll
        command: ["hyprctl", "-j", "clients"]
        stdout: StdioCollector {
            onStreamFinished: {
                let addrs = null;
                try {
                    const arr = JSON.parse(text);
                    if (Array.isArray(arr) && arr.length >= 0)
                        addrs = arr;
                } catch (e) {
                    addrs = null; // unreadable poll: keep showing what we have
                }
                root.live = addrs ? root._addrSet(addrs.map(c => c && c.address)) : null;
                root.liveEpoch++;
            }
        }
    }
    Timer {
        interval: 15000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            root.atPollStart = root._addrSet(root._modelAddrs());
            Hyprland.refreshToplevels(); // a missed `openwindow`
            clientsPoll.running = true;  // and a missed `closewindow`
        }
    }
}
