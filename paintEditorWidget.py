"""
import __main__
self = __main__.paintEditor
"""
from Qt import QtGui, QtCore, QtWidgets

# import shiboken2 as shiboken
from functools import partial
from maya import cmds, mel, OpenMaya
import blurdev
import os
from studio.gui.resource import Icons
from mWeightEditor.tools.skinData import DataOfSkin
from mWeightEditor.tools.spinnerSlider import ValueSetting, ButtonWithValue
from tools.brushFunctions import BrushFunctions


def getIcon(iconNm):
    fileVar = os.path.realpath(__file__)
    uiFolder, filename = os.path.split(fileVar)
    iconPth = os.path.join(uiFolder, "img", iconNm + ".png")
    return QtGui.QIcon(iconPth)


_icons = {
    "lock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\lock-48"),
    "unlock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\unlock-48"),
    "pinOn": getIcon("pinOn"),
    "pinOff": getIcon("pinOff"),
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

    def getSkinClusterValues(self, skinCluster):
        driverNames = cmds.skinCluster(skinCluster, q=True, inf=True)
        skinningMethod = cmds.getAttr(skinCluster + ".skinningMethod")
        normalizeWeights = cmds.getAttr(skinCluster + ".normalizeWeights")
        return (driverNames, skinningMethod, normalizeWeights)

    #####################################################################################
    def __init__(self, parent=None):
        super(SkinPaintWin, self).__init__(parent)
        import __main__

        __main__.__dict__["paintEditor"] = self

        if not cmds.pluginInfo("blurSkin", query=True, loaded=True):
            cmds.loadPlugin("blurSkin")
        blurdev.gui.loadUi(__file__, self)

        self.useShortestNames = (
            cmds.optionVar(q="useShortestNames")
            if cmds.optionVar(exists="useShortestNames")
            else True
        )
        self.dataOfSkin = DataOfSkin(useShortestNames=self.useShortestNames)

        self.brushFunctions = BrushFunctions()

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
        self.valueSetter.theProgress.applyVal(val)

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

    def changePin(self, val):
        if val:
            self.pinSelection_btn.setIcon(_icons["pinOn"])
        else:
            self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.unPin = not val

    def enterPaint(self):
        self.brushFunctions.setColorsOnJoints()
        self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
        if not self.brushFunctions.bsd:
            self.brushFunctions.addColorNode()
        self.brushFunctions.enterPaint()

    def updateOptionEnable(self, toggleValue):
        setOn = self.smooth_btn.isChecked() or self.sharpen_btn.isChecked()
        for btn in [self.repeatBTN, self.depthBTN]:
            btn.setEnabled(setOn)

    def createWindow(self):
        self.unLock = True
        self.unPin = True
        dialogLayout = self.layout()

        self.lock_btn.setIcon(_icons["unlock"])
        self.refresh_btn.setIcon(_icons["refresh"])
        self.lock_btn.toggled.connect(self.changeLock)
        self.refresh_btn.clicked.connect(self.refreshBtn)
        self.enterPaint_btn.clicked.connect(self.enterPaint)

        self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.pinSelection_btn.toggled.connect(self.changePin)
        self.pickVertex_btn.clicked.connect(self.pickMaxInfluence)
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)

        self.repeatBTN = ButtonWithValue(
            self.buttonWidg,
            usePow=False,
            name="iter",
            minimumValue=1,
            defaultValue=1,
            step=1,
            clickable=False,
            minHeight=20,
        )
        self.depthBTN = ButtonWithValue(
            self.buttonWidg,
            usePow=False,
            name="dpth",
            minimumValue=1,
            maximumValue=9,
            defaultValue=1,
            step=1,
            clickable=False,
            minHeight=20,
        )
        self.smoothOption_lay.addWidget(self.repeatBTN)
        self.smoothOption_lay.addWidget(self.depthBTN)
        """
        self.repeatBTN.move(173,1)
        self.depthBTN.move(173,22)
        for btn in [self.repeatBTN, self.depthBTN]:
            btn.resize(30,22)
            btn.show()
        """

        for ind, nm in enumerate(["add", "rmv", "addPerc", "abs", "smooth", "sharpen"]):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.clicked.connect(partial(self.brushFunctions.setInfluenceIndex, ind))
        self.smooth_btn.toggled.connect(self.updateOptionEnable)
        self.sharpen_btn.toggled.connect(self.updateOptionEnable)
        self.updateOptionEnable(True)

        for nm in ["lock", "refresh", "pinSelection"]:
            self.__dict__[nm + "_btn"].setText("")
        self.valueSetter = ValueSetting(self)
        self.valueSetter.setAddMode(False, autoReset=False)
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

    # --------------------------------------------------------------
    # artAttrSkinPaintCtx
    # --------------------------------------------------------------
    def pickMaxInfluence(self):
        ctxArgs = {
            "title": "Select vertex influence",
            #'finalCommandScript ':"python (\"finishTheSelection()\");",
            "toolStart": "SelectVertexMask;",
            #'toolFinish ':"python (\"self.finalCommandScriptPickVtxInfluence()\");",
            "toolCursorType": "question",
            "totalSelectionSets": 1,
            "cumulativeLists": False,
            "expandSelectionList": True,
            "setNoSelectionPrompt": "Select Vertex Influence",
            "setSelectionPrompt": "Never used",
            "setDoneSelectionPrompt": "Never used because setAutoComplete is set",
            "setAutoToggleSelection": True,
            "setSelectionCount": 1,
            "setAutoComplete": True,
        }
        if not cmds.scriptCtx("SelectVertexSkinInfluence", q=True, exists=True):
            ctxSelection = cmds.scriptCtx(name="SelectVertexSkinInfluence", **ctxArgs)
        else:
            cmds.scriptCtx("SelectVertexSkinInfluence", e=True, **ctxArgs)

        import __main__

        __main__.BLRpickVtxInfluence = self.finalCommandScriptPickVtxInfluence
        cmds.scriptCtx(
            "SelectVertexSkinInfluence", e=True, toolFinish='python ("BLRpickVtxInfluence()");'
        )
        cmds.setToolTo("SelectVertexSkinInfluence")

    # --------------------------------------------------------------
    # Pick Vtx Influence
    # --------------------------------------------------------------
    def finalCommandScriptPickVtxInfluence(self):
        theSelection = cmds.ls(sl=True)
        if theSelection:
            vtx = theSelection[0]
            hist = cmds.listHistory(vtx, lv=0, pruneDagObjects=True)
            if hist:
                skinClusters = cmds.ls(hist, type="skinCluster")
                if skinClusters:
                    skinClus = skinClusters[0]
                    values = cmds.skinPercent(skinClus, vtx, query=True, value=True)
                    influences = cmds.skinCluster(skinClus, q=True, influence=True)
                    maxVal, maxInfluence = sorted(zip(values, influences), reverse=True)[0]
                    listCurrentInfluences = [
                        self.joints_tree.topLevelItem(i).text(1)
                        for i in range(self.joints_tree.topLevelItemCount())
                    ]
                    print maxVal, maxInfluence
                    if maxInfluence in listCurrentInfluences:
                        ind = listCurrentInfluences.index(maxInfluence)
                        itemDeformer = self.joints_tree.topLevelItem(ind)
                        self.joints_tree.setCurrentItem(itemDeformer)
                    # theCommand = "selectMode -object;ArtPaintSkinWeightsToolOptions;setSmoothSkinInfluence {0};artSkinRevealSelected artAttrSkinPaintCtx;".format (maxInfluence)
                    # cmds.evalDeferred( partial ( mel.eval ,theCommand))
                    cmds.evalDeferred(
                        partial(mel.eval, "changeSelectMode -hierarchical;setToolTo $gMove;")
                    )

    def refreshBtn(self):
        # self.storeSelection ()
        self.refresh(force=True)
        # self.retrieveSelection ()

    def refresh(self, force=False):
        self.dataOfSkin.getAllData(displayLocator=False)
        self.joints_tree.clear()
        for nm in self.dataOfSkin.driverNames:  # .shortDriverNames :
            jointItem = InfluenceTreeWidgetItem(nm)
            # jointItem =  QtWidgets.QTreeWidgetItem()
            # jointItem.setText (1, nm)

            self.joints_tree.addTopLevelItem(jointItem)


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
        super(InfluenceTreeWidgetItem, self).__init__(["", influence])
        self._influence = influence

        self.setDisplay()

    def setDisplay(self):
        self.setIcon(0, self.colorIcon())
        self.setIcon(1, self.lockIcon())

    def setColor(self, index):
        cmds.setAttr(self._influence + ".objectColor", index)

        theCol = [col / 250.0 for col in self._colors[index]]
        cmds.setAttr(objAsStr + ".overrideColorRGB", *theCol)

        self.setDisplay()

    def color(self):
        return self._colors[cmds.getAttr(self._influence + ".objectColor")]

    def lockIcon(self):
        return Icons.getIcon("lock") if self.isLocked() else Icons.getIcon("lock-gray-unlocked")

    def colorIcon(self):
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtGui.QColor(*self.color()))
        return QtGui.QIcon(pixmap)

    def setVisible(self, visible):
        self.setLocked(not visible)
        self.setHidden(not visible)

    def setLocked(self, locked):
        cmds.setAttr(self._influence + ".lockInfluenceWeights", locked)
        if locked:
            self.setSelected(False)
        self.setDisplay()

    def isLocked(self):
        return cmds.getAttr(self._influence + ".lockInfluenceWeights")

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
