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
import numpy as np
from studio.gui.resource import Icons
from mWeightEditor.tools.skinData import DataOfSkin
from mWeightEditor.tools.spinnerSlider import ValueSetting, ButtonWithValue, VerticalBtn
from mWeightEditor.tools.utils import GlobalContext, toggleBlockSignals, deleteTheJobs
from tools.brushFunctions import BrushFunctions
from tools.catchEventsUI import CatchEventsWidget, rootWindow

thePaintContextName = "BlurSkinartAttrContext"


def deleteNodesOnSave():
    nodeToDelete = cmds.ls(type="blurSkinDisplay")
    if nodeToDelete:
        cmds.delete(nodeToDelete)


class ValueSettingPE(ValueSetting):
    def doSet(self, theVal):
        self.mainWindow.value = theVal

    def postSet(self):
        if cmds.currentCtx() == thePaintContextName:
            cmds.artAttrCtx(thePaintContextName, e=True, value=self.mainWindow.value)


def getIcon(iconNm):
    fileVar = os.path.realpath(__file__)
    uiFolder, filename = os.path.split(fileVar)
    iconPth = os.path.join(uiFolder, "img", iconNm + ".png")
    return QtGui.QIcon(iconPth)


_icons = {
    "lock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\lock-48"),
    "unlock": Icons.getIcon(r"icons8\Android_L\PNG\48\Very_Basic\unlock-48"),
    "del": Icons.getIcon(r"icons8\office\PNG\16\Editing\delete_sign-16"),
    "pinOn": getIcon("pinOn"),
    "pinOff": getIcon("pinOff"),
    "gaussian": getIcon("circleGauss"),
    "poly": getIcon("circlePoly"),
    "solid": getIcon("circleSolid"),
    "square": getIcon("rect"),
    "refresh": Icons.getIcon("refresh"),
    "eye": Icons.getIcon("eye"),
    "eye-half": Icons.getIcon("eye-half"),
    "plus": Icons.getIcon("plus-button"),
    "minus": Icons.getIcon("minus-button"),
    "removeUnused": Icons.getIcon("arrow-transition-270--red"),
    "randomColor": Icons.getIcon("color-swatch"),
}

INFLUENCE_COLORS = [
    (0, 0, 224),
    (224, 224, 0),
    (224, 0, 224),
    (96, 224, 192),
    (224, 128, 0),
    (192, 0, 192),
    (0, 192, 64),
    (192, 160, 0),
    (160, 0, 32),
    (128, 192, 224),
    (224, 192, 128),
    (64, 32, 160),
    (192, 160, 32),
    (224, 32, 160),
]

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
QWidget:disabled {
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
QGroupBox{
    background-color: #aba8a6;
    color : black;
    border :0 px; 
}
QGroupBox::checked{
    background-color: #aba8a6;
    color : black;
    border : 1px solid rgb(120, 120, 120); 
}

QGroupBox::indicator {
    width: 0px;
    height: 0px;
}
QComboBox{
    border : 1px solid rgb(120, 120, 120); 
}
"""


class HelpWidget(QtWidgets.QTreeWidget):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        super(HelpWidget, self).__init__(rootWindow())
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet(styleSheet)
        self.setColumnCount(2)
        self.header().hide()
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        # self.setStyleSheet("margin-left: 0px; border-radius: 25px; background: yellow; color: black; border: 1px solid black;")
        nb = self.populate() - 1
        self.setColumnWidth(0, 150)
        self.resizeColumnToContents(1)
        self.resize(250, nb * 15)

    def close(self):
        self.mainWindow.setEnabled(True)
        super(HelpWidget, self).close()

    def populate(self):
        lstShortCuts = [
            ("Smooth ", "SHIFT"),
            ("Remove ", "CTRL"),
            ("markingMenu ", "0"),
            ("pick Vertex ", "ALT + D"),
            ("pick influence", "D"),
            ("Toggle Solo Mode", "ALT + S"),
            ("Toggle Wireframe", "ALT + W"),
            ("Toggle Xray", "ALT + X"),
            ("Undo", "CTRL + Z"),
            ("update Value", "N"),
        ]
        for nm1, nm2 in lstShortCuts:
            helpItem = QtWidgets.QTreeWidgetItem()
            helpItem.setText(0, nm1)
            helpItem.setText(1, nm2)
            self.addTopLevelItem(helpItem)
        return len(lstShortCuts)

    def mousePressEvent(self, *args):
        self.close()


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
        if not cmds.artAttrCtx(thePaintContextName, query=True, ex=True):
            cmds.artAttrCtx(name=thePaintContextName)

        blurdev.gui.loadUi(__file__, self)

        self.useShortestNames = (
            cmds.optionVar(q="useShortestNames")
            if cmds.optionVar(exists="useShortestNames")
            else True
        )
        self.dataOfSkin = DataOfSkin(useShortestNames=self.useShortestNames)

        self.brushFunctions = BrushFunctions(self, thePaintContextName=thePaintContextName)
        self.createWindow()
        self.setStyleSheet(styleSheet)
        self.setWindowDisplay()

        self.addCallBacks()
        self.buildRCMenu()
        self.createColorPicker()
        self.uiInfluenceTREE.clear()
        self.refresh()

        self.theHelpWidget = HelpWidget(self)

        if self.EVENTCATCHER == None:
            self.EVENTCATCHER = CatchEventsWidget(
                connectedWindow=self, thePaintContextName=thePaintContextName
            )

    def colorSelected(self, color):
        values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
        item = self.colorDialog.item
        nm = item._influence
        ind = item._index
        # print ind,nm, values
        self.brushFunctions.setColor(ind, values)
        item.setColor(values)
        # cmds.displayRGBColor ("userDefined{0}".format (theUserDefinedIndex),*values)

    def createColorPicker(self):
        self.colorDialog = QtWidgets.QColorDialog()
        # self.colorDialog .colorSelected.connect ( self.colorSelected )
        self.colorDialog.currentColorChanged.connect(self.colorSelected)

        self.colorDialog.setWindowFlags(QtCore.Qt.Tool)
        self.colorDialog.setWindowTitle("pick color")
        self.colorDialog.setWindowModality(QtCore.Qt.ApplicationModal)

    def showHelp(self):
        self.theHelpWidget.move(self.pos() + QtCore.QPoint(0.5 * (self.width() - 250 + 10), 40))
        self.setEnabled(False)
        self.theHelpWidget.show()

    def buildRCMenu(self):
        self.mainPopMenu = QtWidgets.QMenu(self)
        self.subMenuSoloColor = self.mainPopMenu.addMenu("solo color")
        self.soloColorIndex = (
            cmds.optionVar(q="soloColor_SkinPaintWin")
            if cmds.optionVar(exists="soloColor_SkinPaintWin")
            else 0
        )
        for ind, colType in enumerate(["white", "lava", "influence"]):
            theFn = partial(self.updateSoloColor, ind)
            act = self.subMenuSoloColor.addAction(colType, theFn)
            act.setCheckable(True)
            act.setChecked(self.soloColorIndex == ind)
        self.mainPopMenu.addAction("help", self.showHelp)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMainMenu)

        # ------------------------------
        self.popMenu = QtWidgets.QMenu(self.uiInfluenceTREE)
        """
        chbox = QtWidgets.QCheckBox("auto Prune", self.popMenu)
        chbox.setChecked (self.autoPrune)
        chbox.toggled.connect (self.autoPruneChecked)
        checkableAction = QtWidgets.QWidgetAction(self.popMenu)
        checkableAction.setDefaultWidget(chbox)
        self.popMenu.addAction(checkableAction)
        """
        selectItems = self.popMenu.addAction("select node", partial(self.applyLock, "selJoints"))
        self.popMenu.addAction(selectItems)

        self.popMenu.addSeparator()
        lockSel = self.popMenu.addAction("lock Sel", partial(self.applyLock, "lockSel"))
        self.popMenu.addAction(lockSel)
        allButSel = self.popMenu.addAction(
            "lock all but Sel", partial(self.applyLock, "lockAllButSel")
        )
        self.popMenu.addAction(allButSel)
        unLockSel = self.popMenu.addAction("unlock Sel", partial(self.applyLock, "unlockSel"))
        self.popMenu.addAction(unLockSel)
        unLockAllButSel = self.popMenu.addAction(
            "unlock all but Sel", partial(self.applyLock, "unlockAllButSel")
        )
        self.popMenu.addAction(unLockAllButSel)

        self.popMenu.addSeparator()
        unLockSel = self.popMenu.addAction("clear locks", partial(self.applyLock, "clearLocks"))
        self.popMenu.addAction(unLockSel)

        self.popMenu.addSeparator()
        self.showZeroDeformers = (
            cmds.optionVar(q="showZeroDeformers")
            if cmds.optionVar(exists="showZeroDeformers")
            else False
        )
        chbox = QtWidgets.QCheckBox("show Zero Deformers", self.popMenu)
        chbox.setChecked(self.showZeroDeformers)
        chbox.toggled.connect(self.showZeroDefmChecked)
        checkableAction = QtWidgets.QWidgetAction(self.popMenu)
        checkableAction.setDefaultWidget(chbox)
        self.popMenu.addAction(checkableAction)

        self.uiInfluenceTREE.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.uiInfluenceTREE.customContextMenuRequested.connect(self.showMenu)

    def showMenu(self, pos):
        self.popMenu.exec_(self.uiInfluenceTREE.mapToGlobal(pos))

    def showMainMenu(self, pos):
        self.mainPopMenu.exec_(self.mapToGlobal(pos))

    def updateSoloColor(self, ind):
        self.soloColor_cb.setCurrentIndex(ind)

    def comboSoloColorChanged(self, ind):
        self.soloColorIndex = ind
        self.brushFunctions.setBSDAttr("soloColType", self.soloColorIndex)
        cmds.optionVar(intValue=["soloColor_SkinPaintWin", ind])
        for i in range(3):
            self.subMenuSoloColor.actions()[i].setChecked(i == ind)

    def showZeroDefmChecked(self, checked):
        cmds.optionVar(intValue=["showZeroDeformers", checked])
        self.showZeroDeformers = checked
        self.popMenu.close()

        allItems = [
            self.uiInfluenceTREE.topLevelItem(ind)
            for ind in range(self.uiInfluenceTREE.topLevelItemCount())
        ]
        for item in allItems:
            if item.isZeroDfm:
                item.setHidden(not self.showZeroDeformers)

    def setWindowDisplay(self):
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.Tool)
        self.setWindowTitle("Paint Editor")
        self.refreshPosition()
        self.show()

    def refreshPosition(self):
        if cmds.optionVar(ex="SkinPaintWindow"):
            vals = cmds.optionVar(q="SkinPaintWindow")
            if vals:
                self.move(vals[0], vals[1])
                self.resize(vals[2], vals[3])
            if len(vals) > 4:
                self.changeCommand(vals[4])
                thebtn = self.__dict__[self.commandArray[vals[4]] + "_btn"]
                thebtn.setChecked(True)

    def addCallBacks(self):
        self.refreshSJ = cmds.scriptJob(event=["SelectionChanged", self.refreshCallBack])
        # create callBack to end
        import __main__

        if "PEW_preSaveCallback" not in __main__.__dict__:
            __main__.PEW_preSaveCallback = OpenMaya.MSceneMessage.addCallback(
                OpenMaya.MSceneMessage.kBeforeSave, deleteNodesOnSave
            )
        """
        #self.listJobEvents =[refreshSJ] 
        sceneUpdateCallback = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeNew, self.deselectAll )  #kSceneUpdate
        self.close_callback = [sceneUpdateCallback]
        self.close_callback.append (  OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeOpen, self.deselectAll )  )
        """

    def deleteCallBacks(self):
        deleteTheJobs("BrushFunctions.callAfterPaint")
        deleteTheJobs("SkinPaintWin.refreshCallBack")
        # cmds.scriptJob( kill=self.refreshSJ, force=True)
        # for callBck in self.close_callback : OpenMaya.MSceneMessage.removeCallback(callBck)

    commandIndex = -1
    value = 1.0
    commandArray = ["add", "rmv", "addPerc", "abs", "smooth", "sharpen", "locks"]

    def storePrevCommandValue(self):
        # print "call prevCommand"
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
        allItems = [
            self.uiInfluenceTREE.topLevelItem(ind)
            for ind in range(self.uiInfluenceTREE.topLevelItemCount())
        ]
        if val:
            self.lock_btn.setIcon(_icons["lock"])
        else:
            self.lock_btn.setIcon(_icons["unlock"])
        self.unLock = not val

    def changePin(self, val):
        selectedItems = self.uiInfluenceTREE.selectedItems()
        allItems = [
            self.uiInfluenceTREE.topLevelItem(ind)
            for ind in range(self.uiInfluenceTREE.topLevelItemCount())
        ]
        if val:
            self.pinSelection_btn.setIcon(_icons["pinOn"])
            for item in allItems:
                toHide = item not in selectedItems
                toHide |= not self.showZeroDeformers and item.isZeroDfm
                item.setHidden(toHide)
        else:
            for item in allItems:
                toHide = not self.showZeroDeformers and item.isZeroDfm
                item.setHidden(toHide)
            self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.unPin = not val

    def showHideLocks(self, val):
        allItems = [
            self.uiInfluenceTREE.topLevelItem(ind)
            for ind in range(self.uiInfluenceTREE.topLevelItemCount())
        ]
        if val:
            self.showLocks_btn.setIcon(_icons["eye"])
            for item in allItems:
                item.setHidden(False)
        else:
            for item in allItems:
                item.setHidden(item.isLocked())
            self.showLocks_btn.setIcon(_icons["eye-half"])

    def changeOfValue(self):
        if cmds.currentCtx() == thePaintContextName:
            currentVal = cmds.artAttrCtx(thePaintContextName, q=True, value=True)
            self.setBrushValue(currentVal)

    def enterPaint(self):
        if self.dataOfSkin.theSkinCluster:
            self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
            if not self.brushFunctions.bsd:
                self.brushFunctions.doAddColorNode(
                    self.dataOfSkin.deformedShape, self.dataOfSkin.theSkinCluster
                )
            self.transferValues()
            self.brushFunctions.enterPaint()

    def transferValues(self):
        self.brushFunctions.setPaintMode(self.commandIndex)
        cmds.artAttrCtx(thePaintContextName, e=True, value=self.value)
        self.brushFunctions.setSmoothOptions(self.repeatBTN.precision, self.depthBTN.precision)
        self.influenceSelChanged()
        self.brushFunctions.togglePostSetting(self.postSet_cb.isChecked())
        self.brushFunctions.setBSDAttr("soloColType", self.soloColorIndex)

        # self.changeMultiSolo(self.multi_rb.isChecked ())
        # self.brushFunctions.setColor (self.postSet_cb.isChecked())

    def updateOptionEnable(self, toggleValue):
        setOn = self.smooth_btn.isChecked() or self.sharpen_btn.isChecked()
        for btn in [self.repeatBTN, self.depthBTN]:
            btn.setEnabled(setOn)

    def changeMultiSolo(self, val):
        res = cmds.polyColorSet(query=True, allColorSets=True) or []
        if val == -1 and "noColorsSet" in res:
            cmds.polyColorSet(currentColorSet=True, colorSet="noColorsSet")
        elif "multiColorsSet" in res and "soloColorsSet" in res:
            if val:
                cmds.polyColorSet(currentColorSet=True, colorSet="multiColorsSet")
            else:
                cmds.polyColorSet(currentColorSet=True, colorSet="soloColorsSet")
        self.brushFunctions.setBSDAttr("colorType", int(not val))

    def addInfluences(self):
        cmds.confirmDialog(m="addInfluences")

    def removeInfluences(self):
        cmds.confirmDialog(m="removeInfluences")

    def removeUnusedInfluences(self):
        cmds.confirmDialog(m="removeUnusedInfluences")

    def randomColors(self):
        cmds.confirmDialog(m="randomColors")

    def createWindow(self):
        self.unLock = True
        self.unPin = True
        dialogLayout = self.layout()

        self.lock_btn.setIcon(_icons["unlock"])
        self.refresh_btn.setIcon(_icons["refresh"])
        self.lock_btn.toggled.connect(self.changeLock)
        self.refresh_btn.clicked.connect(self.refreshBtn)
        self.enterPaint_btn.clicked.connect(self.enterPaint)

        self.showLocks_btn.setIcon(_icons["eye"])
        self.showLocks_btn.toggled.connect(self.showHideLocks)
        self.showLocks_btn.setText("")

        self.delete_btn.setIcon(_icons["del"])
        self.delete_btn.setText("")
        # self.delete_btn.clicked.connect (self.paintEnd )
        self.delete_btn.clicked.connect(lambda: mel.eval("SelectToolOptionsMarkingMenu"))
        self.delete_btn.clicked.connect(self.brushFunctions.deleteNode)

        self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.pinSelection_btn.toggled.connect(self.changePin)
        self.pickVertex_btn.clicked.connect(self.pickMaxInfluence)
        self.pickInfluence_btn.clicked.connect(self.pickInfluence)
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)

        self.postSet_cb.toggled.connect(self.autoExpand_cb.setEnabled)

        self.postSet_cb.toggled.connect(self.brushFunctions.togglePostSetting)
        self.searchInfluences_le.textChanged.connect(self.filterInfluences)
        self.multi_rb.toggled.connect(self.changeMultiSolo)

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

        self.autoExpand_cb.toggled.connect(partial(self.brushFunctions.setBSDAttr, "autoExpand"))
        self.repeatBTN._valueChanged.connect(
            partial(self.brushFunctions.setBSDAttr, "smoothRepeat")
        )
        self.depthBTN._valueChanged.connect(partial(self.brushFunctions.setBSDAttr, "smoothDepth"))
        self.minColor_sb.valueChanged.connect(partial(self.brushFunctions.setBSDAttr, "minColor"))
        self.maxColor_sb.valueChanged.connect(partial(self.brushFunctions.setBSDAttr, "maxColor"))

        self.soloColor_cb.currentIndexChanged.connect(self.comboSoloColorChanged)
        # self.uiInfluenceTREE.itemSelectionChanged.connect(self.influenceSelChanged)
        self.uiInfluenceTREE.itemDoubleClicked.connect(self.influenceDoubleClicked)
        self.uiInfluenceTREE.itemClicked.connect(self.influenceClicked)

        self.locks_btn = VerticalBtn("locks", self.lockPlacement_btn.parent())
        self.lockPlacement_btn.hide()
        self.locks_btn.move(self.lockPlacement_btn.pos())
        self.locks_btn.resize(self.lockPlacement_btn.size())
        self.locks_btn.setCheckable(True)
        self.locks_btn.setAutoExclusive(True)

        self.option_cb.toggled.connect(self.option_GB.setChecked)
        self.option_cb.toggled.connect(self.option_GB.setVisible)
        self.option_GB.setVisible(False)

        self.addInfluences_btn.clicked.connect(self.addInfluences)
        self.removeInfluences_btn.clicked.connect(self.removeInfluences)
        self.removeUnusedInfluences_btn.clicked.connect(self.removeUnusedInfluences)
        self.randomColors_btn.clicked.connect(self.randomColors)
        for btn, icon in [
            ("addInfluences", "plus"),
            ("removeInfluences", "minus"),
            ("removeUnusedInfluences", "removeUnused"),
            ("randomColors", "randomColor"),
        ]:
            theBtn = self.__dict__[btn + "_btn"]
            theBtn.setText("")
            theBtn.setIcon(_icons[icon])
        for ind, nm in enumerate(self.commandArray):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.clicked.connect(partial(self.brushFunctions.setPaintMode, ind))
            thebtn.clicked.connect(partial(self.changeCommand, ind))
        # "gaussian", "poly", "solid" and "square"
        if cmds.artAttrCtx(thePaintContextName, query=True, ex=True):
            stampProfile = cmds.artAttrCtx(thePaintContextName, query=True, stampProfile=True)
            self.__dict__[stampProfile + "_btn"].setChecked(True)
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
        for btnName in ["pickVertex_btn", "pickInfluence_btn"]:
            self.__dict__[btnName].setEnabled(False)
        self.valueSetter = ValueSettingPE(self, precision=2)
        self.valueSetter.setAddMode(False, autoReset=False)
        Hlayout = QtWidgets.QHBoxLayout(self)
        Hlayout.setContentsMargins(0, 0, 0, 0)
        Hlayout.setSpacing(0)
        Hlayout.addWidget(self.valueSetter)
        self.valueSetter.setMaximumSize(self.maxWidthCentralWidget, 18)

        self.widgetAbs = self.addButtonsDirectSet([0.25, 0.5, 1, 2, 5, 10, 25, 50, 75, 100])

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
        self.pickInfluence(vertexPicking=True)

    def pickInfluence(self, vertexPicking=False):
        with GlobalContext(message="prepareToGetHighestInfluence", doPrint=True):
            if vertexPicking:
                self.prepareToGetHighestInfluence()
        self.EVENTCATCHER.createDisplayLabel(vertexPicking=vertexPicking)

    def pickMaxInfluenceOLD(self):
        import __main__

        __main__.BLURpickVtxInfluence = self.finalCommandScriptPickVtxInfluence
        __main__.BLURstartPickVtx = self.startpickVtx

        currContext = cmds.currentCtx()
        self.inPainting = currContext == thePaintContextName

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

    def influenceDoubleClicked(self, item, column):
        # print item.text(1), column
        txt = item.text(1)
        if cmds.objExists(txt):
            if column == 1:
                cmds.select(txt)
            elif column == 0:
                pos = QtGui.QCursor().pos() - QtCore.QPoint(355, 100)
                self.colorDialog.item = item
                with toggleBlockSignals([self.colorDialog]):
                    self.colorDialog.setCurrentColor(QtGui.QColor(*item.color()))
                self.colorDialog.move(pos)
                self.colorDialog.show()
                """
                theColor = [el/255. for el in item.color ()]
                cmds.colorEditor(mini=True, position=[pos.x(), pos.y()], rgbValue = theColor)
                if cmds.colorEditor(query=True, result=True):
                    values = cmds.colorEditor(query=True, rgb=True)
                    nm = item._influence
                    ind = item._index
                    #print ind,nm, values
                    self.brushFunctions.setColor (ind, values)
                    item.setColor (values)
                    #cmds.displayRGBColor ("userDefined{0}".format (theUserDefinedIndex),*values)
                """

    def influenceClicked(self, item, column):
        text = item.text(1)
        if text in self.dataOfSkin.driverNames:
            ind = self.dataOfSkin.driverNames.index(text)
            # ind = item._index
            self.brushFunctions.setInfluenceIndex(ind)

    def applyLock(self, typeOfLock):
        # ["lockSel","unlockSel","lockAllButSel","unlockAllButSel","clearLocks" ]
        autoHide = not self.showLocks_btn.isChecked()
        selectedItems = self.uiInfluenceTREE.selectedItems()
        allItems = [
            self.uiInfluenceTREE.topLevelItem(ind)
            for ind in range(self.uiInfluenceTREE.topLevelItemCount())
        ]
        if typeOfLock == "selJoints":
            toSel = cmds.ls([item.text(1) for item in selectedItems])
            if toSel:
                cmds.select(toSel)
            else:
                cmds.select(clear=True)
        if typeOfLock == "clearLocks":
            for item in allItems:
                item.setLocked(False, autoHide=autoHide)
        elif typeOfLock == "lockSel":
            for item in selectedItems:
                item.setLocked(True, autoHide=autoHide)
        elif typeOfLock == "unlockSel":
            for item in selectedItems:
                item.setLocked(False, autoHide=autoHide)
        elif typeOfLock == "lockAllButSel":
            for item in allItems:
                item.setLocked(item not in selectedItems, autoHide=autoHide)
        elif typeOfLock == "unlockAllButSel":
            for item in allItems:
                item.setLocked(item in selectedItems, autoHide=autoHide)
        if typeOfLock in ["clearLocks", "lockSel", "unlockSel", "lockAllButSel", "unlockAllButSel"]:
            self.brushFunctions.setBSDAttr("getLockWeights", True)

    def influenceSelChanged(self):
        influences = self.selectedInfluences()
        if len(influences) > 0:
            # print influences
            toSel = influences[0]
            ind = self.dataOfSkin.driverNames.index(influences[0])
            self.brushFunctions.setInfluenceIndex(ind)
        else:
            inflInd = self.brushFunctions.getCurrentInfluence()
            if inflInd != -1:
                with toggleBlockSignals([self.uiInfluenceTREE]):
                    self.uiInfluenceTREE.setCurrentItem(self.uiInfluenceTREE.topLevelItem(inflInd))
        #    print "clear influence"

    def filterInfluences(self, newText):
        self.pinSelection_btn.setChecked(False)
        if newText:
            newTexts = [el for el in newText.split(" ") if el]
            for nm, it in self.uiInfluenceTREE.dicWidgName.iteritems():
                foundText = False
                for txt in newTexts:
                    foundText = re.search(txt, nm, re.IGNORECASE) != None
                    if foundText:
                        break
                it.setHidden(not foundText)
        else:
            for nm, item in self.uiInfluenceTREE.dicWidgName.iteritems():
                item.setHidden(not self.showZeroDeformers and item.isZeroDfm)

    def refreshBtn(self):
        self.refresh(force=True)

    def prepareToGetHighestInfluence(self):
        self.highestInfluence = -1
        self.dataOfSkin.rawSkinValues = self.dataOfSkin.exposeSkinData(
            self.dataOfSkin.theSkinCluster
        )
        self.dataOfSkin.getZeroColumns()

    def getHighestInfluence(self, vtxIndex):
        self.highestInfluence = np.argmax(self.dataOfSkin.raw2dArray[vtxIndex])
        return self.dataOfSkin.driverNames[self.highestInfluence]

    def selectPickedInfluence(self):
        if self.highestInfluence != -1:
            self.uiInfluenceTREE.setCurrentItem(
                self.uiInfluenceTREE.topLevelItem(self.highestInfluence)
            )
            self.brushFunctions.setInfluenceIndex(int(self.highestInfluence))

    def refreshCallBack(self):
        currContext = cmds.currentCtx()
        if (
            not self.lock_btn.isChecked() and currContext != thePaintContextName
        ):  # dont refresh for paint
            self.refresh()

    def refresh(self, force=False):
        # print "refresh CALLED"
        with GlobalContext(message="paintEditor getAllData", doPrint=False):
            resultData = self.dataOfSkin.getAllData(
                displayLocator=False, getskinWeights=True, force=force
            )
        if resultData:
            # print "- refreshing -"
            self.brushFunctions.setColorsOnJoints()
            self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
            self.uiInfluenceTREE.clear()
            self.uiInfluenceTREE.dicWidgName = {}

            isPaintable = self.dataOfSkin.shapePath.apiType() == OpenMaya.MFn.kMesh
            for uiObj in [
                "options_widget",
                "buttonWidg",
                "widgetAbs",
                "valueSetter",
                "widget_paintBtns",
                "option_GB",
            ]:
                self.__dict__[uiObj].setEnabled(isPaintable)
            for ind, nm in enumerate(self.dataOfSkin.driverNames):  # .shortDriverNames :
                jointItem = InfluenceTreeWidgetItem(nm, ind)
                # jointItem =  QtWidgets.QTreeWidgetItem()
                # jointItem.setText (1, nm)
                self.uiInfluenceTREE.addTopLevelItem(jointItem)
                self.uiInfluenceTREE.dicWidgName[nm] = jointItem

                jointItem.isZeroDfm = ind in self.dataOfSkin.hideColumnIndices
                jointItem.setHidden(not self.showZeroDeformers and jointItem.isZeroDfm)

    def paintEnd(self):
        self.EVENTCATCHER.fermer()  # removeFilters ()
        for btnName in ["pickVertex_btn", "pickInfluence_btn"]:
            self.__dict__[btnName].setEnabled(False)
        self.setStyleSheet(styleSheet)
        self.changeMultiSolo(-1)
        self.dataOfSkin.getConnectedBlurskinDisplay(disconnectWeightList=True)
        # self.brushFunctions.deleteNode ()

    def paintStart(self):
        # self.enterPaint ( withBrushFn = False)

        self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay()
        if not self.brushFunctions.bsd:
            self.brushFunctions.doAddColorNode(
                self.dataOfSkin.deformedShape, self.dataOfSkin.theSkinCluster
            )
            self.transferValues()
        self.EVENTCATCHER.open()
        for btnName in ["pickVertex_btn", "pickInfluence_btn"]:
            self.__dict__[btnName].setEnabled(True)
        self.setStyleSheet(styleSheet + "SkinPaintWin {border : 2px solid red}")
        self.changeMultiSolo(self.multi_rb.isChecked())


# -------------------------------------------------------------------------------
# INFLUENCE ITEM
# -------------------------------------------------------------------------------
class InfluenceTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    isZeroDfm = False
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

    def getColors(self):
        self._colors = []
        for i in xrange(1, 9):
            col = cmds.displayRGBColor("userDefined{0}".format(i), q=True)
            self._colors.append([int(el * 255) for el in col])

    def __init__(self, influence, index):
        super(InfluenceTreeWidgetItem, self).__init__(["", influence])
        self._influence = influence
        self._index = index
        self.regularBG = self.background(1)
        self.darkBG = QtGui.QBrush(QtGui.QColor(120, 120, 120))
        self.getColors()
        self.setDisplay()

    def setDisplay(self):
        self.setIcon(0, self.colorIcon())
        self.setIcon(1, self.lockIcon())
        if self.isLocked():
            self.setBackground(1, self.darkBG)
        else:
            self.setBackground(1, self.regularBG)

    """
    def setColor(self, index):        
        cmds.setAttr(self._influence+'.objectColor', index)

        theCol = [col/250. for col in self._colors [index]]
        cmds.setAttr (objAsStr+".overrideColorRGB", *theCol )
        
        self.setDisplay()
    """

    def setColor(self, col):
        cmds.setAttr(self._influence + ".wireColorRGB", *col)
        self.setIcon(0, self.colorIcon())

    def color(self):
        return [255.0 * el for el in cmds.getAttr(self._influence + ".wireColorRGB")[0]]
        # return self._colors[cmds.getAttr(self._influence+'.objectColor')]

    def lockIcon(self):
        return Icons.getIcon("lock") if self.isLocked() else Icons.getIcon("lock-gray-unlocked")

    def colorIcon(self):
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtGui.QColor(*self.color()))
        return QtGui.QIcon(pixmap)

    def setLocked(self, locked, autoHide=False):
        cmds.setAttr(self._influence + ".lockInfluenceWeights", locked)
        if locked:
            self.setSelected(False)
        if autoHide and locked:
            self.setHidden(True)
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
