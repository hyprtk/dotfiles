"""hyprtk-shot — the hyprtk desktop's screenshot tool.

Capture through ``grim``, select and annotate in a frozen fullscreen overlay,
then save, copy or both. Wayland-native: no X11 grab, no portal prompt for the
common case, and the frozen image means the overlay can never capture itself.

Qt Quick/QML chrome, Python geometry and rendering, and the same pywal palette
as the rest of the suite.
"""

__version__ = "0.2.5"

APP_NAME = "hyprtk-shot"
APP_ID = "hyprtk-shot"
BIN_NAME = "hyprtk-shot"
