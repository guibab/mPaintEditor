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
import re
from studio.gui.resource import Icons
from mWeightEditor.tools.skinData import DataOfSkin
from mWeightEditor.tools.spinnerSlider import ValueSetting, ButtonWithValue
from tools.brushFunctions import BrushFunctions
from tools.catchEventsUI import CatchEventsWidget


class ValueSettingPE(ValueSetting):
    def doSet(self, theVal):
        self.mainWindow.value = theVal

    def postSet(self):
        if cmds.currentCtx() == "artAttrContext":
            cmds.artAttrCtx("artAttrContext", e=True, value=self.mainWindow.value)


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
    "gaussian": getIcon("circleGauss"),
    "poly": getIcon("circlePoly"),
    "solid": getIcon("circleSolid"),
    "square": getIcon("rect"),
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
    background-color: rgb(100, 100, 100);
    color:white;
    border: none; 
}
QPushButton:hover{  
    background-color: grey; 
    border-style: outset;  
}
QPushButton:pressed {
    background-color: rgb(130, 130, 130);
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
    EVENTCATCHER = None

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

        self.brushFunctions = BrushFunctions(self)

        self.createWindow()
        self.setStyleSheet(styleSheet)
        self.setWindowDisplay()

        # self.addCallBacks ()
        self.refresh()
        if self.EVENTCATCHER == None:
            self.EVENTCATCHER = CatchEventsWidget(connectedWindow=self)

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
        if len(vals) > 4:
            self.changeCommand(vals[4])
            thebtn = self.__dict__[self.commandArray[vals[4]] + "_btn"]
            thebtn.setChecked(True)

    def addCallBacks(self):
        self.refreshSJ = cmds.scriptJob(event=["SelectionChanged", self.refresh])
        """
        #self.listJobEvents =[refreshSJ] 
        sceneUpdateCallback = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeNew, self.deselectAll )  #kSceneUpdate
        self.close_callback = [sceneUpdateCallback]
        self.close_callback.append (  OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeOpen, self.deselectAll )  )
        """

    def deleteCallBacks(self):
        self.brushFunctions.deleteTheJobs()
        # cmds.scriptJob( kill=self.refreshSJ, force=True)
        # for callBck in self.close_callback : OpenMaya.MSceneMessage.removeCallback(callBck)

    commandIndex = -1
    value = 1.0
    commandArray = ["add", "rmv", "addPerc", "abs", "smooth", "sharpen"]

    def storePrevCommandValue(self):
        if self.commandIndex != -1:
            nmPrev = self.commandArray[self.commandIndex]
            cmds.optionVar(floatValue=[nmPrev + "_SkinPaintWin", self.value])
            return nmPrev
        return "-1"

    def getEnabledButton(self):
        for nm in self.commandArray:
            thebtn = self.__dict__[nm + "_btn"]
            if thebtn.isChecked():
                return thebtn
        return None

    def changeCommand(self, newCommand):
        nmPrev = self.storePrevCommandValue()

        nmNew = self.commandArray[newCommand]
        optionVarName = nmNew + "_SkinPaintWin"
        newCommandValue = (
            cmds.optionVar(q=optionVarName) if cmds.optionVar(exists=optionVarName) else 1.0
        )

        # print nmPrev, " = ",self.value, "  | ", nmNew ," = ", newCommandValue
        self.commandIndex = newCommand
        self.setBrushValue(newCommandValue)

    def closeEvent(self, event):
        self.deleteCallBacks()
        pos = self.pos()
        size = self.size()
        cmds.optionVar(clearArray="SkinPaintWindow")
        for el in pos.x(), pos.y(), size.width(), size.height():
            cmds.optionVar(intValueAppend=("SkinPaintWindow", el))
        cmds.optionVar(intValueAppend=("SkinPaintWindow", self.commandIndex))
        self.storePrevCommandValue()
        # self.headerView.deleteLater()
        if self.EVENTCATCHER != None:
            self.EVENTCATCHER.close()
        super(SkinPaintWin, self).closeEvent(event)

    def setBrushValue(self, val):
        self.value = val
        # print self.value
        self.valueSetter.theProgress.applyVal(val)
        self.valueSetter.setVal(val * 100)

    def addButtonsDirectSet(self, lstBtns):
        theCarryWidget = QtWidgets.QWidget()

        carryWidgLayoutlayout = QtWidgets.QHBoxLayout(theCarryWidget)
        carryWidgLayoutlayout.setContentsMargins(0, 0, 0, 0)
        carryWidgLayoutlayout.setSpacing(0)

        for theVal in lstBtns:
            nm = "{0:.0f}".format(theVal) if theVal == int(theVal) else "{0:.2f}".format(theVal)
            if theVal == 0.25:
                nm = "1/4"
            if theVal == 0.5:
                nm = "1/2"
            newBtn = QtWidgets.QPushButton(nm)
            newBtn.clicked.connect(partial(self.setBrushValue, theVal / 100.0))
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

    def transferValues(self):
        self.brushFunctions.setPaintMode(self.commandIndex)
        cmds.artAttrCtx("artAttrContext", e=True, value=self.value)
        self.brushFunctions.setSmoothOptions(self.repeatBTN.precision, self.depthBTN.precision)
        self.influenceSelChanged()
        self.brushFunctions.togglePostSetting(self.postSet_cb.isChecked())

    def changeOfValue(self):
        if cmds.currentCtx() == "artAttrContext":
            currentVal = cmds.artAttrCtx("artAttrContext", q=True, value=True)
            self.setBrushValue(currentVal)

    def enterPaint(self):
        self.show()
        self.brushFunctions.setColorsOnJoints()
        if self.dataOfSkin.theSkinCluster:
            self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
            if not self.brushFunctions.bsd:
                self.brushFunctions.doAddColorNode(
                    self.dataOfSkin.deformedShape, self.dataOfSkin.theSkinCluster
                )
            self.brushFunctions.enterPaint()
            self.transferValues()

    def updateOptionEnable(self, toggleValue):
        setOn = self.smooth_btn.isChecked() or self.sharpen_btn.isChecked()
        for btn in [self.repeatBTN, self.depthBTN]:
            btn.setEnabled(setOn)

    def smoothValueUpdate(self, val, nm):
        print nm, val

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
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)
        self.postSet_cb.toggled.connect(self.brushFunctions.togglePostSetting)
        self.searchInfluences_le.textChanged.connect(self.filterInfluences)

        self.repeatBTN = ButtonWithValue(
            self.buttonWidg,
            usePow=False,
            name="iter",
            minimumValue=1,
            defaultValue=1,
            step=1,
            clickable=False,
            minHeight=20,
            addSpace=False,
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
            addSpace=False,
        )
        self.smoothOption_lay.addWidget(self.repeatBTN)
        self.smoothOption_lay.addWidget(self.depthBTN)

        self.repeatBTN._valueChanged.connect(partial(self.smoothValueUpdate, "smoothRepeat"))
        self.depthBTN._valueChanged.connect(partial(self.smoothValueUpdate, "smoothDepth"))

        self.uiInfluenceTREE.itemSelectionChanged.connect(self.influenceSelChanged)

        for ind, nm in enumerate(self.commandArray):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.clicked.connect(partial(self.brushFunctions.setPaintMode, ind))
            thebtn.clicked.connect(partial(self.changeCommand, ind))
        # "gaussian", "poly", "solid" and "square"
        for ind, nm in enumerate(["gaussian", "poly", "solid", "square"]):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.setText("")
            thebtn.clicked.connect(partial(self.brushFunctions.setStampProfile, nm))
            # "gaussian", "poly", "solid" and "square"

            thebtn.setIcon(_icons[nm])
        self.smooth_btn.toggled.connect(self.updateOptionEnable)
        self.sharpen_btn.toggled.connect(self.updateOptionEnable)
        self.updateOptionEnable(True)

        for nm in ["lock", "refresh", "pinSelection"]:
            self.__dict__[nm + "_btn"].setText("")
        self.valueSetter = ValueSettingPE(self, precision=2)
        self.valueSetter.setAddMode(False, autoReset=False)
        Hlayout = QtWidgets.QHBoxLayout(self)
        Hlayout.setContentsMargins(0, 0, 0, 0)
        Hlayout.setSpacing(0)
        Hlayout.addWidget(self.valueSetter)
        self.valueSetter.setMaximumSize(self.maxWidthCentralWidget, 18)

        self.widgetAbs = self.addButtonsDirectSet([0, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 75, 100])

        Hlayout2 = QtWidgets.QHBoxLayout(self)
        Hlayout2.setContentsMargins(0, 0, 0, 0)
        Hlayout2.setSpacing(0)
        Hlayout2.addWidget(self.widgetAbs)

        dialogLayout.insertSpacing(1, 10)
        dialogLayout.insertLayout(1, Hlayout)
        dialogLayout.insertLayout(1, Hlayout2)
        dialogLayout.insertSpacing(1, 10)

    # --------------------------------------------------------------
    # artAttrSkinPaintCtx
    # --------------------------------------------------------------
    def pickMaxInfluence(self):
        import __main__

        __main__.BLURpickVtxInfluence = self.finalCommandScriptPickVtxInfluence
        __main__.BLURstartPickVtx = self.startpickVtx

        currContext = cmds.currentCtx()
        self.inPainting = currContext == "artAttrContext"

        # cmds.select (cl=True)

        ctxArgs = {
            "title": "Select vertex influence",
            #'finalCommandScript ':"python (\"BLURfinishSkinPaint()\");",
            "toolStart": 'python ("BLURstartPickVtx()");',
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

        cmds.scriptCtx(
            "SelectVertexSkinInfluence", e=True, toolFinish='python ("BLURpickVtxInfluence()");'
        )
        cmds.setToolTo("SelectVertexSkinInfluence")

    # --------------------------------------------------------------
    # Pick Vtx Influence
    # --------------------------------------------------------------
    def startpickVtx(self):
        self.softOn = cmds.softSelect(q=True, softSelectEnabled=True)
        if self.softOn:
            cmds.softSelect(e=True, softSelectEnabled=False)
        self.currentVertsSel = [el for el in cmds.ls(sl=True) if ".vtx[" in el]
        if self.currentVertsSel:
            cmds.select(self.currentVertsSel, d=True)

        cmds.SelectVertexMask()

    def finalCommandScriptPickVtxInfluence(self):
        theVtxSelection = [el for el in cmds.ls(sl=True, fl=True) if ".vtx[" in el]
        if theVtxSelection:
            vtx = theVtxSelection[0]
            hist = cmds.listHistory(vtx, lv=0, pruneDagObjects=True)
            if hist:
                skinClusters = cmds.ls(hist, type="skinCluster")
                if skinClusters:
                    skinClus = skinClusters[0]
                    values = cmds.skinPercent(skinClus, vtx, query=True, value=True)
                    influences = cmds.skinCluster(skinClus, q=True, influence=True)
                    maxVal, maxInfluence = sorted(zip(values, influences), reverse=True)[0]
                    listCurrentInfluences = [
                        self.uiInfluenceTREE.topLevelItem(i).text(1)
                        for i in range(self.uiInfluenceTREE.topLevelItemCount())
                    ]
                    print maxVal, maxInfluence
                    if maxInfluence in listCurrentInfluences:
                        ind = listCurrentInfluences.index(maxInfluence)
                        itemDeformer = self.uiInfluenceTREE.topLevelItem(ind)
                        self.uiInfluenceTREE.setCurrentItem(itemDeformer)
                    # theCommand = "selectMode -object;ArtPaintSkinWeightsToolOptions;setSmoothSkinInfluence {0};artSkinRevealSelected artAttrSkinPaintCtx;".format (maxInfluence)
                    # cmds.evalDeferred( partial ( mel.eval ,theCommand))
                    if self.inPainting:
                        cmds.evalDeferred(
                            partial(mel.eval, "changeSelectMode -hierarchical;ArtPaintAttrTool;")
                        )
                    else:
                        cmds.evalDeferred(
                            partial(mel.eval, "changeSelectMode -hierarchical;setToolTo $gMove;")
                        )
        if self.softOn:
            cmds.softSelect(e=True, softSelectEnabled=True)
        if self.currentVertsSel:
            cmds.select(self.currentVertsSel, add=True)

    def selectedInfluences(self):
        return [item.influence() for item in self.uiInfluenceTREE.selectedItems()]

    def influenceSelChanged(self):
        influences = self.selectedInfluences()
        if len(influences) > 0:
            print influences
            toSel = influences[0]
            ind = self.dataOfSkin.driverNames.index(influences[0])
            self.brushFunctions.setInfluenceIndex(ind)
        else:
            print "clear influence"

    def filterInfluences(self, newText):
        for nm, it in self.uiInfluenceTREE.dicWidgName.iteritems():
            it.setHidden(re.search(newText, nm, re.IGNORECASE) == None)

    def refreshBtn(self):
        # self.storeSelection ()
        self.refresh(force=True)
        # self.retrieveSelection ()

    def refresh(self, force=False):
        # print "refresh CALLED"
        resultData = self.dataOfSkin.getAllData(displayLocator=False)
        if resultData:
            self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
            self.uiInfluenceTREE.clear()
            self.uiInfluenceTREE.dicWidgName = {}

            for nm in self.dataOfSkin.driverNames:  # .shortDriverNames :
                jointItem = InfluenceTreeWidgetItem(nm)
                # jointItem =  QtWidgets.QTreeWidgetItem()
                # jointItem.setText (1, nm)
                self.uiInfluenceTREE.addTopLevelItem(jointItem)
                self.uiInfluenceTREE.dicWidgName[nm] = jointItem


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
