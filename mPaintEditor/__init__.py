from __future__ import absolute_import
import os

PAINT_EDITOR = None
PAINT_EDITOR_ROOT = None

def runMPaintEditor():
    from .utils import rootWindow
    from .paintEditorWidget import SkinPaintWin

    # Keep global references around, otherwise they get GC'd
    global PAINT_EDITOR
    global PAINT_EDITOR_ROOT

    # make and show the UI
    if PAINT_EDITOR_ROOT is None:
        PAINT_EDITOR_ROOT = rootWindow()
    PAINT_EDITOR = SkinPaintWin(parent=PAINT_EDITOR_ROOT)
    PAINT_EDITOR.show()


if __name__ == "__main__":
    import sys

    folder = os.path.dirname(os.path.dirname(__file__))
    if folder not in sys.path:
        sys.path.insert(0, folder)
    runMPaintEditor()
