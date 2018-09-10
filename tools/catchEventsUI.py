from Qt import QtGui, QtCore, QtWidgets
from Qt.QtWidgets import QApplication, QSplashScreen, QDialog, QMainWindow


def rootWindow():
    """
    Returns the currently active QT main window
    Only works for QT UI's like Maya
    """
    # for MFC apps there should be no root window
    window = None
    if QApplication.instance():
        inst = QApplication.instance()
        window = inst.activeWindow()
        # Ignore QSplashScreen's, they should never be considered the root window.
        if isinstance(window, QSplashScreen):
            return None
        # If the application does not have focus try to find A top level widget
        # that doesn't have a parent and is a QMainWindow or QDialog
        if window == None:
            windows = []
            dialogs = []
            for w in QApplication.instance().topLevelWidgets():
                if w.parent() == None:
                    if isinstance(w, QMainWindow):
                        windows.append(w)
                    elif isinstance(w, QDialog):
                        dialogs.append(w)
            if windows:
                window = windows[0]
            elif dialogs:
                window = dialogs[0]
        # grab the root window
        if window:
            while True:
                parent = window.parent()
                if not parent:
                    break
                if isinstance(parent, QSplashScreen):
                    break
                window = parent
    return window


class CatchEventsWidget(QtWidgets.QWidget):
    # transparent widget over viewport to catch rightclicks
    verbose = False
    filterInstalled = False

    def __init__(self, connectedWindow=None):
        super(CatchEventsWidget, self).__init__(rootWindow())
        self.setMask(QtGui.QRegion(0, 0, 1, 1))
        self.mainWindow = connectedWindow
        self.NPressed = False
        self.brushValUpdate = False
        # self.setAttribute (QtCore.Qt.WA_MouseNoMask, True)

    def open(self):
        if not self.filterInstalled:
            self.installFilters()
        self.show()

    def installFilters(self):
        self.filterInstalled = True
        QApplication.instance().installEventFilter(self)

    def removeFilters(self):
        self.hide()
        self.filterInstalled = False
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseMove and event.modifiers() != QtCore.Qt.AltModifier:
            if self.NPressed:
                self.brushValUpdate = True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        if (
            event.type() in [QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease]
            and event.modifiers() != QtCore.Qt.AltModifier
        ):
            # if event.button() == QtCore.Qt.RightButton  : print "Right Click"
            # elif event.button() == QtCore.Qt.LeftButton  : print "Left Click"

            # theModifiers = QtCore.Qt.KeyboardModifiers (QtCore.Qt.NoModifier )
            if event.modifiers() == QtCore.Qt.NoModifier:
                if event.type() == QtCore.QEvent.MouseButtonRelease and self.brushValUpdate:
                    self.brushValUpdate = False
                    # print "!!! update Value of Brush !!!"
                    self.mainWindow.changeOfValue()
                return super(CatchEventsWidget, self).eventFilter(obj, event)
            else:
                # remove the alt and control
                altShift = (
                    event.modifiers()
                    == QtCore.Qt.AltModifier | event.modifiers()
                    == QtCore.Qt.ShiftModifier
                )
                altCtrl = (
                    event.modifiers()
                    == QtCore.Qt.AltModifier | event.modifiers()
                    == QtCore.Qt.ControlModifier
                )
                theModifiers = QtCore.Qt.KeyboardModifiers(QtCore.Qt.NoModifier)
                if altShift or altCtrl:
                    theModifiers = QtCore.Qt.KeyboardModifiers(QtCore.Qt.AltModifier)

                theMouseEvent = QtGui.QMouseEvent(
                    event.type(), event.pos(), event.button(), event.buttons(), theModifiers
                )
                QApplication.instance().postEvent(obj, theMouseEvent)
                event.ignore()
                return True
        elif event.type() == QtCore.QEvent.KeyRelease:
            if event.key() in [QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control]:
                if self.verbose:
                    print "custom SHIFT released"
                event.ignore()
                self.prevButton.click()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.NPressed = False  # the value of the brush
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Control:
                if self.verbose:
                    print "custom CONTROL pressed"
                event.ignore()
                self.prevButton = self.mainWindow.getEnabledButton()
                self.mainWindow.smooth_btn.click()
                return True
            elif event.key() == QtCore.Qt.Key_Shift:
                if self.verbose:
                    print "custom SHIFT pressed"
                event.ignore()
                self.prevButton = self.mainWindow.getEnabledButton()
                self.mainWindow.rmv_btn.setChecked(True)
                # self.mainWindow.rmv_btn.click()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.NPressed = True
            elif event.key() == QtCore.Qt.Key_Escape:
                print "CLOSING"
                event.ignore()
                self.close()
                return True
            shiftPressed = event.modifiers() == QtCore.Qt.ShiftModifier
            ctrlPressed = event.modifiers() == QtCore.Qt.ControlModifier
            altPressed = event.modifiers() == QtCore.Qt.AltModifier
            if ctrlPressed and event.key() == QtCore.Qt.Key_Z:
                if self.verbose:
                    print "custom UNDO"
                event.ignore()
                self.mainWindow.undo_btn.click()
                return True
            if event.key() == QtCore.Qt.Key_D:
                if altPressed:
                    if self.verbose:
                        print "custom pressed Alt D"
                    event.ignore()
                    self.mainWindow.pickMaxInfluence()
                    return True
                else:
                    if self.verbose:
                        print "custom pressed D"
                    event.ignore()
                    return True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        else:
            return super(CatchEventsWidget, self).eventFilter(obj, event)

    def closeEvent(self, e):
        """
        Make sure the eventFilter is removed
        """
        self.removeFilters()
        return super(CatchEventsWidget, self).closeEvent(e)


"""
a = CatchEventsWidget ()
"""
