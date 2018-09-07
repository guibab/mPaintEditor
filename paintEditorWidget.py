"""
import __main__
self = __main__.paintEditor
"""
from Qt import QtGui, QtCore, QtWidgets

# import shiboken2 as shiboken
from functools import partial
from maya import cmds, OpenMaya
import blurdev
from studio.gui.resource import Icons

from mWeightEditor.tools.spinnerSlider import ValueSetting, ButtonWithValue


_icons = {
    "lock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\lock-48"),
    "unlock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\unlock-48"),
    "refresh": Icons.getIcon("refresh"),
}
styleSheet = """
QWidget {
    background:  #aba8a6;
    color:black;
    selection-background-color: #a0a0ff;
}
QCheckBox:hover
{
  background:rgb(120, 120, 120); 
}
QMenu::item:disabled {
    color:grey;
    font: italic;
}
QMenu::item:selected  {
    background-color:rgb(120, 120, 120);  
}
QPushButton {
    color:  black;
}
QPushButton:checked{
    background-color: rgb(80, 80, 80);
    color:white;
    border: none; 
}
QPushButton:hover{  
    background-color: grey; 
    border-style: outset;  
}
QPushButton:pressed {
    background-color: rgb(100, 100, 100);
    color:white;
    border-style: inset;
}
QPushButton:disabled {
    font:italic;
    color:grey;
    }

TableView {
     selection-background-color: #a0a0ff;
     background : #aba8a6;
     color: black;
     selection-color: black;
     border : 0px;
 }
QTableView QTableCornerButton::section {
    background:  transparent;
    border : 1px solid black;
}
 
TableView::section {
    background-color: #878787;
    color: black;
    border : 1px solid black;
}
QHeaderView::section {
    background-color: #878787;
    color: black;
    border : 1px solid black;
}
VertHeaderView{
    color: black;
    border : 0px solid black;
}
HorizHeaderView{
    color: black;
    border : 0px solid black;
}
"""
###################################################################################
#
#   the window
#
###################################################################################


class SkinPaintWin(QtWidgets.QDialog):
    """
    A simple test widget to contain and own the model and table.
    """

    colWidth = 30
    maxWidthCentralWidget = 230

    def addMinButton(self):
        # self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowFlags(QtCore.Qt.Window)

    def __init__(self, parent=None):
        super(SkinPaintWin, self).__init__(parent)
        import __main__

        __main__.__dict__["paintEditor"] = self

        if not cmds.pluginInfo("blurSkin", query=True, loaded=True):
            cmds.loadPlugin("blurSkin")
        blurdev.gui.loadUi(__file__, self)

        self.createWindow()
        self.setStyleSheet(styleSheet)
        self.setWindowDisplay()

    def setWindowDisplay(self):
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.Tool)
        self.setWindowTitle("Paint Editor")
        self.refreshPosition()
        self.show()

    def refreshPosition(self):
        vals = cmds.optionVar(q="SkinPaintWindow")
        if vals:
            self.move(vals[0], vals[1])
            self.resize(vals[2], vals[3])

    def closeEvent(self, event):
        # self.deleteCallBacks ()
        pos = self.pos()
        size = self.size()
        cmds.optionVar(clearArray="SkinPaintWindow")
        for el in pos.x(), pos.y(), size.width(), size.height():
            cmds.optionVar(intValueAppend=("SkinPaintWindow", el))
        # self.headerView.deleteLater()
        super(SkinPaintWin, self).closeEvent(event)

    def doAddValue(self, val):
        print val

    def addButtonsDirectSet(self, lstBtns):
        theCarryWidget = QtWidgets.QWidget()

        carryWidgLayoutlayout = QtWidgets.QHBoxLayout(theCarryWidget)
        carryWidgLayoutlayout.setContentsMargins(40, 0, 0, 0)
        carryWidgLayoutlayout.setSpacing(0)

        for theVal in lstBtns:
            newBtn = QtWidgets.QPushButton("{0:.0f}".format(theVal))

            newBtn.clicked.connect(partial(self.doAddValue, theVal / 100.0))

            carryWidgLayoutlayout.addWidget(newBtn)
        theCarryWidget.setMaximumSize(self.maxWidthCentralWidget, 14)

        return theCarryWidget

    def changeLock(self, val):
        if val:
            self.lock_btn.setIcon(_icons["lock"])
        else:
            self.lock_btn.setIcon(_icons["unlock"])
        self.unLock = not val

    def createWindow(self):
        self.unLock = True
        dialogLayout = self.layout()

        self.lock_btn.setIcon(_icons["unlock"])
        self.refresh_btn.setIcon(_icons["refresh"])
        self.lock_btn.toggled.connect(self.changeLock)
        self.refresh_btn.clicked.connect(self.refreshBtn)
        for nm in ["lock", "refresh"]:
            self.__dict__[nm + "_btn"].setText("")
        self.valueSetter = ValueSetting(self)
        Hlayout = QtWidgets.QHBoxLayout(self)
        Hlayout.setContentsMargins(0, 0, 0, 0)
        Hlayout.setSpacing(0)
        Hlayout.addWidget(self.valueSetter)
        self.valueSetter.setMaximumWidth(self.maxWidthCentralWidget)

        self.widgetAbs = self.addButtonsDirectSet(
            [0, 10, 25, 100.0 / 3, 50, 200 / 3.0, 75, 90, 100]
        )

        Hlayout2 = QtWidgets.QHBoxLayout(self)
        Hlayout2.setContentsMargins(0, 0, 0, 0)
        Hlayout2.setSpacing(0)
        Hlayout2.addWidget(self.widgetAbs)

        # dialogLayout.insertSpacing (1,0)
        dialogLayout.insertLayout(1, Hlayout)
        dialogLayout.insertLayout(1, Hlayout2)
        dialogLayout.insertSpacing(1, 10)

    def refreshBtn(self):
        # self.storeSelection ()
        self.refresh(force=True)
        # self.retrieveSelection ()

    def refresh(self, force=False):
        pass


# -------------------------------------------------------------------------------
# INFLUENCE ITEM
# -------------------------------------------------------------------------------
class InfluenceTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    _colors = [
        (161, 105, 48),
        (159, 161, 48),
        (104, 161, 48),
        (48, 161, 93),
        (48, 161, 161),
        (48, 103, 161),
        (111, 48, 161),
        (161, 48, 105),
    ]

    def __init__(self, influence):
        influence = dcc.maya.cast.toMFn(influence)
        super(InfluenceTreeWidgetItem, self).__init__(["", influence.name()])
        self._influence = influence

        self.setDisplay()

    def setDisplay(self):
        self.setIcon(0, self.colorIcon())
        self.setIcon(1, self.lockIcon())

    def setColor(self, index):
        objAsStr = dcc.maya.cast.toPath(self._influence)
        cmds.setAttr(objAsStr + ".objectColor", index)

        theCol = [col / 250.0 for col in self._colors[index]]
        cmds.setAttr(objAsStr + ".overrideColorRGB", *theCol)

        self.setDisplay()

    def color(self):
        return self._colors[cmds.getAttr(dcc.maya.cast.toPath(self._influence) + ".objectColor")]

    def lockIcon(self):
        return (
            IconsLibrary.getIcon("lock")
            if self.isLocked()
            else IconsLibrary.getIcon("lock-gray-unlocked")
        )

    def colorIcon(self):
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtGui.QColor(*self.color()))
        return QtGui.QIcon(pixmap)

    def setVisible(self, visible):
        self.setLocked(not visible)
        self.setHidden(not visible)

    def setLocked(self, locked):
        self._influence.findPlug("lockInfluenceWeights").setBool(locked)
        if locked:
            self.setSelected(False)
        self.setDisplay()

    def isLocked(self):
        return self._influence.findPlug("lockInfluenceWeights").asBool()

    def influence(self):
        return self._influence

    def showWeights(self, value):
        self.setText(2, str(value))


# -------------------------------------------------------------------------------
# COLOR
# -------------------------------------------------------------------------------
class ColorMenu(QtWidgets.QMenu):

    _colors = [
        (161, 105, 48),
        (159, 161, 48),
        (104, 161, 48),
        (48, 161, 93),
        (48, 161, 161),
        (48, 103, 161),
        (111, 48, 161),
        (161, 48, 105),
    ]

    def __init__(self, parent):
        super(ColorMenu, self).__init__(parent)

        self._color = None

        self.setFixedWidth(20)

        for index, color in enumerate(self._colors):
            pixmap = QtGui.QPixmap(12, 12)
            pixmap.fill(QtGui.QColor(*color))
            act = self.addAction("")
            act.setIcon(QtGui.QIcon(pixmap))
            act.triggered.connect(partial(self.pickColor, index))

    def pickColor(self, index):
        self._color = index

    def color(self):
        return self._color
