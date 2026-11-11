pragma Singleton

import QtQuick
import Quickshell
import "."

Singleton {
    id: root

    property var cache: ({})
    property var pending: ({})
    property var requests: ({})
    property var queue: []
    property int inFlight: 0

    readonly property int maxInFlight: 3
    readonly property int maxCache: 600

    function stamp(path, mtime, size) {
        return path + ":" + mtime + ":" + size;
    }

    function thumbFor(path, mtime, size) {
        const hit = root.cache[path];
        if (!hit || hit.mtime !== mtime || hit.size !== size)
            return "";
        return "file://" + hit.thumb;
    }

    function request(path, mtime, size) {
        if (!path)
            return;
        const hit = root.cache[path];
        if (hit && hit.mtime === mtime && hit.size === size)
            return;
        const key = root.stamp(path, mtime, size);
        if (root.pending[path] === key)
            return;
        const pend = Object.assign({}, root.pending);
        pend[path] = key;
        root.pending = pend;
        const next = root.queue.slice();
        next.push({ path: path, mtime: mtime, size: size });
        root.queue = next;
        root.pump();
    }

    function pump() {
        while (root.inFlight < root.maxInFlight && root.queue.length > 0) {
            const job = root.queue[0];
            root.queue = root.queue.slice(1);
            const id = Backend.call("thumb", { path: job.path });
            const req = Object.assign({}, root.requests);
            req[id] = job;
            root.requests = req;
            root.inFlight += 1;
        }
    }

    function finish(id, result) {
        const job = root.requests[id];
        if (!job)
            return;
        const req = Object.assign({}, root.requests);
        delete req[id];
        root.requests = req;
        root.inFlight = Math.max(0, root.inFlight - 1);
        const pend = Object.assign({}, root.pending);
        delete pend[job.path];
        root.pending = pend;
        if (result && result.thumb) {
            const next = Object.assign({}, root.cache);
            next[job.path] = { thumb: result.thumb, mtime: job.mtime, size: job.size };
            const keys = Object.keys(next);
            for (let i = 0; i < keys.length - root.maxCache; i++)
                delete next[keys[i]];
            root.cache = next;
        }
        root.pump();
    }

    Connections {
        target: Backend
        function onResponse(id, result) { root.finish(id, result); }
        function onFailure(id, message) { root.finish(id, null); }
    }
}
