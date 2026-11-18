"""The QML-facing facade.

Everything the UI needs crosses this one object: evaluation, the history list,
the memory register, persisted settings, the palette and clipboard access. It
stays a thin layer over the pure modules so those keep being testable without a
display.
"""

from __future__ import annotations

import os
from decimal import Decimal

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication

from . import __version__, palette
from .evaluator import Context, evaluate
from .history import History
from .number import CalcError, all_bases, format_number
from .settings import Settings


class Bridge(QObject):
    paletteChanged = Signal()
    settingsChanged = Signal()
    historyChanged = Signal()
    memoryChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.settings = Settings()
        self.history = History(limit=int(self.settings.get("history_limit")))
        self._palette = palette.resolve()
        self._memory = Decimal(0)
        self._ans = Decimal(0)

    # -- properties ------------------------------------------------------
    @Property("QVariantMap", notify=paletteChanged)
    def palette(self):
        # QML receives QVariantMaps as JS objects, so a hex string arrives as a
        # *string* and ``th.accent.r`` is undefined. Hand QML real QColors.
        data = dict(self._palette)
        for key, value in list(data.items()):
            if isinstance(value, str) and value.startswith("#"):
                data[key] = QColor(value)
        data["opacity"] = float(data.get("opacity") or 0.98)
        return data

    @Property("QVariantMap", notify=settingsChanged)
    def config(self):
        return self.settings.as_dict()

    @Property("QVariantList", notify=historyChanged)
    def historyRows(self):
        return [entry.as_row() for entry in self.history.newest_first(120)]

    @Property(str, notify=memoryChanged)
    def memoryValue(self):
        return format_number(self._memory, self._precision())

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property(bool, notify=memoryChanged)
    def memorySet(self):
        return self._memory != 0

    # -- helpers ---------------------------------------------------------
    def _precision(self) -> int:
        return int(self.settings.get("precision"))

    def context(self) -> Context:
        return Context(
            precision=self._precision(),
            angle=str(self.settings.get("angle")),
            ans=self._ans,
        )

    def _row(self, text: str, value: Decimal) -> dict:
        precision = self._precision()
        bases = {}
        if value == value.to_integral_value():
            bases = {str(base): number for base, number in all_bases(value).items()}
        return {
            "ok": True,
            "display": format_number(
                value, precision, grouping=str(self.settings.get("grouping"))
            ),
            "error": "",
            "bases": bases,
            "value": format_number(value, max(precision, 15)),
        }

    # -- slots -----------------------------------------------------------
    def _compute(self, text):
        """Evaluate once; returns (value or None, result row)."""
        if not (text or "").strip():
            return None, {"ok": False, "display": "", "error": "", "bases": {}, "value": ""}
        try:
            value = evaluate(text, self.context())
        except CalcError as exc:
            return None, {"ok": False, "display": "", "error": str(exc), "bases": {}, "value": ""}
        except Exception as exc:  # pragma: no cover - a parser bug must not kill the UI
            return None, {
                "ok": False,
                "display": "",
                "error": "could not evaluate: {0}".format(exc),
                "bases": {},
                "value": "",
            }
        return value, self._row(text, value)

    @Slot(str, result="QVariantMap")
    def evaluate(self, text):
        """Evaluate without recording; the live result line."""
        return self._compute(text)[1]

    @Slot(str, result="QVariantMap")
    def commit(self, text):
        """Evaluate, record in history, and make the answer ``ans``."""
        value, row = self._compute(text)
        if row.get("ok") and value is not None:
            self._ans = value
            self.history.add(text.strip(), row["display"])
            self.historyChanged.emit()
        return row

    @Slot(str, result=bool)
    def copy(self, text):
        if not text:
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:  # pragma: no cover - headless without a platform
            return False
        clipboard.setText(text)
        return True

    @Slot(int, result=str)
    def recall(self, index):
        rows = self.history.newest_first(120)
        try:
            return rows[int(index)].expression
        except (IndexError, TypeError, ValueError):
            return ""

    @Slot(int, result=str)
    def resultAt(self, index):
        rows = self.history.newest_first(120)
        try:
            return rows[int(index)].result
        except (IndexError, TypeError, ValueError):
            return ""

    @Slot()
    def clearHistory(self):
        self.history.clear()
        self.historyChanged.emit()

    @Slot(str, str)
    def memory(self, action):
        """``clear``, ``recall``, ``add``, ``subtract``, ``store``."""
        current = self._ans
        if action == "clear":
            self._memory = Decimal(0)
        elif action == "add":
            self._memory += current
        elif action == "subtract":
            self._memory -= current
        elif action == "store":
            self._memory = current
        elif action == "recall":
            pass
        else:
            return self.memoryValue
        self.memoryChanged.emit()
        return self.memoryValue

    @Slot(str, "QVariant")
    def setConfig(self, key, value):
        if self.settings.set(key, value):
            self.settings.save()
            if key == "history_limit":
                self.history.limit = int(self.settings.get("history_limit"))
            self.settingsChanged.emit()

    @Slot()
    def reloadPalette(self):
        self._palette = palette.resolve()
        self.paletteChanged.emit()

    @Slot(str, result=str)
    def format(self, value_text):
        """Used by the programmer readout: format a raw integer in one base."""
        try:
            return format_number(Decimal(value_text), self._precision())
        except (CalcError, ArithmeticError, ValueError):
            return ""
