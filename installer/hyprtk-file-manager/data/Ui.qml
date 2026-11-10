pragma Singleton

import QtQuick
import Quickshell

Singleton {
    id: root

    property bool modalOpen: false

    signal renameRequested(string path, string name)
    signal newRequested(string dir, bool folder)
    signal deleteRequested(var paths, bool permanent)
    signal batchRenameRequested(var paths)
    signal propertiesRequested(string path)
    signal emptyTrashRequested()
    signal placesChanged()
    signal networkScanRequested()
    signal networkAuthRequested(string uri, string name)
    signal networkAuthAccepted(string uri, string username, string password, string domain)

    function askRename(path, name) {
        root.modalOpen = true;
        root.renameRequested(path, name);
    }

    function askNew(dir, folder) {
        root.modalOpen = true;
        root.newRequested(dir, folder);
    }

    function askDelete(paths, permanent) {
        root.modalOpen = true;
        root.deleteRequested(paths, permanent);
    }

    function askBatchRename(paths) {
        root.modalOpen = true;
        root.batchRenameRequested(paths);
    }

    function askProperties(path) {
        root.modalOpen = true;
        root.propertiesRequested(path);
    }

    function askEmptyTrash() {
        root.modalOpen = true;
        root.emptyTrashRequested();
    }

    function refreshPlaces() {
        root.placesChanged();
    }

    function requestNetworkScan() {
        root.networkScanRequested();
    }

    function askNetworkAuth(uri, name) {
        root.modalOpen = true;
        root.networkAuthRequested(uri, name || uri);
    }

    function acceptNetworkAuth(uri, username, password, domain) {
        root.modalOpen = false;
        root.networkAuthAccepted(uri, username || "", password || "", domain || "");
    }

    function cancelNetworkAuth() {
        root.modalOpen = false;
    }

    function close() {
        root.modalOpen = false;
    }
}
