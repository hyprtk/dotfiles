"""File operation jobs: copy, move, trash, delete, rename, create, undo."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from . import trash as trash_mod

DECISIONS = ("replace", "skip", "keep-both")


def unique_path(path: str) -> str:
    base, ext = os.path.splitext(path)
    index = 1
    while os.path.lexists(f"{base} ({index}){ext}"):
        index += 1
    return f"{base} ({index}){ext}"


def validate_name(name: str) -> str:
    if not name or name in (".", "..") or "/" in name or "\x00" in name:
        raise ValueError(f"invalid name: {name!r}")
    return name


def as_paths(values) -> list[str]:
    if not values:
        return []
    if not isinstance(values, list):
        values = [values]
    return [str(Path(str(value)).expanduser()) for value in values]


class GioTrash:
    def trash(self, path: str) -> None:
        subprocess.run(
            ["gio", "trash", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )

    def restore(self, path: str) -> None:
        listing = subprocess.run(
            ["gio", "trash", "--list"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for line in listing.splitlines():
            uri, _, original = line.partition("\t")
            if original == str(path):
                subprocess.run(
                    ["gio", "trash", "--restore", uri],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return
        raise FileNotFoundError(f"not in trash: {path}")


class Job:
    def __init__(self, kind: str, sources: list[str], dest: str | None = None):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.sources = sources
        self.dest = dest
        self.renames = None
        self.state = "queued"
        self.total = len(sources)
        self.done = 0
        self.current = ""
        self.errors: list[dict] = []
        self.undo = None
        self.cancel = threading.Event()
        self.conflict_ack = threading.Event()
        self.decisions: dict[str, str] = {}
        self.default_decision: str | None = None
        self.pending_conflict: dict | None = None
        self.finished_at = 0.0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "errors": self.errors[:20],
            "dest": self.dest,
            "sourceCount": len(self.sources),
        }


class JobManager:
    def __init__(self, emit, journal, trash=None, threaded=True, ask_handler=None):
        self.emit = emit
        self.journal = journal
        self.trash = trash or GioTrash()
        self.threaded = threaded
        self.ask_handler = ask_handler
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self.lock = threading.RLock()

    def dispatch(self, op: str, params: dict) -> dict:
        if op in ("copy", "move", "trash", "delete", "rename", "batchrename",
                  "mkdir", "newfile", "undo", "redo", "emptytrash"):
            return self._submit(op, params)
        if op == "cancel":
            return self.cancel(params.get("job"))
        if op == "resolve":
            return self.resolve(
                params.get("job"),
                params.get("path"),
                params.get("decision"),
                bool(params.get("applyAll", False)),
            )
        if op == "list":
            with self.lock:
                return {"jobs": [self.jobs[job_id].as_dict() for job_id in self.order[-20:]]}
        raise ValueError(f"unknown job op: {op}")

    def _submit(self, kind: str, params: dict) -> dict:
        job = self._build(kind, params)
        with self.lock:
            self.jobs[job.id] = job
            self.order.append(job.id)
            while len(self.order) > 50:
                old = self.order.pop(0)
                self.jobs.pop(old, None)
        self._emit(job)
        if self.threaded:
            threading.Thread(target=self._run, args=(job,), daemon=True).start()
        else:
            self._run(job)
        return job.as_dict()

    def _build(self, kind: str, params: dict) -> Job:
        if kind in ("undo", "redo", "emptytrash"):
            job = Job(kind, [])
            job.total = 1
            return job
        if kind in ("copy", "move"):
            sources = as_paths(params.get("sources"))
            dest = str(Path(str(params.get("dest") or "")).expanduser())
            if not sources:
                raise ValueError("no sources")
            if not dest or not Path(dest).is_dir():
                raise ValueError("destination is not a directory")
            dest_abs = os.path.abspath(dest)
            for src in sources:
                src_abs = os.path.abspath(src)
                if src_abs == dest_abs:
                    continue
                if os.path.commonpath([src_abs, dest_abs]) == src_abs:
                    raise ValueError("destination is inside a source")
            return Job(kind, sources, dest)
        if kind in ("trash", "delete"):
            sources = as_paths(params.get("paths") or params.get("sources"))
            if not sources:
                raise ValueError("no paths")
            return Job(kind, sources)
        if kind == "rename":
            source = str(Path(str(params.get("path") or "")).expanduser())
            name = validate_name(str(params.get("name") or ""))
            if not os.path.lexists(source):
                raise FileNotFoundError(source)
            dest = os.path.join(os.path.dirname(source), name)
            return Job("rename", [source], dest)
        if kind == "batchrename":
            items = params.get("renames") or []
            if not isinstance(items, list) or not items:
                raise ValueError("no renames")
            pairs = []
            seen_sources = set()
            seen_targets = set()
            for item in items:
                source = str(Path(str(item.get("path") or "")).expanduser())
                name = validate_name(str(item.get("name") or ""))
                if not os.path.lexists(source):
                    raise FileNotFoundError(source)
                if source in seen_sources:
                    raise ValueError(f"duplicate source: {source}")
                dest = os.path.join(os.path.dirname(source), name)
                if os.path.abspath(source) != os.path.abspath(dest):
                    if dest in seen_targets:
                        raise ValueError(f"duplicate target: {dest}")
                    if os.path.lexists(dest):
                        raise FileExistsError(dest)
                seen_sources.add(source)
                seen_targets.add(dest)
                pairs.append([source, dest])
            job = Job("batchrename", [pair[0] for pair in pairs])
            job.renames = pairs
            job.total = len(pairs)
            return job
        if kind in ("mkdir", "newfile"):
            parent = str(Path(str(params.get("path") or "")).expanduser())
            name = validate_name(str(params.get("name") or ""))
            if not Path(parent).is_dir():
                raise ValueError("parent is not a directory")
            return Job(kind, [parent], os.path.join(parent, name))
        raise ValueError(f"unknown job kind: {kind}")

    def _emit(self, job: Job) -> None:
        self.emit({"event": "job", "job": job.as_dict()})

    def _error(self, job: Job, path, exc: Exception) -> None:
        job.errors.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})

    def _run(self, job: Job) -> None:
        job.state = "running"
        self._emit(job)
        try:
            getattr(self, f"_do_{job.kind}")(job)
            succeeded = job.done - len(job.errors)
            if job.cancel.is_set():
                job.state = "cancelled"
            elif job.errors and succeeded <= 0:
                job.state = "failed"
            else:
                job.state = "done"
        except Exception as exc:
            self._error(job, job.current, exc)
            job.state = "failed"
        job.finished_at = time.time()
        if job.undo and job.done > 0 and job.state in ("done", "cancelled"):
            self.journal.add(job.undo)
        self._emit(job)

    def cancel(self, job_id) -> dict:
        with self.lock:
            job = self.jobs.get(str(job_id or ""))
            if job:
                job.cancel.set()
                job.conflict_ack.set()
        return {"ok": True}

    def resolve(self, job_id, path, decision, apply_all=False) -> dict:
        if decision not in DECISIONS:
            raise ValueError(f"invalid decision: {decision}")
        with self.lock:
            job = self.jobs.get(str(job_id or ""))
            if not job:
                raise ValueError("unknown job")
            if apply_all:
                job.default_decision = decision
            if path:
                job.decisions[str(path)] = decision
            job.conflict_ack.set()
        return {"ok": True}

    def _ask(self, job: Job, src: str, dst: str) -> str:
        if self.ask_handler:
            return self.ask_handler(src, dst)
        key = str(dst)
        with self.lock:
            if job.default_decision:
                return job.default_decision
            if key in job.decisions:
                return job.decisions.pop(key)
            job.pending_conflict = {"src": str(src), "dst": key, "name": os.path.basename(key)}
            job.conflict_ack.clear()
        self.emit({"event": "conflict", "job": job.id, "conflict": job.pending_conflict})
        while not job.conflict_ack.wait(0.2):
            if job.cancel.is_set():
                return "skip"
        with self.lock:
            job.pending_conflict = None
            if job.default_decision:
                return job.default_decision
            return job.decisions.pop(key, "skip")

    def _copy_tree(self, job: Job, src: str, dst: str):
        if job.cancel.is_set():
            return None
        if os.path.lexists(dst):
            same = os.path.abspath(src) == os.path.abspath(dst)
            decision = self._ask(job, src, dst)
            if decision == "skip":
                return None
            if decision == "keep-both":
                dst = unique_path(dst)
            elif decision == "replace":
                if same:
                    return None
                if not (os.path.isdir(src) and os.path.isdir(dst) and not os.path.islink(dst)):
                    if os.path.isdir(dst) and not os.path.islink(dst):
                        shutil.rmtree(dst)
                    else:
                        os.unlink(dst)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            return dst
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            for name in os.listdir(src):
                if job.cancel.is_set():
                    break
                self._copy_tree(job, os.path.join(src, name), os.path.join(dst, name))
            return dst
        shutil.copy2(src, dst)
        return dst

    def _do_copy(self, job: Job) -> None:
        created = []
        pairs = []
        for src in job.sources:
            if job.cancel.is_set():
                break
            job.current = src
            target = os.path.join(job.dest, os.path.basename(src.rstrip("/")))
            try:
                final = self._copy_tree(job, src, target)
                if final:
                    created.append(final)
                    pairs.append([src, final])
            except Exception as exc:
                self._error(job, src, exc)
            job.done += 1
            self._emit(job)
        if created:
            job.undo = {"kind": "copy", "targets": created, "items": pairs}

    def _do_move(self, job: Job) -> None:
        moves = []
        for src in job.sources:
            if job.cancel.is_set():
                break
            job.current = src
            target = os.path.join(job.dest, os.path.basename(src.rstrip("/")))
            try:
                if os.path.abspath(src) == os.path.abspath(target):
                    job.done += 1
                    self._emit(job)
                    continue
                if os.path.lexists(target):
                    decision = self._ask(job, src, target)
                    if decision == "skip":
                        job.done += 1
                        self._emit(job)
                        continue
                    if decision == "keep-both":
                        target = unique_path(target)
                    elif decision == "replace":
                        if os.path.isdir(target) and not os.path.islink(target):
                            shutil.rmtree(target)
                        else:
                            os.unlink(target)
                shutil.move(src, target)
                moves.append([src, target])
            except Exception as exc:
                self._error(job, src, exc)
            job.done += 1
            self._emit(job)
        if moves:
            job.undo = {"kind": "move", "moves": moves}

    def _do_trash(self, job: Job) -> None:
        done = []
        for src in job.sources:
            if job.cancel.is_set():
                break
            job.current = src
            try:
                self.trash.trash(src)
                done.append(src)
            except Exception as exc:
                self._error(job, src, exc)
            job.done += 1
            self._emit(job)
        if done:
            job.undo = {"kind": "trash", "paths": done}

    def _do_delete(self, job: Job) -> None:
        for src in job.sources:
            if job.cancel.is_set():
                break
            job.current = src
            try:
                if os.path.isdir(src) and not os.path.islink(src):
                    shutil.rmtree(src)
                else:
                    os.unlink(src)
            except Exception as exc:
                self._error(job, src, exc)
            job.done += 1
            self._emit(job)

    def _do_rename(self, job: Job) -> None:
        src = job.sources[0]
        if os.path.lexists(job.dest):
            raise FileExistsError(job.dest)
        os.rename(src, job.dest)
        job.undo = {"kind": "rename", "items": [[src, job.dest]]}
        job.done = 1
        self._emit(job)

    def _do_batchrename(self, job: Job) -> None:
        items = []
        for source, dest in job.renames or []:
            if job.cancel.is_set():
                break
            job.current = source
            if os.path.abspath(source) == os.path.abspath(dest):
                job.done += 1
                self._emit(job)
                continue
            try:
                if os.path.lexists(dest):
                    raise FileExistsError(dest)
                os.rename(source, dest)
                items.append([source, dest])
            except Exception as exc:
                self._error(job, source, exc)
            job.done += 1
            self._emit(job)
        if items:
            job.undo = {"kind": "rename", "items": items}

    def _do_emptytrash(self, job: Job) -> None:
        trash_mod.empty()
        job.done = 1
        self._emit(job)

    def _do_mkdir(self, job: Job) -> None:
        os.makedirs(job.dest, exist_ok=False)
        job.undo = {"kind": "mkdir", "paths": [job.dest]}
        job.done = 1
        self._emit(job)

    def _do_newfile(self, job: Job) -> None:
        with open(job.dest, "x"):
            pass
        job.undo = {"kind": "newfile", "paths": [job.dest]}
        job.done = 1
        self._emit(job)

    def _do_undo(self, job: Job) -> None:
        record = self.journal.last()
        if not record:
            raise RuntimeError("nothing to undo")
        kind = record.get("kind")
        job.current = kind
        job.total = 1
        if kind == "copy":
            for target in record.get("targets", []):
                if os.path.lexists(target):
                    self.trash.trash(target)
        elif kind == "move":
            for src, dst in record.get("moves", []):
                if not os.path.lexists(dst):
                    continue
                if os.path.lexists(src):
                    raise FileExistsError(src)
                shutil.move(dst, src)
        elif kind == "trash":
            for path in record.get("paths", []):
                self.trash.restore(path)
        elif kind == "rename":
            for old, new in record.get("items", []):
                if os.path.lexists(old):
                    raise FileExistsError(old)
                os.rename(new, old)
        elif kind == "mkdir":
            for path in record.get("paths", []):
                os.rmdir(path)
        elif kind == "newfile":
            for path in record.get("paths", []):
                if os.path.lexists(path):
                    self.trash.trash(path)
        else:
            raise ValueError(f"cannot undo {kind}")
        self.journal.mark_undo(record)
        job.done = 1
        self._emit(job)

    def _copy_plain(self, src: str, dst: str) -> None:
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
            return
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            for name in os.listdir(src):
                self._copy_plain(os.path.join(src, name), os.path.join(dst, name))
            return
        shutil.copy2(src, dst)

    def _do_redo(self, job: Job) -> None:
        record = self.journal.last_redo()
        if not record:
            raise RuntimeError("nothing to redo")
        kind = record.get("kind")
        job.current = kind
        if kind == "copy":
            for src, target in record.get("items", []):
                if os.path.lexists(target):
                    raise FileExistsError(target)
                self._copy_plain(src, target)
        elif kind == "move":
            for src, dst in record.get("moves", []):
                if os.path.lexists(dst):
                    raise FileExistsError(dst)
                shutil.move(src, dst)
        elif kind == "trash":
            for path in record.get("paths", []):
                self.trash.trash(path)
        elif kind == "rename":
            for old, new in record.get("items", []):
                if os.path.lexists(new):
                    raise FileExistsError(new)
                os.rename(old, new)
        elif kind == "mkdir":
            for path in record.get("paths", []):
                os.makedirs(path, exist_ok=False)
        elif kind == "newfile":
            for path in record.get("paths", []):
                with open(path, "x"):
                    pass
        else:
            raise ValueError(f"cannot redo {kind}")
        self.journal.mark_redo(record)
        job.done = 1
        self._emit(job)
