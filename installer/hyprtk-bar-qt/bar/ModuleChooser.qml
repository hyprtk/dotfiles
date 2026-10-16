// Maps a bar layout entry (Config.layoutLeft/Center/Right) to its module
// component. This lives in its own file on purpose: an inline
// `component ModuleChooser: DelegateChooser` used directly as a Repeater
// delegate is not recognised as a delegate component on Qt < 6.9 (e.g. the
// Qt 6.8 bundled with the prebuilt Quickshell on Debian/Ubuntu/Mint) — it warns
// "Delegate must be of Item type" and leaves the whole bar empty. A file-based
// component resolves correctly on every supported Qt version.
//
// DelegateChooser lives in Qt.labs.qmlmodels on Qt 6.0-6.8 and moved to
// QtQml.Models in 6.9; the labs module re-exports it on both, so a single import
// stays portable.
import QtQuick
import Qt.labs.qmlmodels
import "modules"

DelegateChooser {
    role: "modelData"
    DelegateChoice { roleValue: "start_button"; delegate: StartButton {} }
    DelegateChoice { roleValue: "quicklinks"; delegate: Quicklinks {} }
    DelegateChoice { roleValue: "workspaces"; delegate: Workspaces {} }
    DelegateChoice { roleValue: "tasklist"; delegate: Tasklist {} }
    DelegateChoice { roleValue: "window"; delegate: ActiveWindow {} }
    DelegateChoice { roleValue: "updates"; delegate: Updates {} }
    DelegateChoice { roleValue: "net"; delegate: Net {} }
    DelegateChoice { roleValue: "tray"; delegate: Tray {} }
    DelegateChoice { roleValue: "kbstate"; delegate: KbState {} }
    DelegateChoice { roleValue: "notifications"; delegate: NotificationsButton {} }
    DelegateChoice { roleValue: "clock"; delegate: Clock {} }
    DelegateChoice { roleValue: "media"; delegate: Media {} }
    DelegateChoice { roleValue: "sysmon"; delegate: SysMonitor {} }
    DelegateChoice { roleValue: "themer"; delegate: ThemerButton {} }
    DelegateChoice { roleValue: "settings"; delegate: SettingsButton {} }
    DelegateChoice { roleValue: "quicksettings"; delegate: QuickSettingsButton {} }
    DelegateChoice { delegate: Item {} }
}
