"""
import __main__
self = __main__.paintEditor
"""
from Qt import QtGui, QtCore, QtWidgets, QtCompat

# import shiboken2 as shiboken
from functools import partial
from maya import cmds, mel, OpenMaya
import blurdev
from blurdev.gui import Window
import os
import re
import random
import numpy as np
from studio.gui.resource import Icons
from mWeightEditor.tools.skinData import DataOfSkin
from mWeightEditor.tools.spinnerSlider import ValueSetting, ButtonWithValue, VerticalBtn
from mWeightEditor.tools.utils import (
    GlobalContext,
    toggleBlockSignals,
    deleteTheJobs,
    addNameChangedCallback,
    removeNameChangedCallback,
)
from tools.brushFunctions import BrushFunctions
from tools.catchEventsUI import CatchEventsWidget, rootWindow


# To make your color choice reproducible, uncomment the following line:
# random.seed(10)
def get_random_color(pastel_factor=0.5):
    return [
        (x + pastel_factor) / (1.0 + pastel_factor)
        for x in [random.uniform(0, 1.0) for i in [1, 2, 3]]
    ]


def color_distance(c1, c2):
    return sum([abs(x[0] - x[1]) for x in zip(c1, c2)])


def generate_new_color(existing_colors, pastel_factor=0.5):
    max_distance = None
    best_color = None
    for i in range(0, 100):
        color = get_random_color(pastel_factor=pastel_factor)
        if not existing_colors:
            return color
        best_distance = min([color_distance(color, c) for c in existing_colors])
        if not max_distance or best_distance > max_distance:
            max_distance = best_distance
            best_color = color
    return best_color


thePaintContextName = "BlurSkinartAttrContext"


def deleteNodesOnSave(*args, **kwargs):
    print "delete blurSkinDisplay Nodes On Save "
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
    "lock": getIcon("lock-48"),
    "unlock": getIcon("unlock-48"),
    "del": getIcon("delete_sign-16"),
    "fromScene": Icons.getIcon("arrow-045"),
    "pinOn": getIcon("pinOn"),
    "pinOff": getIcon("pinOff"),
    "gaussian": getIcon("circleGauss"),
    "poly": getIcon("circlePoly"),
    "solid": getIcon("circleSolid"),
    "clearText": getIcon("clearText"),
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
QWidget:disabled {
    font:italic;
    color:grey;
}
QLineEdit{
    background-color:  #bfbcba;
    color:black;
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
QCheckBox:hover
{
  background:rgb(120, 120, 120); 
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

        self.closeBtn = QtWidgets.QPushButton("X", self)
        self.closeBtn.resize(20, 20)
        self.closeBtn.move(225, 5)
        self.closeBtn.clicked.connect(self.close)

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
            ("Toggle Mirror Mode", "ALT + M"),
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

    # def mousePressEvent (self, *args):
    #    self.close()


###################################################################################
#
#   the window
#
###################################################################################
class SkinPaintWin(Window):
    """
    A simple test widget to contain and own the model and table.
    """

    colWidth = 30
    maxWidthCentralWidget = 230

    #####################################################################################
    EVENTCATCHER = None

    def __init__(self, parent=None):
        super(SkinPaintWin, self).__init__(parent)
        import __main__

        __main__.paintEditor = self

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
        self.dataOfSkin = DataOfSkin(
            useShortestNames=self.useShortestNames, createDisplayLocator=False
        )
        self.dataOfSkin.softOn = False

        self.brushFunctions = BrushFunctions(self, thePaintContextName=thePaintContextName)
        self.createWindow()
        self.setStyleSheet(styleSheet)
        self.setWindowDisplay()

        # self.addCallBacks ()
        self.buildRCMenu()
        self.createColorPicker()
        self.uiInfluenceTREE.clear()
        self.refresh()

        self.theHelpWidget = HelpWidget(self)

        if self.EVENTCATCHER == None:
            self.EVENTCATCHER = CatchEventsWidget(
                connectedWindow=self, thePaintContextName=thePaintContextName
            )

    def showEvent(self, event):
        super(SkinPaintWin, self).showEvent(event)
        self.addCallBacks()

    def colorSelected(self, color):
        values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
        item = self.colorDialog.item
        nm = item._influence
        ind = item._index
        # print ind,nm, values
        self.brushFunctions.setColor(ind, values)
        item.setColor(values)

        self.refreshWeightEditor(getLocks=False)
        # cmds.displayRGBColor ("userDefined{0}".format (theUserDefinedIndex),*values)

    def refreshWeightEditor(self, getLocks=True):
        import __main__

        if (
            hasattr(__main__, "weightEditor")
            and __main__.weightEditor in QtWidgets.QApplication.instance().topLevelWidgets()
        ):
            if getLocks:
                __main__.weightEditor.dataOfSkin.getLocksInfo()
            __main__.weightEditor._tv.repaint()

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
        resetBindPose = self.popMenu.addAction("reset bindPreMatrix", self.resetBindPreMatrix)
        self.popMenu.addAction(resetBindPose)
        self.popMenu.addSeparator()
        self.showZeroDeformers = (
            cmds.optionVar(q="showZeroDeformers")
            if cmds.optionVar(exists="showZeroDeformers")
            else True
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

    def renameCB(self, oldName, newName):
        if self.dataOfSkin:
            lst = self.dataOfSkin.driverNames + [
                self.dataOfSkin.theSkinCluster,
                self.dataOfSkin.deformedShape,
            ]
            self.dataOfSkin.renameCB(oldName, newName)
            if oldName in lst:
                self.refresh(force=False, renamedCalled=True)

    def addCallBacks(self):
        self.renameCallBack = addNameChangedCallback(self.renameCB)
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
        removeNameChangedCallback(self.renameCallBack)
        deleteTheJobs("BrushFunctions.callAfterPaint")
        deleteTheJobs("SkinPaintWin.refreshCallBack")
        deleteTheJobs("SkinPaintWin.updateMirrorCB")
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
        mel.eval("setToolTo $gMove;")
        self.brushFunctions.deleteNode()

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
        sel = cmds.ls(sl=True, tr=True)
        skn = self.dataOfSkin.theSkinCluster
        prt = (
            cmds.listRelatives(self.dataOfSkin.deformedShape, path=-True, parent=True)[0]
            if not cmds.nodeType(self.dataOfSkin.deformedShape) == "transform"
            else self.dataOfSkin.deformedShape
        )
        if prt in sel:
            sel.remove(prt)
        allInfluences = cmds.skinCluster(skn, query=True, influence=True)
        toAdd = filter(lambda x: x not in allInfluences, sel)
        if toAdd:
            toAddStr = "add Influences :\n - "
            toAddStr += "\n - ".join(toAdd[:10])
            if len(toAdd) > 10:
                toAddStr += "\n -....and {0} others..... ".format(len(toAdd) - 10)

            res = cmds.confirmDialog(
                t="add Influences",
                m=toAddStr,
                button=["Yes", "No"],
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )
            if res == "Yes":
                self.delete_btn.click()
                cmds.skinCluster(skn, edit=True, lockWeights=False, weight=0.0, addInfluence=toAdd)
                toSelect = range(
                    self.uiInfluenceTREE.topLevelItemCount(),
                    self.uiInfluenceTREE.topLevelItemCount() + len(toAdd),
                )
                cmds.evalDeferred(self.selectRefresh)
                cmds.evalDeferred(partial(self.reselectIndices, toSelect))

    def fromScene(self):
        sel = cmds.ls(sl=True, tr=True)
        for ind in range(self.uiInfluenceTREE.topLevelItemCount()):
            item = self.uiInfluenceTREE.topLevelItem(ind)
            toSel = item._influence in sel
            item.setSelected(toSel)
            if toSel:
                self.uiInfluenceTREE.scrollToItem(item)

    def reselectIndices(self, toSelect):
        count = self.uiInfluenceTREE.topLevelItemCount()
        # if toSelect[-1] < count: self.uiInfluenceTREE.topLevelItem (ind).setCurrentItem(self.uiInfluenceTREE.topLevelItem(toSelect[-1]))
        for ind in toSelect:
            if ind < count:
                self.uiInfluenceTREE.topLevelItem(ind).setSelected(True)
                self.uiInfluenceTREE.scrollToItem(self.uiInfluenceTREE.topLevelItem(ind))
        # self.uiInfluenceTREE.scrollToBottom()

    def removeInfluences(self):
        skn = self.dataOfSkin.theSkinCluster

        toRemove = [item._influence for item in self.uiInfluenceTREE.selectedItems()]
        removeable = []
        non_removable = []
        for nm in toRemove:
            columnIndex = self.dataOfSkin.driverNames.index(nm)
            res = self.dataOfSkin.display2dArray[:, columnIndex]
            notNormalizable = np.where(res >= 1.0)[0]
            if notNormalizable.size == 0:
                removeable.append(nm)
            else:
                non_removable.append((nm, notNormalizable.tolist()))
        message = ""
        toRmvStr = "\n - ".join(removeable[:10])
        if len(removeable) > 10:
            toRmvStr += "\n -....and {0} others..... ".format(len(removeable) - 10)

        message += "remove Influences :\n - {0}".format(toRmvStr)
        if non_removable:
            toNotRmvStr = "\n - ".join([el for el, vtx in non_removable])
            message += "\n\n\ncannot remove Influences :\n - {0}".format(toNotRmvStr)
            for nm, vtx in non_removable:
                selVertices = self.dataOfSkin.orderMelList(vtx)
                inList = [
                    "{1}.vtx[{0}]".format(el, self.dataOfSkin.deformedShape) for el in selVertices
                ]
                print nm, "\n", inList, "\n"
        res = cmds.confirmDialog(
            t="remove Influences",
            m=message,
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )
        if res == "Yes":
            self.delete_btn.click()
            cmds.skinCluster(skn, e=True, removeInfluence=toRemove)
            cmds.skinCluster(skn, e=True, forceNormalizeWeights=True)
            cmds.evalDeferred(self.selectRefresh)
            # res = self.dataOfSkin.display2dArray  [:,5]

    def removeUnusedInfluences(self):
        skn = self.dataOfSkin.theSkinCluster
        if skn:
            allInfluences = set(cmds.skinCluster(skn, query=True, influence=True))
            weightedInfluences = set(cmds.skinCluster(skn, query=True, weightedInfluence=True))
            zeroInfluences = list(allInfluences - weightedInfluences)
            if zeroInfluences:
                toRmvStr = "\n - ".join(zeroInfluences[:10])
                if len(zeroInfluences) > 10:
                    toRmvStr += "\n -....and {0} others..... ".format(len(zeroInfluences) - 10)

                res = cmds.confirmDialog(
                    t="remove Influences",
                    m="remove Unused Influences :\n - {0}".format(toRmvStr),
                    button=["Yes", "No"],
                    defaultButton="Yes",
                    cancelButton="No",
                    dismissString="No",
                )
                if res == "Yes":
                    self.delete_btn.click()
                    cmds.skinCluster(skn, e=True, removeInfluence=zeroInfluences)
                    cmds.evalDeferred(self.selectRefresh)

    def randomColors(self):
        self.delete_btn.click()

        golden_ratio_conjugate = 0.618033988749895
        s, v = 0.5, 0.95
        colors = []
        for itemIndex in range(self.uiInfluenceTREE.topLevelItemCount()):
            item = self.uiInfluenceTREE.topLevelItem(itemIndex)
            nm = item._influence
            ind = item._index
            """
            h = ( random.random() + golden_ratio_conjugate ) %1
            theCol = QtGui.QColor.fromHsvF (h,s,v)
            values = [theCol.redF(), theCol.greenF(), theCol.blueF()]
            """
            values = generate_new_color(colors, pastel_factor=0.2)
            colors.append(values)

            # print ind,nm, values
            self.brushFunctions.setColor(ind, values)
            item.setColor(values)
        # cmds.confirmDialog (m="randomColors")

    def createWindow(self):
        self.unLock = True
        self.unPin = True
        dialogLayout = self.mainLayout  # self.layout()

        # changing the treeWidghet
        for ind in range(dialogLayout.count()):
            it = dialogLayout.itemAt(ind)
            if isinstance(it, QtWidgets.QWidgetItem) and it.widget() == self.uiInfluenceTREE:
                break
        # for propName in ["selectionMode", "indentation","columnCount", "headerVisible", "headerDefaultSectionSize", "headerDefaultSectionSize", "headerVisible"]:
        # dialogLayout.removeItem(it)
        self.uiInfluenceTREE.deleteLater()

        self.uiInfluenceTREE = InfluenceTree(self)
        dialogLayout.insertWidget(ind, self.uiInfluenceTREE)
        # end changing the treeWidghet

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
        self.delete_btn.clicked.connect(lambda: mel.eval("setToolTo $gMove;"))
        self.delete_btn.clicked.connect(self.brushFunctions.deleteNode)
        self.delete_btn.clicked.connect(partial(self.mirrorActive_cb.setChecked, False))

        self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.pinSelection_btn.toggled.connect(self.changePin)
        self.pickVertex_btn.clicked.connect(self.pickMaxInfluence)
        self.pickInfluence_btn.clicked.connect(self.pickInfluence)
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)
        self.undo_btn.clicked.connect(self.brushFunctions.callUndo)
        self.clearText_btn.clicked.connect(self.clearInputText)

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

        self.mirrorActive_cb.toggled.connect(self.toggleMirror)
        self.mirrorActive_cb.toggled.connect(self.checkIfSameValue)
        # self.mirrorStore_btn.clicked.connect (self.getMirrorInfluenceArray)

        self.soloColorIndex = (
            cmds.optionVar(q="soloColor_SkinPaintWin")
            if cmds.optionVar(exists="soloColor_SkinPaintWin")
            else 0
        )
        self.soloColor_cb.setCurrentIndex(self.soloColorIndex)
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
        self.fromScene_btn.clicked.connect(self.fromScene)
        self.randomColors_btn.clicked.connect(self.randomColors)

        if cmds.optionVar(exists="mirrorOptions"):
            leftText, rightText = cmds.optionVar(q="mirrorOptions")
            self.uiLeftNamesLE.setText(leftText)
            self.uiRightNamesLE.setText(rightText)
        self.uiLeftNamesLE.editingFinished.connect(self.storeMirrorOptions)
        self.uiRightNamesLE.editingFinished.connect(self.storeMirrorOptions)

        for btn, icon in [
            ("clearText", "clearText"),
            ("addInfluences", "plus"),
            ("removeInfluences", "minus"),
            ("removeUnusedInfluences", "removeUnused"),
            ("randomColors", "randomColor"),
            ("fromScene", "fromScene"),
        ]:
            theBtn = self.__dict__[btn + "_btn"]
            theBtn.setText("")
            theBtn.setIcon(_icons[icon])
        self.locks_btn.clicked.connect(lambda: self.locks_btn.setText("locks"))
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
        self.flood_btn.clicked.connect(self.brushFunctions.flood)
        self.smooth_btn.toggled.connect(self.updateOptionEnable)
        self.sharpen_btn.toggled.connect(self.updateOptionEnable)
        self.updateOptionEnable(True)

        for nm in ["lock", "refresh", "pinSelection"]:
            self.__dict__[nm + "_btn"].setText("")
        self.uiToActivateWithPaint = ["pickVertex_btn", "pickInfluence_btn", "mirrorActive_cb"]
        for btnName in self.uiToActivateWithPaint:
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

        dialogLayout.insertSpacing(2, 10)
        dialogLayout.insertLayout(1, Hlayout)
        dialogLayout.insertLayout(1, Hlayout2)
        dialogLayout.insertSpacing(1, 10)

    def clearInputText(self):
        self.searchInfluences_le.clear()

    def updateMirrorCB(self):
        mirrorActive = self.brushFunctions.getBSDAttr("mirrorActive")
        with toggleBlockSignals([self.mirrorActive_cb]):
            self.mirrorActive_cb.setChecked(False)

    def toggleMirror(self, val):
        if val:
            self.getMirrorInfluenceArray()
        self.brushFunctions.setBSDAttr("mirrorActive", val)

    def checkIfSameValue(self, val):
        attr = "mirrorActive"
        deleteTheJobs("SkinPaintWin.updateMirrorCB")
        if cmds.objExists(self.brushFunctions.bsd) and cmds.attributeQuery(
            attr, node=self.brushFunctions.bsd, exists=True
        ):
            cmds.scriptJob(
                runOnce=True,
                attributeChange=[self.brushFunctions.bsd + "." + attr, self.updateMirrorCB],
            )

    def storeMirrorOptions(self):
        cmds.optionVar(clearArray="mirrorOptions")
        cmds.optionVar(stringValueAppend=("mirrorOptions", self.uiLeftNamesLE.text()))
        cmds.optionVar(stringValueAppend=("mirrorOptions", self.uiRightNamesLE.text()))

    def getMirrorInfluenceArray(self):
        from mrigtools.tools import mirrorFn

        msh = cmds.listRelatives(self.dataOfSkin.deformedShape, path=True, parent=True)[0]
        if not cmds.attributeQuery("symmetricVertices", node=msh, exists=True):
            selectionShapes = mirrorFn.getShapesSelected(intermediateObject=True)
            _symData = mirrorFn.SymData()
            _symData.computeSymetry(selectionShapes[-1], displayInfo=False)
        leftInfluence = self.uiLeftNamesLE.text()
        rightInfluence = self.uiRightNamesLE.text()
        driverNames_oppIndices = self.dataOfSkin.getArrayOppInfluences(
            leftInfluence=leftInfluence, rightInfluence=rightInfluence, useRealIndices=True
        )
        if not driverNames_oppIndices:
            return
        self.brushFunctions.setMirrorInfluences(driverNames_oppIndices)

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
                        self.uiInfluenceTREE.topLevelItem(i)._influence
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
        txt = item._influence  # text(1)
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
        text = item._influence  # text(1)
        # print "CLICKED " + text
        if text in self.dataOfSkin.driverNames:
            # ind = self.dataOfSkin.driverNames.index (text)
            ind = item._index
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
            toSel = cmds.ls([item._influence for item in selectedItems])
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
            self.refreshWeightEditor(getLocks=True)

    def resetBindPreMatrix(self):
        selectedItems = self.uiInfluenceTREE.selectedItems()
        for item in selectedItems:
            item.resetBindPose()

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
            newTexts = newText.split(" ")
            while "" in newTexts:
                newTexts.remove("")
            for nm, it in self.uiInfluenceTREE.dicWidgName.iteritems():
                foundText = False
                for txt in newTexts:
                    txt = txt.replace("*", ".*")
                    foundText = re.search(txt, nm, re.IGNORECASE) != None
                    if foundText:
                        break
                it.setHidden(not foundText)
        else:
            for nm, item in self.uiInfluenceTREE.dicWidgName.iteritems():
                item.setHidden(not self.showZeroDeformers and item.isZeroDfm)

    def refreshBtn(self):
        self.refresh(force=True)

    def selectRefresh(self):
        cmds.select(self.dataOfSkin.deformedShape)
        self.refresh(force=True)

    def prepareToGetHighestInfluence(self):
        self.highestInfluence = -1
        self.dataOfSkin.softOn = False
        self.dataOfSkin.rawSkinValues = self.dataOfSkin.exposeSkinData(
            self.dataOfSkin.theSkinCluster
        )
        self.dataOfSkin.getZeroColumns()

    def getHighestInfluence(self, vtxIndex):
        highestDriver = np.argmax(self.dataOfSkin.raw2dArray[vtxIndex])
        self.highestInfluence = self.dataOfSkin.indicesJoints[highestDriver]
        return self.dataOfSkin.driverNames[highestDriver]

    def selectPickedInfluence(self):
        if self.highestInfluence in self.dataOfSkin.indicesJoints:
            highestDriver = self.dataOfSkin.indicesJoints.index(self.highestInfluence)
            # print self.highestInfluence, highestDriver
            self.uiInfluenceTREE.setCurrentItem(self.uiInfluenceTREE.topLevelItem(highestDriver))
            self.brushFunctions.setInfluenceIndex(int(self.highestInfluence))

    def refreshColorsAndLocks(self):
        for i in range(self.uiInfluenceTREE.topLevelItemCount()):
            item = self.uiInfluenceTREE.topLevelItem(i)
            item.setDisplay()
            if item.currentColor != item.color():
                # we need a real update :
                ind = item._index
                item.currentColor = item.color()
                self.brushFunctions.setColor(ind, item.currentColor)
                # print ind, item._influence
        self.brushFunctions.setBSDAttr("getLockWeights", True)

    def refreshCallBack(self):
        currContext = cmds.currentCtx()
        if (
            not self.lock_btn.isChecked() and currContext != thePaintContextName
        ):  # dont refresh for paint
            self.refresh()

    def refresh(self, force=False, renamedCalled=False):
        # print "refresh CALLED"
        with GlobalContext(message="paintEditor getAllData", doPrint=False):
            resultData = self.dataOfSkin.getAllData(
                displayLocator=False, getskinWeights=True, force=force
            )
        if renamedCalled or resultData:
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
                theIndexJnt = self.dataOfSkin.indicesJoints[ind]
                theCol = self.uiInfluenceTREE.getDeformerColor(nm)
                jointItem = InfluenceTreeWidgetItem(
                    nm, theIndexJnt, theCol, self.dataOfSkin.theSkinCluster
                )
                # jointItem =  QtWidgets.QTreeWidgetItem()
                # jointItem.setText (1, nm)
                self.uiInfluenceTREE.addTopLevelItem(jointItem)
                self.uiInfluenceTREE.dicWidgName[nm] = jointItem

                jointItem.isZeroDfm = ind in self.dataOfSkin.hideColumnIndices
                jointItem.setHidden(not self.showZeroDeformers and jointItem.isZeroDfm)

    def paintEnd(self):
        self.EVENTCATCHER.fermer()  # removeFilters ()
        for btnName in self.uiToActivateWithPaint:
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
        for btnName in self.uiToActivateWithPaint:
            self.__dict__[btnName].setEnabled(True)
        self.setStyleSheet(styleSheet + "SkinPaintWin {border : 2px solid red}")
        self.changeMultiSolo(self.multi_rb.isChecked())


# -------------------------------------------------------------------------------
# INFLUENCE ITEM
# -------------------------------------------------------------------------------
class InfluenceTree(QtWidgets.QTreeWidget):
    blueBG = QtGui.QBrush(QtGui.QColor(112, 124, 137))
    redBG = QtGui.QBrush(QtGui.QColor(134, 119, 127))
    yellowBG = QtGui.QBrush(QtGui.QColor(144, 144, 122))
    regularBG = QtGui.QBrush(QtGui.QColor(130, 130, 130))

    def getDeformerColor(self, driverName):
        try:
            for letter, col in [("L", self.redBG), ("R", self.blueBG), ("M", self.yellowBG)]:
                if "_{0}_".format(letter) in driverName:
                    return col
            return self.regularBG
        except:
            return self.regularBG

    def __init__(self, *args):
        self.isOn = False
        super(InfluenceTree, self).__init__(*args)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setIndentation(5)
        self.setColumnCount(2)
        self.header().hide()
        self.setColumnWidth(0, 20)

    def enterEvent(self, event):
        # print "enterEvent TREE"
        self.isOn = True
        super(InfluenceTree, self).enterEvent(event)

    def leaveEvent(self, event):
        # print "leaveEvent TREE"
        self.isOn = False
        super(InfluenceTree, self).leaveEvent(event)


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

    def __init__(self, influence, index, col, skinCluster):
        shortName = influence.split(":")[-1]
        super(InfluenceTreeWidgetItem, self).__init__(["", shortName])
        self._influence = influence
        self._index = index
        self._skinCluster = skinCluster
        self.regularBG = col  # self.background(1)

        self.currentColor = [
            255.0 * el for el in cmds.getAttr(self._influence + ".wireColorRGB")[0]
        ]

        self.setBackground(1, self.regularBG)
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

    def resetBindPose(self):
        inConn = cmds.listConnections(self._skinCluster + ".bindPreMatrix[{0}]".format(self._index))
        if not inConn:
            mat = cmds.getAttr(self._influence + ".worldInverseMatrix")
            cmds.setAttr(
                self._skinCluster + ".bindPreMatrix[{0}]".format(self._index), mat, type="matrix"
            )

    """
    def setColor(self, index):        
        cmds.setAttr(self._influence+'.objectColor', index)

        theCol = [col/250. for col in self._colors [index]]
        cmds.setAttr (objAsStr+".overrideColorRGB", *theCol )
        
        self.setDisplay()
    """

    def setColor(self, col):
        self.currentColor = col
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
