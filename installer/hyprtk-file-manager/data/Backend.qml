pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    readonly property string backendDir:
        Qt.resolvedUrl("../backend").toString().replace("file://", "")

    property bool started: false
    property int reqId: 0
    property var queue: []
    property string lastError: ""
    property bool elevated: false

    signal response(int id, var result)
    signal failure(int id, string message)
    signal jobEvent(var job)
    signal conflictEvent(string job, var conflict)
    signal fsEvent(string token, string dir)

    function call(method, params) {
        root.reqId += 1;
        const id = root.reqId;
        const line = JSON.stringify({ id: id, method: method, params: params || ({}) });
        if (root.started) {
            proc.write(line + "\n");
        } else {
            const pending = root.queue.slice();
            pending.push(line);
            root.queue = pending;
        }
        return id;
    }

    function onLine(line) {
        let res = null;
        try {
            res = JSON.parse(line);
        } catch (e) {
            console.warn("hyprtk-fm: bad line", line);
            return;
        }
        if (res.event === "job") {
            root.jobEvent(res.job);
            return;
        }
        if (res.event === "conflict") {
            root.conflictEvent(String(res.job), res.conflict);
            return;
        }
        if (res.event === "fs") {
            root.fsEvent(String(res.token), String(res.dir));
            return;
        }
        if (res.result && res.result.kind === "ping")
            root.elevated = res.result.root === true;
        const id = (res.id === null || res.id === undefined) ? -1 : res.id;
        if (res.error) {
            root.failure(id, res.error);
        } else {
            root.response(id, res.result);
        }
    }

    Component.onCompleted: root.call("ping", {})

    Process {
        id: proc
        running: true
        stdinEnabled: true
        command: ["python3", "-u", "-m", "hyprtk_file_manager.cli", "serve"]
        environment: ({ "PYTHONPATH": root.backendDir })
        clearEnvironment: false
        stdout: SplitParser { onRead: line => root.onLine(line) }
        stderr: SplitParser { onRead: line => console.warn("hyprtk-fm backend:", line) }
        onStarted: {
            root.started = true;
            const pending = root.queue;
            root.queue = [];
            for (let i = 0; i < pending.length; i++)
                proc.write(pending[i] + "\n");
        }
        onExited: (code, status) => {
            root.started = false;
            root.lastError = "backend exited " + code;
            console.warn("hyprtk-fm:", root.lastError);
        }
    }
}
