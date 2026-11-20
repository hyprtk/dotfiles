"""hyprtk-rec — the hyprtk desktop's screen recorder.

A controller for the two recorders that actually work on a wlroots compositor:
``wf-recorder`` (the dependable default) and ``wl-screenrec`` (GPU-encoded when
it is installed). The app owns the source picker, the audio choice, the
countdown, the running state and the finished file — not the encoder.
"""

__version__ = "0.2.0"

APP_NAME = "hyprtk-rec"
APP_ID = "hyprtk-rec"
BIN_NAME = "hyprtk-rec"
