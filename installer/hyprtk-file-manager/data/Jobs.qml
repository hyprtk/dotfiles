pragma Singleton

import QtQuick
import Quickshell
import "."

Singleton {
    id: root

    property var jobs: []
    property var conflicts: []

    readonly property var currentConflict: root.conflicts.length > 0 ? root.conflicts[0] : null
    readonly property int activeCount:
        root.jobs.filter(function (job) { return job.state === "running" || job.state === "queued"; }).length

    signal jobFinished()

    Connections {
        target: Backend
        function onJobEvent(job) { root.upsert(job) }
        function onConflictEvent(job, conflict) { root.enqueueConflict(job, conflict) }
    }

    Timer {
        interval: 3000
        repeat: true
        running: true
        onTriggered: root.prune()
    }

    function upsert(job) {
        if (!job || !job.id)
            return;
        const next = root.jobs.slice();
        const index = next.findIndex(function (item) { return item.id === job.id; });
        const previous = index >= 0 ? next[index] : null;
        const merged = Object.assign({}, job);
        if (previous && previous._doneAt)
            merged._doneAt = previous._doneAt;
        if (merged.state !== "running" && merged.state !== "queued" && !merged._doneAt)
            merged._doneAt = Date.now();
        if (index >= 0)
            next[index] = merged;
        else
            next.unshift(merged);
        root.jobs = next.slice(0, 20);
        if (previous && previous.state !== merged.state
                && (merged.state === "done" || merged.state === "failed" || merged.state === "cancelled"))
            root.jobFinished();
    }

    function prune() {
        const now = Date.now();
        root.jobs = root.jobs.filter(function (job) {
            return job.state === "running" || job.state === "queued"
                || !job._doneAt || (now - job._doneAt) < 8000;
        });
    }

    function enqueueConflict(job, conflict) {
        const next = root.conflicts.slice();
        next.push({ job: job, conflict: conflict });
        root.conflicts = next;
    }

    function resolve(decision, applyAll) {
        const current = root.currentConflict;
        if (!current)
            return;
        Backend.call("job.resolve", {
            job: current.job,
            path: current.conflict.dst,
            decision: decision,
            applyAll: applyAll
        });
        root.conflicts = root.conflicts.slice(1);
    }

    function cancelConflict() {
        const current = root.currentConflict;
        if (!current)
            return;
        Backend.call("job.cancel", { job: current.job });
        root.conflicts = root.conflicts.slice(1);
    }

    function cancel(jobId) { Backend.call("job.cancel", { job: jobId }); }
    function undo() { Backend.call("undo", {}); }
    function redo() { Backend.call("redo", {}); }

    function clearFinished() {
        root.jobs = root.jobs.filter(function (job) {
            return job.state === "running" || job.state === "queued";
        });
    }

    function label(kind) {
        const labels = {
            copy: "Copying", move: "Moving", trash: "Trashing", delete: "Deleting",
            rename: "Renaming", batchrename: "Batch rename", mkdir: "New folder",
            newfile: "New file", undo: "Undoing", redo: "Redoing", emptytrash: "Emptying trash"
        };
        return labels[kind] || kind;
    }
}
