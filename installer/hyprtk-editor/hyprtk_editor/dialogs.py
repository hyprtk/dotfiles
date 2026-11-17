"""Widget-side styling for the file dialogs.

The editor itself is Qt Quick, but ``QFileDialog`` is a widget dialog, so the
platform theme (here GTK/Adwaita) paints it unless told otherwise — which left
a light GTK window bolted onto a dark pywal editor. These helpers dress the
dialog in the same palette the QML surfaces use: a widget palette for every
colour the style draws (text, inputs, selections, arrows, check marks) plus a
stylesheet for the shapes and accents the palette cannot express.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QIcon, QPalette
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFileDialog, QListView

from .palette import FALLBACK


def _hex(palette: dict, key: str) -> str:
    value = palette.get(key)
    if isinstance(value, str) and value.startswith("#"):
        return value
    return FALLBACK[key]


def _color(palette: dict, key: str) -> QColor:
    return QColor(_hex(palette, key))


def qpalette(palette: dict) -> QPalette:
    """A widget palette with the editor's colours in every role."""
    window = _color(palette, "background")
    surface = _color(palette, "surface")
    text = _color(palette, "foreground")
    muted = _color(palette, "muted")
    accent = _color(palette, "accent")
    border = _color(palette, "border")

    pal = QPalette()
    pal.setColor(QPalette.Window, window)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, surface)
    pal.setColor(QPalette.AlternateBase, window)
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, surface)
    pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.BrightText, _color(palette, "danger"))
    pal.setColor(QPalette.Highlight, accent)
    pal.setColor(QPalette.HighlightedText, _color(palette, "text_on_accent"))
    pal.setColor(QPalette.ToolTipBase, surface)
    pal.setColor(QPalette.ToolTipText, text)
    pal.setColor(QPalette.PlaceholderText, muted)
    pal.setColor(QPalette.Link, _color(palette, "accent2"))
    pal.setColor(QPalette.LinkVisited, _color(palette, "accent2"))
    pal.setColor(QPalette.Light, border)
    pal.setColor(QPalette.Midlight, border)
    pal.setColor(QPalette.Mid, border)
    pal.setColor(QPalette.Dark, window)
    pal.setColor(QPalette.Shadow, window)

    # A disabled dialog still reads as the editor, just dimmer.
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, muted)
    pal.setColor(QPalette.Disabled, QPalette.Base, window)
    pal.setColor(QPalette.Disabled, QPalette.Button, window)
    return pal


def style_sheet(palette: dict, font_family: str = "", font_size: int = 13) -> str:
    """Shapes, spacing and accent states for the widget dialog."""
    background = _hex(palette, "background")
    foreground = _hex(palette, "foreground")
    surface = _hex(palette, "surface")
    surface_alt = _hex(palette, "surface_alt")
    muted = _hex(palette, "muted")
    accent = _hex(palette, "accent")
    accent2 = _hex(palette, "accent2")
    border = _hex(palette, "border")
    on_accent = _hex(palette, "text_on_accent")

    try:
        size = max(8, min(48, int(font_size)))
    except (TypeError, ValueError):
        size = 13
    family = f'font-family: "{font_family}"; ' if font_family else ""

    return f"""
QFileDialog {{
    background-color: {background};
    color: {foreground};
    {family}font-size: {size}px;
}}
QFileDialog QLabel {{
    background: transparent;
    color: {foreground};
}}
QLineEdit, QComboBox {{
    background-color: {surface};
    color: {foreground};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 3px 7px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QLineEdit:focus, QComboBox:focus, QComboBox:on {{
    border-color: {accent};
}}
QComboBox::drop-down {{
    border: 0;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {foreground};
    border: 1px solid {border};
    outline: 0;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QPushButton {{
    background-color: {surface};
    color: {foreground};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 16px;
    min-width: 72px;
}}
QPushButton:hover {{
    background-color: {surface_alt};
}}
QPushButton[primary="true"] {{
    background-color: {accent};
    color: {on_accent};
    border-color: {accent};
}}
QPushButton[primary="true"]:hover {{
    border-color: {accent2};
}}
QPushButton[primary="true"]:disabled {{
    background-color: {surface};
    color: {muted};
    border-color: {surface_alt};
}}
QPushButton:pressed {{
    border-color: {accent};
}}
QPushButton:default {{
    background-color: {accent};
    color: {on_accent};
    border-color: {accent};
}}
QPushButton:default:hover {{
    border-color: {accent2};
}}
QPushButton:disabled {{
    background-color: {surface};
    color: {muted};
    border-color: {surface_alt};
}}
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 3px;
}}
QToolButton:hover {{
    background-color: {surface_alt};
}}
QToolButton:pressed {{
    background-color: {accent};
}}
QListView, QTreeView {{
    background-color: {surface};
    alternate-background-color: {background};
    color: {foreground};
    border: 1px solid {border};
    border-radius: 6px;
    outline: 0;
}}
QListView::item, QTreeView::item {{
    padding: 3px;
    border-radius: 4px;
}}
QListView::item:hover, QTreeView::item:hover {{
    background-color: {surface_alt};
}}
QListView::item:selected, QTreeView::item:selected {{
    background-color: {accent};
    color: {on_accent};
}}
QHeaderView {{
    background-color: {background};
}}
QHeaderView::section {{
    background-color: {background};
    color: {muted};
    border: 0;
    border-bottom: 1px solid {border};
    padding: 4px 6px;
}}
QAbstractScrollArea::corner {{
    background: {background};
    border: 0;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {surface_alt};
    border-radius: 5px;
    min-height: 26px;
}}
QScrollBar::handle:vertical:hover {{
    background: {accent};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {surface_alt};
    border-radius: 5px;
    min-width: 26px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {accent};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
    border: 0;
    background: transparent;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}
QSplitter::handle {{
    background: transparent;
    width: 6px;
}}
QMenu {{
    background-color: {surface};
    color: {foreground};
    border: 1px solid {border};
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 22px 5px 10px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {accent};
    color: {on_accent};
}}
QMenu::separator {{
    height: 1px;
    background: {border};
    margin: 4px 6px;
}}
QToolTip {{
    background-color: {surface};
    color: {foreground};
    border: 1px solid {border};
    padding: 3px 6px;
}}
QCheckBox {{
    color: {foreground};
    background: transparent;
}}
QDialogButtonBox {{
    background: transparent;
}}
"""


def apply(dialog, palette: dict, font_family: str = "", font_size: int = 13) -> None:
    """Dress one dialog in the editor palette."""
    dialog.setPalette(qpalette(palette))
    dialog.setStyleSheet(style_sheet(palette, font_family, font_size))
    dress_buttons(dialog)
    dress_filter_combo(dialog)


def dress_filter_combo(dialog) -> None:
    """Keep the long name filter from widening the dialog to half the screen.

    Without a stylesheet the style elides the filter text; once the combo is
    stylesheet-drawn its size hint is the whole filter string, which made the
    dialog ~1570 px wide.
    """
    combo = dialog.findChild(QComboBox, "fileTypeCombo")
    if combo is not None:
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(20)
    # The QListView item padding above shrinks the places sidebar's hint to
    # about 100 px, which clips "Computer" and the home folder name.
    sidebar = dialog.findChild(QListView, "sidebar")
    if sidebar is not None:
        sidebar.setMinimumWidth(170)


def dress_buttons(dialog) -> None:
    """Strip the platform icons and mark the accept button as primary."""
    box = dialog.findChild(QDialogButtonBox)
    if box is None:
        return
    for button in box.buttons():
        # The icon theme puts a blue floppy on Save and a red cross on Cancel.
        # They are the last remnant of the GTK look and they fight a
        # palette-coloured dialog, so the buttons are plain text.
        button.setIcon(QIcon())
        if box.buttonRole(button) == QDialogButtonBox.AcceptRole:
            # Qt only highlights the accept button through the style's own idea
            # of a "default" button, so mark it explicitly and let the
            # stylesheet paint it with the accent.
            button.setDefault(True)
            button.setProperty("primary", True)
            # A stylesheet attribute selector is resolved when the widget is
            # polished, so the flag set after the stylesheet was applied has to
            # be polished in again or it stays invisible.
            button.style().unpolish(button)
            button.style().polish(button)


class ThemedFileDialog(QFileDialog):
    """A file dialog dressed in the editor palette.

    QFileDialog reconfigures itself — and rebuilds its standard buttons — when
    the accept mode changes or the dialog is shown, which throws away whatever
    was set on those buttons at construction time. So the dressing is applied
    again after every show, once the rebuild has settled.
    """

    def __init__(self, palette: dict, font_family: str = "", font_size: int = 13,
                 parent=None) -> None:
        super().__init__(parent)
        # With QT_QPA_PLATFORMTHEME=gtk3 (what the launcher sets) the platform
        # theme offers a native GTK file chooser, which ignores every colour we
        # could give it — that is the GTK-looking window this is here to
        # replace. Insist on the Qt dialog so the palette actually applies.
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self._theme = palette
        self._family = font_family
        self._size = font_size
        self.dress()
        self._resize_for_screen()

    def _resize_for_screen(self) -> None:
        """Give the dialog a workable default size on the current screen."""
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.resize(min(900, int(area.width() * 0.7)), min(560, int(area.height() * 0.7)))

    def dress(self) -> None:
        apply(self, self._theme, self._family, self._size)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.dress)
