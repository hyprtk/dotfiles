"""The QML-facing facade.

Everything the UI needs crosses this one object: file dialogs, document I/O,
language detection, highlighting, search, line operations, settings, session
and drafts. It is deliberately a thin layer over the pure modules so those can
be tested without a display.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQuick import QQuickTextDocument
from PySide6.QtWidgets import QFileDialog

from . import __version__, fileio, languages, palette, search, textops
from .highlight import PAGE_BLOCKS, Highlighter, spans
from .session import Drafts, Session
from .settings import MONO_FAMILIES, Settings

OPEN_FILTER = (
    "Text and code (*.txt *.md *.markdown *.rst *.org *.py *.qml *.js *.ts "
    "*.json *.yaml *.yml *.toml *.ini *.conf *.sh *.zsh *.c *.h *.cpp *.hpp "
    "*.rs *.go *.lua *.sql *.css *.scss *.html *.xml *.desktop);;All files (*)"
)


@dataclass
class Attached:
    area: QObject
    qdoc: QQuickTextDocument
    document: object
    highlighter: Highlighter
    alias: str = "text"
    path: str = ""
    last_spans: dict = field(default_factory=dict)


class Bridge(QObject):
    paletteChanged = Signal()
    settingsChanged = Signal()
    recentChanged = Signal()
    draftsChanged = Signal()
    fileChanged = Signal(str)
    toast = Signal(str, str)

    def __init__(self, parent=None, initial=None) -> None:
        super().__init__(parent)
        self.settings = Settings()
        self._palette = palette.resolve()
        self.session = Session()
        self.drafts_store = Drafts()
        self._editors: dict[str, Attached] = {}
        self._initial: list[str] = [str(p) for p in (initial or [])]
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._path_docs: dict[str, set[str]] = {}

        # Watch the live pywal palette so the editor follows a wallpaper change
        # without a restart, like the bar does.
        self._wal_watch = QFileSystemWatcher(self)
        wal = os.path.join(
            os.environ.get("HYPRTK_WAL_HOME") or os.path.expanduser("~"),
            ".cache", "wal", "colors.json",
        )
        if os.path.exists(wal):
            self._wal_watch.addPath(wal)
        self._wal_watch.fileChanged.connect(self.reloadPalette)

    # -- properties ------------------------------------------------------
    @Property("QVariantMap", notify=paletteChanged)
    def palette(self):
        # QML receives QVariantMaps as JS objects, so a hex string arrives as a
        # *string*: ``th.accent.r`` is undefined and Util.alpha() silently
        # produced black. Hand QML real QColor values instead.
        data = dict(self._palette)
        for key in (
            "background", "foreground", "surface", "surface_alt", "muted",
            "accent", "accent2", "danger", "warning", "success", "info",
            "border", "text_on_accent",
        ):
            value = data.get(key)
            if isinstance(value, str):
                data[key] = QColor(value)
        # QML reads camelCase roles; the toolkit-free resolver keeps snake_case.
        data["surfaceAlt"] = data.get("surface_alt")
        data["onAccent"] = data.get("text_on_accent")

        syntax = {}
        for key, value in (data.get("syntax") or {}).items():
            syntax[key] = QColor(value) if isinstance(value, str) else value
        data["syntax"] = syntax
        ansi = data.get("ansi") or []
        data["ansi"] = [QColor(value) if isinstance(value, str) else value for value in ansi]
        return data

    @Property("QVariantMap", notify=settingsChanged)
    def config(self):
        return self.settings.as_dict()

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property(str, notify=settingsChanged)
    def fontFamily(self):
        return self.settings.resolved_font()

    @Property("QVariantList", constant=True)
    def languages(self):
        return languages.languages()

    @Property("QVariantList", notify=recentChanged)
    def recent(self):
        values = []
        for path in self.settings.get("recent") or []:
            if os.path.exists(path):
                values.append({
                    "path": path,
                    "name": fileio.display_name(path),
                    "folder": os.path.dirname(path),
                })
        return values

    @Property("QVariantList", notify=draftsChanged)
    def drafts(self):
        return self.drafts_store.list()

    @Property("QVariantList", constant=True)
    def initialFiles(self):
        return self._initial

    @Property("QVariantList", constant=True)
    def fontChoices(self):
        return [{"name": name} for name in MONO_FAMILIES]

    # -- ids -------------------------------------------------------------
    @Slot(result=str)
    def newId(self):
        return uuid.uuid4().hex

    # -- file dialogs ----------------------------------------------------
    def _start_dir(self) -> str:
        last = str(self.settings.get("last_open_dir") or "")
        if last and os.path.isdir(last):
            return last
        home = os.path.expanduser("~")
        return home if os.path.isdir(home) else ""

    @Slot(result="QVariantList")
    def openDialog(self):
        parent = QGuiApplication.activeWindow()
        files, _ = QFileDialog.getOpenFileNames(parent, "Open File", self._start_dir(), OPEN_FILTER)
        if files:
            self.settings.set("last_open_dir", os.path.dirname(files[0]))
        return files

    @Slot(str, result=str)
    def saveDialog(self, suggested: str = ""):
        parent = QGuiApplication.activeWindow()
        start = suggested or os.path.join(self._start_dir(), "Untitled.txt")
        path, _ = QFileDialog.getSaveFileName(parent, "Save File", start, OPEN_FILTER)
        if path:
            self.settings.set("last_open_dir", os.path.dirname(path))
        return path

    @Slot(str, result=str)
    def folderDialog(self, suggested: str = ""):
        parent = QGuiApplication.activeWindow()
        path = QFileDialog.getExistingDirectory(parent, "Open Folder", suggested or self._start_dir())
        if path:
            self.settings.set("last_open_dir", path)
        return path

    # -- documents -------------------------------------------------------
    @Slot(str, result="QVariantMap")
    def load(self, path: str):
        loaded = fileio.read_text(path)
        data = loaded.as_dict()
        first_line = loaded.text.split("\n", 1)[0] if loaded.text else ""
        alias = languages.detect(path, first_line)
        data["language"] = alias
        data["languageName"] = languages.display_name(alias)
        data["title"] = fileio.display_name(path)
        data["id"] = self.newId()
        if not loaded.ok:
            data["encoding"] = "utf-8"
            data["eol"] = "lf"
        return data

    @Slot(str, result=str)
    def encodingLabel(self, codec: str):
        return fileio.DISPLAY_ENCODING.get(codec or "utf-8", (codec or "utf-8").upper())

    @Slot(str, result=float)
    def mtime(self, path: str):
        return fileio.file_mtime(path)

    @Slot(str, result=str)
    def commentPrefix(self, alias: str):
        tokens = languages.comment_tokens(alias or "text")
        return tokens[0] if tokens else "#"

    @Slot(str, str, result="QVariantMap")
    def detect(self, path: str, first_line: str = ""):
        alias = languages.detect(path, first_line)
        return {"alias": alias, "name": languages.display_name(alias)}

    @Slot(str, str, str, bool, float, result="QVariantMap")
    def save(self, path: str, text: str, encoding: str, eol: str, bom: bool, expected_mtime: float = 0.0):
        if self.settings.get("trim_trailing_on_save"):
            text = textops.trim_trailing(text, 0, 0)["text"]
        result = fileio.write_text(path, text, encoding, eol, bom, expected_mtime)
        if result.get("ok"):
            self.settings.add_recent(path)
            self.recentChanged.emit()
            result["text"] = text
            result["title"] = fileio.display_name(path)
        return result

    @Slot(str, int, result="QVariantMap")
    def bracketMatch(self, text: str, position: int):
        position = max(0, min(int(position), len(text)))
        if len(text) > 400_000:
            return {"ok": False}
        pairs = {"(": ")", "[": "]", "{": "}"}
        closers = {value: key for key, value in pairs.items()}

        anchor = -1
        forward = True
        if position > 0 and text[position - 1] in pairs:
            anchor = position - 1
            forward = True
        elif position < len(text) and text[position] in pairs:
            anchor = position
            forward = True
        elif position > 0 and text[position - 1] in closers:
            anchor = position - 1
            forward = False
        elif position < len(text) and text[position] in closers:
            anchor = position
            forward = False
        if anchor < 0:
            return {"ok": False}

        opener = text[anchor] if forward else closers[text[anchor]]
        closer = pairs[opener] if forward else text[anchor]
        depth = 0
        step = 1 if forward else -1
        index = anchor
        limit = min(len(text), 200_000)
        while 0 <= index < limit:
            char = text[index]
            if char == (opener if forward else closer):
                depth += 1
            elif char == (closer if forward else opener):
                depth -= 1
                if depth == 0:
                    return {"ok": True, "positions": [self._line_col(text, anchor), self._line_col(text, index)]}
            index += step
        return {"ok": False}

    @staticmethod
    def _line_col(text: str, position: int) -> list[int]:
        line = text.count("\n", 0, max(0, position))
        start = text.rfind("\n", 0, max(0, position)) + 1
        return [line, max(0, position - start)]

    # -- editor attachment ----------------------------------------------
    @Slot("QVariant", str)
    def attach(self, area, doc_id: str):
        try:
            qdoc = area.property("textDocument")
            if qdoc is None:
                return
            document = qdoc.textDocument()
        except Exception:
            return
        highlighter = Highlighter(document, self._palette, self.settings.as_dict())
        highlighter.set_current_line(0)
        self._editors[str(doc_id)] = Attached(
            area=area, qdoc=qdoc, document=document, highlighter=highlighter
        )

    @Slot(str)
    def detach(self, doc_id: str):
        item = self._editors.pop(str(doc_id), None)
        if item is not None:
            item.highlighter.setDocument(None)
            item.highlighter.deleteLater()
            if item.path and item.path in self._path_docs:
                self._path_docs[item.path].discard(str(doc_id))
                if not self._path_docs[item.path] and item.path in self._watcher.files():
                    self._watcher.removePath(item.path)

    @Slot(str, str)
    def setPath(self, doc_id: str, path: str):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        if item.path and item.path in self._path_docs:
            self._path_docs[item.path].discard(str(doc_id))
            if not self._path_docs[item.path] and item.path in self._watcher.files():
                self._watcher.removePath(item.path)
        item.path = str(path or "")
        if item.path:
            self._path_docs.setdefault(item.path, set()).add(str(doc_id))
            if os.path.exists(item.path) and item.path not in self._watcher.files():
                self._watcher.addPath(item.path)

    @Slot(str, int, int)
    def refresh(self, doc_id: str, first: int, last: int):
        item = self._editors.get(str(doc_id))
        if item is None or not item.highlighter.enabled:
            return
        count = item.document.blockCount()
        first = max(0, min(int(first), count - 1))
        last = max(first, min(int(last), count - 1))
        if last - first > PAGE_BLOCKS * 2:
            last = first + PAGE_BLOCKS * 2
        for number in range(first, last + 1):
            block = item.document.findBlockByNumber(number)
            if block.isValid():
                item.highlighter.rehighlightBlock(block)

    @Slot(str, int, int)
    def recompute(self, doc_id: str, first: int = 0, last: int = 0):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        text = item.document.toPlainText()
        if not self.settings.get("syntax", True) or len(text) > 400_000:
            item.highlighter.set_spans({})
            item.highlighter.set_enabled(False)
            return
        item.highlighter.set_enabled(True)
        item.highlighter.set_spans(spans(text, item.alias))
        self.refresh(doc_id, first, last)

    @Slot(str, str)
    def setLanguage(self, doc_id: str, alias: str):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        item.alias = alias or "text"
        self.recompute(doc_id, 0, PAGE_BLOCKS)

    @Slot(str, int)
    def setCurrentLine(self, doc_id: str, line: int):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        old = item.highlighter.current_line
        item.highlighter.set_current_line(int(line))
        first = max(0, min(old, int(line)))
        last = max(old, int(line))
        self.refresh(doc_id, first, last)

    @Slot(str, "QVariant")
    def setSearch(self, doc_id: str, ranges):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        values = []
        for entry in ranges or []:
            try:
                values.append((int(entry.get("start", 0)), int(entry.get("length", 0)), bool(entry.get("current", False))))
            except Exception:
                continue
        item.highlighter.set_search(values)

    @Slot(str, "QVariant")
    def setBrackets(self, doc_id: str, state):
        item = self._editors.get(str(doc_id))
        if item is None:
            return
        positions = []
        if isinstance(state, dict) and state.get("ok"):
            positions = state.get("positions") or []
        item.highlighter.set_brackets(positions)

    # -- finding ---------------------------------------------------------
    @staticmethod
    def _query(needle, case, word, regex, multiline=False) -> search.Query:
        return search.Query(text=str(needle or ""), case=bool(case), word=bool(word), regex=bool(regex), multiline=bool(multiline))

    @Slot(str, str, bool, bool, bool, result="QVariantList")
    def findAll(self, text: str, needle: str, case: bool, word: bool, regex: bool):
        return search.find_all(text, self._query(needle, case, word, regex))

    @Slot(str, str, int, bool, bool, bool, bool, result="QVariantMap")
    def findNext(self, text: str, needle: str, position: int, case: bool, word: bool, regex: bool, backwards: bool):
        match = search.find_next(text, self._query(needle, case, word, regex), position, backwards)
        return match or {}

    @Slot(str, str, str, bool, bool, bool, result="QVariantMap")
    def replaceAll(self, text: str, needle: str, replacement: str, case: bool, word: bool, regex: bool):
        new_text, count = search.replace_all(text, self._query(needle, case, word, regex), replacement)
        return {"text": new_text, "count": count}

    # -- editing helpers -------------------------------------------------
    @Slot(str, int, int, str, str, int, bool, result="QVariantMap")
    def lineOp(self, text: str, sel_start: int, sel_end: int, op: str, comment: str, width: int, spaces: bool):
        if op == "toggleComment":
            return textops.toggle_comment(text, sel_start, sel_end, comment or "#")
        if op == "indent":
            return textops.indent(text, sel_start, sel_end, width, spaces)
        if op == "outdent":
            return textops.outdent(text, sel_start, sel_end, width, spaces)
        if op in ("upper", "lower", "title"):
            return textops.change_case(text, sel_start, sel_end, op)
        if op == "toSpaces":
            return textops.convert_indent(text, sel_start, sel_end, True, width)
        if op == "toTabs":
            return textops.convert_indent(text, sel_start, sel_end, False, width)
        if op == "trimTrailing":
            return textops.trim_trailing(text, sel_start, sel_end)
        return textops.apply(text, sel_start, sel_end, op)

    @Slot(str, int, int, result="QVariantMap")
    def stats(self, text: str, sel_start: int = 0, sel_end: int = 0):
        data = textops.stats(text, sel_start, sel_end)
        data["bytesHuman"] = fileio.human_bytes(data["bytes"])
        return data

    # -- drafts / session ------------------------------------------------
    @Slot(str, str, str, str)
    def saveDraft(self, doc_id: str, path: str, title: str, text: str):
        self.drafts_store.save(str(doc_id), str(path), str(title), str(text))
        self.draftsChanged.emit()

    @Slot(str, result="QVariantMap")
    def loadDraft(self, doc_id: str):
        return self.drafts_store.load(str(doc_id)) or {}

    @Slot(str)
    def clearDraft(self, doc_id: str):
        self.drafts_store.clear(str(doc_id))
        self.draftsChanged.emit()

    @Slot(result="QVariantMap")
    def loadSession(self):
        return self.session.load()

    @Slot("QVariant")
    def saveSession(self, data):
        try:
            self.session.save(dict(data or {}))
        except Exception:
            pass

    # -- settings --------------------------------------------------------
    @Slot("QVariant")
    def updateSettings(self, data):
        if not isinstance(data, dict):
            return
        patch = {}
        for key, value in data.items():
            patch[str(key)] = value
        self.settings.update(patch)
        for item in self._editors.values():
            item.highlighter.opts = self.settings.as_dict()
        self.settingsChanged.emit()
        self.paletteChanged.emit()

    @Slot(str)
    def addRecent(self, path: str):
        if path:
            self.settings.add_recent(path)
            self.recentChanged.emit()

    @Slot()
    def clearRecent(self):
        self.settings.clear_recent()
        self.recentChanged.emit()

    # -- suite integration ----------------------------------------------
    @Slot(str)
    def openInFileManager(self, path: str):
        target = path if os.path.isdir(path) else os.path.dirname(path)
        exe = shutil.which("hyprtk-fm")
        try:
            if exe:
                subprocess.Popen([exe, target or os.path.expanduser("~")], start_new_session=True)
            else:
                subprocess.Popen(["xdg-open", target or os.path.expanduser("~")], start_new_session=True)
        except OSError as exc:
            self.toast.emit(str(exc), "error")

    @Slot(str)
    def openTerminal(self, path: str):
        target = path if os.path.isdir(path) else os.path.dirname(path)
        target = target or os.path.expanduser("~")
        candidates = [
            ("alacritty", ["--working-directory", target]),
            ("kitty", ["--directory", target]),
            ("foot", ["--working-directory", target]),
            ("xterm", ["-cd", target]),
        ]
        for name, args in candidates:
            exe = shutil.which(name)
            if exe:
                try:
                    subprocess.Popen([exe, *args], start_new_session=True)
                    return
                except OSError:
                    continue
        self.toast.emit("No terminal found", "error")

    @Slot(str)
    def copyToClipboard(self, text: str):
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    # -- palette ---------------------------------------------------------
    @Slot()
    def reloadPalette(self):
        self._palette = palette.resolve()
        for item in self._editors.values():
            item.highlighter.apply_palette(self._palette)
        # The UI refreshes its visible window once the new colours are bound;
        # rehighlighting every block here would be the quadratic path.
        self.paletteChanged.emit()

    # -- internals -------------------------------------------------------
    def _on_file_changed(self, path: str):
        # inotify watches the inode; an atomic save replaces it, so re-arm.
        if os.path.exists(path) and path not in self._watcher.files():
            self._watcher.addPath(path)
        self.fileChanged.emit(path)
