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
    SettingVariable,
)

# from tools.brushFunctions import BrushFunctions
from brushTools.catchEventsUI import CatchEventsWidget, rootWindow
from brushTools.brushPythonFunctions import (
    setColorsOnJoints,
    fixOptionVarContext,
    generate_new_color,
    deleteExistingColorSets,
    setSoloMode,
    reloadSkin,
)


class ValueSettingPE(ValueSetting):
    # def doSet(self, theVal):
    #     self.mainWindow.value = theVal
    blockPostSet = False

    def postSet(self):
        if not self.blockPostSet:
            if cmds.currentCtx() == "brSkinBrushContext1":
                value = self.theSpinner.value()
                if self.commandArg in ["strength", "smoothStrength"]:
                    value /= 100.0
                kArgs = {"edit": True}
                kArgs[self.commandArg] = value
                cmds.brSkinBrushContext("brSkinBrushContext1", **kArgs)

    def progressValueChanged(self, val):
        pos = self.theProgress.pos().x() + val / 100.0 * (
            self.theProgress.width() - self.btn.width()
        )
        self.btn.move(pos, 0)

    def setEnabled(self, val):
        if val:
            self.btn.setStyleSheet("border : 1px solid black; background-color:rgb(200,200,200)")
        else:
            self.btn.setStyleSheet("border : 1px solid black; background-color:rgb(170,170,170)")
        super(ValueSettingPE, self).setEnabled(val)

    def updateBtn(self):
        self.progressValueChanged(self.theProgress.value())

    def __init__(self, *args, **kwargs):
        text = ""
        if "text" in kwargs:
            text = kwargs["text"]
            kwargs.pop("text")
        if "commandArg" in kwargs:
            self.commandArg = kwargs["commandArg"]
            kwargs.pop("commandArg")
        super(ValueSettingPE, self).__init__(*args, **kwargs)

        self.theProgress.valueChanged.connect(self.progressValueChanged)
        self.theProgress.setTextVisible(True)
        self.theProgress.setFormat(text)
        self.theProgress.setMaximumHeight(12)
        self.theSpinner.setMaximumHeight(16)
        self.setMinimumHeight(18)

        self.theSpinner.setMaximum(100)
        self.theSpinner.setMinimum(0)

        btn = QtWidgets.QFrame(self)
        btn.show()
        btn.resize(6, 18)
        btn.move(100, 0)
        btn.pos()
        btn.show()
        btn.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        btn.setStyleSheet("border : 1px solid black; background-color:rgb(200,200,200)")
        self.btn = btn
        self.updateBtn()


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
    "curveNone": getIcon("brSkinBrushNone"),
    "curveLinear": getIcon("brSkinBrushLinear"),
    "curveSmooth": getIcon("brSkinBrushSmooth"),
    "curveNarrow": getIcon("brSkinBrushNarrow"),
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
QSplitter::handle {
    border-radius: 5px;
    border: 1px solid gray;
    background-color:  #bfbcba;
}
QSplitter::handle::hover {
    border-radius: 5px;
    border: 1px solid lightGray; 
    background-color:  gray;
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
QGroupBox {
    background-color:  #aba8a6;
    border: 1px solid grey;
    margin-top: 1ex; /* leave space at the top for the title */
}
QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 3px;
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

lstShortCuts = [
    ("Remove ", "Shift + LMB"),
    ("Smooth", "Ctrl + LMB"),
    ("Sharpen", "Ctrl + Shift + LMB"),
    ("Size", "MMB left right"),
    ("Strength", "MMB up down"),
    ("Fine Strength Size", "Ctrl + MMB"),
    ("markingMenu ", "U"),
    ("pick influence", "D"),
    ("pick Vertex ", "ALT + D"),
    ("Toggle Mirror Mode", "ALT + M"),
    ("Toggle Solo Mode", "ALT + S"),
    ("Toggle Solo Opaque", "ALT + A"),
    ("Toggle Wireframe", "ALT + W"),
    ("Toggle Xray", "ALT + X"),
    # ("Flood", "ALT + F"),
    ("Orbit Center To", "F"),
    ("Undo", "CTRL + Z"),
    ("Quit", "Escape or Q"),
    # ("update Value", "N"),
]

###################################################################################
#
#   the window
#
###################################################################################
class SkinPaintWin(Window):
    colWidth = 30
    maxWidthCentralWidget = 230

    #####################################################################################
    # EVENTCATCHER = None

    def __init__(self, parent=None):
        super(SkinPaintWin, self).__init__(parent)
        import __main__

        __main__.paintEditor = self

        if not cmds.pluginInfo("brSkinBrush", q=True, loaded=True):
            cmds.loadPlugin("brSkinBrush")
        if not cmds.pluginInfo("wireframeDisplay", q=True, loaded=True):
            cmds.loadPlugin("wireframeDisplay")
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

        self.createWindow()
        self.addShortCutsHelp()

        self.setStyleSheet(styleSheet)
        self.setWindowDisplay()

        self.buildRCMenu()
        self.createColorPicker()
        self.uiInfluenceTREE.clear()
        self.refresh()

    def addShortCutsHelp(self):
        for nm1, nm2 in lstShortCuts:
            helpItem = QtWidgets.QTreeWidgetItem()
            helpItem.setText(0, nm2)
            helpItem.setText(1, nm1)
            self.shortCut_Tree.addTopLevelItem(helpItem)
        self.shortCut_Tree.setStyleSheet(
            "QTreeWidget::item { padding-right:5px;padding-left:5px;border-right: 1px solid grey;border-bottom: 1px solid grey;}"
        )
        self.shortCut_Tree.setIndentation(0)
        self.shortCut_Tree.header().hide()
        self.shortCut_Tree.resizeColumnToContents(0)

    def showEvent(self, event):
        super(SkinPaintWin, self).showEvent(event)
        self.addCallBacks()
        cmds.evalDeferred(self.updateUIwithContextValues)
        cmds.evalDeferred(self.refresh)

    def colorSelected(self, color):
        values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
        item = self.colorDialog.item
        nm = item._influence
        ind = item._index
        # print ind, nm, values
        item.setColor(values)

        self.refreshWeightEditor(getLocks=False)
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", e=True, refreshDfmColor=ind)

    def refreshWeightEditor(self, getLocks=True):
        import __main__

        if (
            hasattr(__main__, "weightEditor")
            and __main__.weightEditor in QtWidgets.QApplication.instance().topLevelWidgets()
        ):
            if getLocks:
                __main__.weightEditor.dataOfDeformer.getLocksInfo()
            __main__.weightEditor._tv.repaint()

    def revertColor(self):
        self.colorDialog.setCurrentColor(self.colorDialog.cancelColor)

    def createColorPicker(self):
        self.colorDialog = QtWidgets.QColorDialog()
        # self.colorDialog .colorSelected.connect ( self.colorSelected )
        self.colorDialog.currentColorChanged.connect(self.colorSelected)
        self.colorDialog.rejected.connect(self.revertColor)
        self.colorDialog.setWindowFlags(QtCore.Qt.Tool)
        self.colorDialog.setWindowTitle("pick color")
        self.colorDialog.setWindowModality(QtCore.Qt.ApplicationModal)

    def buildRCMenu(self):
        self.mainPopMenu = QtWidgets.QMenu(self)
        self.subMenuSoloColor = self.mainPopMenu.addMenu("solo color")
        soloColorIndex = (
            cmds.optionVar(q="soloColor_SkinPaintWin")
            if cmds.optionVar(exists="soloColor_SkinPaintWin")
            else 0
        )
        for ind, colType in enumerate(["white", "lava", "influence"]):
            theFn = partial(self.updateSoloColor, ind)
            act = self.subMenuSoloColor.addAction(colType, theFn)
            act.setCheckable(True)
            act.setChecked(soloColorIndex == ind)
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
        soloColorIndex = ind
        cmds.optionVar(intValue=["soloColor_SkinPaintWin", ind])
        for i in range(3):
            self.subMenuSoloColor.actions()[i].setChecked(i == ind)
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, soloColorType=ind)

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
        # self.refreshPosition ()
        self.show()

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

        sceneUpdateCallback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeNew, self.exitPaint
        )
        self.close_callback = [sceneUpdateCallback]
        self.close_callback.append(
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeOpen, self.exitPaint)
        )
        self.close_callback.append(
            OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeSave, self.exitPaint)
        )

    def deleteCallBacks(self):
        try:
            removeNameChangedCallback(self.renameCallBack)
        except RuntimeError:
            print "can't remove it "
        deleteTheJobs("SkinPaintWin.refreshCallBack")
        deleteTheJobs("SkinPaintWin.updateMirrorCB")
        cmds.scriptJob(kill=self.refreshSJ, force=True)
        for callBck in self.close_callback:
            OpenMaya.MSceneMessage.removeCallback(callBck)
        print "callBack deleted"

    commandIndex = -1
    previousInfluenceName = ""
    value = 1.0
    commandArray = ["add", "rmv", "addPerc", "abs", "smooth", "sharpen", "locks", "unLocks"]
    highlightingBtn = False

    def highlightBtn(self, btnName):
        key = btnName + "_btn"
        if key in self.__dict__:
            thebtn = self.__dict__[key]
            thebtn.setChecked(True)

    def getCommandIndex(self):
        for ind, nm in enumerate(self.commandArray):
            thebtn = self.__dict__[nm + "_btn"]
            if thebtn.isChecked():
                return ind
        return -1

    def getEnabledButton(self):
        for ind, nm in enumerate(self.commandArray):
            thebtn = self.__dict__[nm + "_btn"]
            if thebtn.isChecked():
                return nm
        return False

    def changeCommand(self, newCommand):
        commandText = self.commandArray[newCommand]
        print commandText
        if commandText in ["locks", "unLocks"]:
            self.valueSetter.setEnabled(False)
            self.widgetAbs.setEnabled(False)
        else:
            contextExists = cmds.brSkinBrushContext("brSkinBrushContext1", q=True, ex=True)
            self.valueSetter.setEnabled(True)
            self.widgetAbs.setEnabled(True)
            if commandText == "smooth":
                theValue = (
                    cmds.brSkinBrushContext("brSkinBrushContext1", query=True, smoothStrength=True)
                    if contextExists
                    else self.smoothStrengthVarStored
                )
                self.valueSetter.commandArg = "smoothStrength"
            else:
                theValue = (
                    cmds.brSkinBrushContext("brSkinBrushContext1", query=True, strength=True)
                    if contextExists
                    else self.strengthVarStored
                )
                self.valueSetter.commandArg = "strength"
            try:
                cmds.floatSliderGrp("brSkinBrushStrength", edit=True, value=theValue)
            except:
                pass
            self.updateStrengthVal(theValue)
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, commandIndex=newCommand)

    def closeEvent(self, event):
        mel.eval("setToolTo $gMove;")

        self.deleteCallBacks()
        # pos = self.pos()
        # size = self.size()
        # cmds.optionVar (clearArray= "SkinPaintWindow")
        # for el in pos.x (), pos.y(), size.width(), size.height() :
        #     cmds.optionVar (intValueAppend = ("SkinPaintWindow", el))
        # cmds.optionVar (intValueAppend = ("SkinPaintWindow", self.commandIndex))
        # self.storePrevCommandValue ()

        # self.headerView.deleteLater()
        # if self.EVENTCATCHER!=None: self.EVENTCATCHER.close()
        super(SkinPaintWin, self).closeEvent(event)

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
            newBtn.clicked.connect(partial(self.updateStrengthVal, theVal / 100.0))
            newBtn.clicked.connect(self.valueSetter.postSet)
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
            cmds.scriptJob(kill=self.refreshSJ, force=True)
            print "deleting callback"
        else:
            self.lock_btn.setIcon(_icons["unlock"])
            self.refreshSJ = cmds.scriptJob(event=["SelectionChanged", self.refreshCallBack])
            print "recreating callback"
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
        pass
        # if cmds.currentCtx() == thePaintContextName:
        #     currentVal = cmds.artAttrCtx(thePaintContextName ,q=True,value = True)
        #     self.updateStrengthVal (currentVal)

    def isInPaint(self):
        currentContext = cmds.currentCtx()
        if currentContext.startswith("brSkinBrushContext"):
            return currentContext
        return False

    def exitPaint(self, *args):  # *args for callBacks
        if self.isInPaint():
            mel.eval("setToolTo $gMove;")

    def enterPaint(self):
        if not cmds.pluginInfo(" brSkinBrush", query=True, loaded=True):
            cmds.loadPlugin("brSkinBrush")
        if self.dataOfSkin.theSkinCluster:
            # print "ENTERPAINT \n"
            setColorsOnJoints()
            context = "brSkinBrushContext1"
            # "from brSkinBrush_pythonFunctions import "
            dic = {
                "soloColor": self.solo_rb.isChecked(),
                "soloColorType": self.soloColor_cb.currentIndex(),
                "size": self.sizeBrushSetter.theSpinner.value(),
                "strength": self.valueSetter.theSpinner.value() * 0.01,
                "commandIndex": self.getCommandIndex(),
            }
            selectedInfluences = self.selectedInfluences()
            if selectedInfluences:
                dic["influenceName"] = selectedInfluences[0]
            fixOptionVarContext(**dic)

            if not cmds.contextInfo(context, ex=True):
                importPython = "from mPaintEditor.brushTools.brushPythonFunctions import "
                context = cmds.brSkinBrushContext(context, importPython=importPython)
            cmds.setToolTo(context)
            mel.eval("rememberCtxSettings " + context)

    def updateOptionEnable(self, toggleValue):
        setOn = self.smooth_btn.isChecked() or self.sharpen_btn.isChecked()
        # for btn in [self.repeatBTN, self.depthBTN]:
        #     btn.setEnabled (setOn)

    def upateSoloModeRBs(self, val):
        if val:
            self.solo_rb.setChecked(True)
        else:
            self.multi_rb.setChecked(True)

    def updateStrengthVal(self, value):
        with SettingVariable(self.valueSetter, "blockPostSet", valueOn=True, valueOut=False):
            self.valueSetter.setVal(value * 100.0)
            self.valueSetter.theProgress.setValue(value * 100.0)

    def updateSizeVal(self, value):
        with SettingVariable(self.sizeBrushSetter, "blockPostSet", valueOn=True, valueOut=False):
            self.sizeBrushSetter.setVal(value)
            self.sizeBrushSetter.theProgress.setValue(value)

    def updateCurrentInfluence(self, jointName):
        # print "updateCurrentInfluence {}".format(jointName)
        items = {}
        ito = None
        for i in range(self.uiInfluenceTREE.topLevelItemCount()):
            it = self.uiInfluenceTREE.topLevelItem(i)
            items[it.text(1)] = it
            if i == 0:
                ito = it
        if jointName in items:
            self.uiInfluenceTREE.clearSelection()
            self.uiInfluenceTREE.setCurrentItem(items[jointName])
        else:
            self.uiInfluenceTREE.clearSelection()
            if ito:  # if there's joints , selct first one
                self.uiInfluenceTREE.setCurrentItem(ito)

    def changeMultiSolo(self, val):
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, soloColor=val)
            setSoloMode(val)

    def addInfluences(self):
        sel = cmds.ls(sl=True, type="joint")
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
                cmds.evalDeferred(partial(self.addInfluencesColors, toSelect))
                # add color to the damn influences added

    def addInfluencesColors(self, toSelect):
        count = self.uiInfluenceTREE.topLevelItemCount()
        colors = []
        for ind in toSelect:
            item = self.uiInfluenceTREE.topLevelItem(ind)
            if ind < count:
                nm = item._influence
                ind = item._index
                item.color
                values = generate_new_color(
                    colors,
                    pastel_factor=0.2,
                    valueMult=self.valueMult,
                    saturationMult=self.saturationMult,
                )
                colors.append(values)
                item.setColor(values)
            else:
                colors.append(item.currentColor)

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

    valueMult, saturationMult = 0.6, 0.6

    def randomColors(self):
        # self.delete_btn.click()

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
            values = generate_new_color(
                colors,
                pastel_factor=0.2,
                valueMult=self.valueMult,
                saturationMult=self.saturationMult,
            )
            colors.append(values)

            # print ind,nm, values
            item.setColor(values)
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", e=True, refresh=True)
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
        dialogLayout.setSpacing(0)
        # for propName in ["selectionMode", "indentation","columnCount", "headerVisible", "headerDefaultSectionSize", "headerDefaultSectionSize", "headerVisible"]:
        # dialogLayout.removeItem(it)
        self.uiInfluenceTREE.deleteLater()

        self.uiInfluenceTREE = InfluenceTree(self)
        dialogLayout.insertWidget(ind, self.uiInfluenceTREE)
        # end changing the treeWidghet

        self.lock_btn.setIcon(_icons["unlock"])
        self.refresh_btn.setIcon(_icons["refresh"])
        self.lock_btn.toggled.connect(self.changeLock)
        self.dgParallel_btn.toggled.connect(self.changeDGParallel)
        self.refresh_btn.clicked.connect(self.refreshBtn)
        self.enterPaint_btn.clicked.connect(self.enterPaint)

        self.deleteExisitingColorSets_btn.clicked.connect(deleteExistingColorSets)

        self.showLocks_btn.setIcon(_icons["eye"])
        self.showLocks_btn.toggled.connect(self.showHideLocks)
        self.showLocks_btn.setText("")

        self.delete_btn.setIcon(_icons["del"])
        self.delete_btn.setText("")
        # self.delete_btn.clicked.connect (self.paintEnd )
        self.delete_btn.clicked.connect(self.exitPaint)
        # self.delete_btn.clicked.connect (partial (self.mirrorActive_cb.setChecked, False))

        self.pinSelection_btn.setIcon(_icons["pinOff"])
        self.pinSelection_btn.toggled.connect(self.changePin)
        self.pickVertex_btn.clicked.connect(self.pickMaxInfluence)
        self.pickInfluence_btn.clicked.connect(self.pickInfluence)
        self.clearText_btn.clicked.connect(self.clearInputText)

        self.searchInfluences_le.textChanged.connect(self.filterInfluences)
        self.solo_rb.toggled.connect(self.changeMultiSolo)

        # self.repeatBTN = ButtonWithValue (self.buttonWidg, usePow = False, name = "iter", minimumValue = 1, defaultValue = 1, step = 1, clickable=False, minHeight=20, addSpace = False)
        # self.depthBTN = ButtonWithValue (self.buttonWidg, usePow = False, name = "dpth", minimumValue = 1, maximumValue = 9, defaultValue = 1, step = 1, clickable=False, minHeight=20, addSpace = False)
        # self.smoothOption_lay.addWidget (self.repeatBTN )
        # self.smoothOption_lay.addWidget (self.depthBTN)

        # self.mirrorActive_cb.toggled.connect (self.toggleMirror)
        # self.mirrorActive_cb.toggled.connect (self.checkIfSameValue)
        # self.mirrorStore_btn.clicked.connect (self.getMirrorInfluenceArray)
        self.soloColor_cb.currentIndexChanged.connect(self.comboSoloColorChanged)
        # self.uiInfluenceTREE.itemSelectionChanged.connect(self.influenceSelChanged)
        self.uiInfluenceTREE.itemDoubleClicked.connect(self.influenceDoubleClicked)
        self.uiInfluenceTREE.itemClicked.connect(self.influenceClicked)

        self.option_btn.clicked.connect(self.displayOptions)

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
        # self.locks_btn.clicked.connect (lambda : self.locks_btn.setText("locks"))
        for ind, nm in enumerate(self.commandArray):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.clicked.connect(partial(self.changeCommand, ind))
        for ind, nm in enumerate(["curveNone", "curveLinear", "curveSmooth", "curveNarrow"]):
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.setText("")
            thebtn.setIcon(_icons[nm])
            thebtn.setToolTip(nm)
            thebtn.clicked.connect(partial(self.brSkinConn, "curve", ind))
        self.flood_btn.clicked.connect(partial(self.brSkinConn, "flood", True))
        # self.smooth_btn.toggled.connect(self.updateOptionEnable)
        # self.sharpen_btn.toggled.connect(self.updateOptionEnable)
        # self.updateOptionEnable(True)

        for nm in ["lock", "refresh", "pinSelection"]:
            self.__dict__[nm + "_btn"].setText("")
        self.uiToActivateWithPaint = [
            "pickVertex_btn",
            "pickInfluence_btn",
            "flood_btn",
        ]  # , "mirrorActive_cb"]
        for btnName in self.uiToActivateWithPaint:
            self.__dict__[btnName].setEnabled(False)
        self.valueSetter = ValueSettingPE(
            self, precision=2, text="intensity", commandArg="strength", spacing=2
        )
        self.valueSetter.setAddMode(False, autoReset=False)

        self.sizeBrushSetter = ValueSettingPE(
            self, precision=2, text="brush size", commandArg="size", spacing=2
        )
        self.sizeBrushSetter.setAddMode(False, autoReset=False)

        Hlayout = QtWidgets.QHBoxLayout()
        Hlayout.setContentsMargins(0, 0, 0, 0)
        Hlayout.setSpacing(0)

        Vlayout = QtWidgets.QVBoxLayout()
        Vlayout.setContentsMargins(0, 0, 0, 0)
        Vlayout.setSpacing(0)
        Vlayout.addWidget(self.valueSetter)
        Vlayout.addWidget(self.sizeBrushSetter)

        Hlayout.addLayout(Vlayout)

        self.valueSetter.setMaximumSize(self.maxWidthCentralWidget, 18)
        self.sizeBrushSetter.setMaximumSize(self.maxWidthCentralWidget, 18)

        self.widgetAbs = self.addButtonsDirectSet([0.25, 0.5, 1, 2, 5, 10, 25, 50, 75, 100])

        Hlayout2 = QtWidgets.QHBoxLayout()
        Hlayout2.setContentsMargins(0, 0, 0, 0)
        Hlayout2.setSpacing(0)
        Hlayout2.addWidget(self.widgetAbs)

        dialogLayout.insertSpacing(2, 10)
        dialogLayout.insertLayout(1, Hlayout)
        dialogLayout.insertLayout(1, Hlayout2)
        dialogLayout.insertSpacing(1, 10)
        cmds.evalDeferred(self.fixUI)

        self.scrollAreaWidgetContents.layout().setContentsMargins(9, 9, 9, 9)
        sz = self.splitter.sizes()
        self.splitter.setSizes([sz[0] + sz[1], 0])

        self.drawManager_rb.toggled.connect(self.drawManager_gb.setEnabled)

        self.listCheckBoxesDirectAction = [
            "meshdrawTriangles",
            "meshdrawEdges",
            "meshdrawPoints",
            "meshdrawTransparency",
            "drawBrush",
            "coverage",
            "postSetting",
            "message",
            "ignoreLock",
            "verbose",
        ]
        for att in self.listCheckBoxesDirectAction:
            checkBox = self.__dict__[att + "_cb"]
            checkBox.toggled.connect(partial(self.brSkinConn, att))
        self.colorSets_rb.toggled.connect(partial(self.brSkinConn, "useColorSetsWhilePainting"))
        self.smoothRepeat_spn.valueChanged.connect(partial(self.brSkinConn, "smoothRepeat"))

        self.maxColor_sb.valueChanged.connect(partial(self.brSkinConn, "maxColor"))
        self.minColor_sb.valueChanged.connect(self.editSoloColor)

        self.soloOpaque_cb.toggled.connect(self.opaqueSet)

        self.wireframe_cb.toggled.connect(self.wireframeToggle)
        self.WarningFixSkin_btn.setVisible(False)
        self.WarningFixSkin_btn.clicked.connect(self.fixSparseArray)
        """
        things that are not working yet !!!
        """

    def opaqueSet(self, checked):
        val = 1.0 if checked else 0.0
        self.brSkinConn("minColor", val)
        with toggleBlockSignals([self.minColor_sb]):
            self.minColor_sb.setValue(val)

    def editSoloColor(self, val):
        with toggleBlockSignals([self.soloOpaque_cb]):
            self.soloOpaque_cb.setChecked(val == 1.0)
        self.brSkinConn("minColor", val)

    def changeDGParallel(self, val):
        # isDG = cmds.evaluationManager( q=True, mode=True) == [u'off']
        if val:
            self.dgParallel_btn.setText("parallel on")
            cmds.evaluationManager(mode="parallel")
        else:
            self.dgParallel_btn.setText("parallel off")
            cmds.evaluationManager(mode="off")
        # val = cmds.optionVar(q="evaluationMode")
        # cmds.evaluationManager(  mode=goodMode)

    def wireframeToggle(self, val):
        if not val and cmds.objExists("SkinningWireframe"):
            cmds.delete("SkinningWireframe")

    def brSkinConn(self, nm, val):
        if self.isInPaint():
            kArgs = {"edit": True}
            kArgs[nm] = val
            cmds.brSkinBrushContext("brSkinBrushContext1", **kArgs)

    def displayOptions(self, val):
        heightOption = 480
        sz = self.splitter.sizes()
        sumSizes = sz[0] + sz[1]
        if sz[1] != 0:
            self.splitter.setSizes([sumSizes, 0])
        else:
            if sumSizes > heightOption:
                self.splitter.setSizes([sumSizes - heightOption, heightOption])
            else:
                self.splitter.setSizes([0, sumSizes])

    def fixUI(self):
        for nm in self.commandArray:
            self.__dict__[nm + "_btn"].setMinimumHeight(23)
        self.valueSetter.updateBtn()
        self.sizeBrushSetter.updateBtn()

    def updateUIwithContextValues(self):
        self.dgParallel_btn.setChecked(cmds.optionVar(q="evaluationMode") == 3)

        KArgs = fixOptionVarContext()
        if "soloColor" in KArgs:
            val = int(KArgs["soloColor"])
            if val:
                self.solo_rb.setChecked(True)
            else:
                self.multi_rb.setChecked(True)
        if "soloColorType" in KArgs:
            self.soloColor_cb.setCurrentIndex(int(KArgs["soloColorType"]))
        sizeVal = 4.0
        if "size" in KArgs:
            sizeVal = float(KArgs["size"])
        self.updateSizeVal(sizeVal)

        if "strength" in KArgs:
            self.strengthVarStored = float(KArgs["strength"])
        else:
            self.strengthVarStored = 1.0
        self.updateStrengthVal(self.strengthVarStored)

        if "commandIndex" in KArgs:
            commandIndex = int(KArgs["commandIndex"])
            commandText = self.commandArray[commandIndex]
            self.__dict__[commandText + "_btn"].setChecked(True)
            if commandText in ["locks", "unLocks"]:
                self.valueSetter.setEnabled(False)
                self.widgetAbs.setEnabled(False)
        if "curve" in KArgs:
            curveIndex = int(KArgs["curve"])
            nm = ["curveNone", "curveLinear", "curveSmooth", "curveNarrow"][curveIndex]
            thebtn = self.__dict__[nm + "_btn"]
            thebtn.setChecked(True)
        if "smoothStrength" in KArgs:
            self.smoothStrengthVarStored = float(KArgs["smoothStrength"])
        else:
            self.smoothStrengthVarStored = 1.0
        if self.smooth_btn.isChecked():
            self.updateStrengthVal(self.smoothStrengthVarStored)
        if "influenceName" in KArgs:
            jointName = KArgs["influenceName"]
            self.previousInfluenceName = jointName
            self.updateCurrentInfluence(jointName)
        if "useColorSetsWhilePainting" in KArgs:
            val = bool(int(KArgs["useColorSetsWhilePainting"]))
            if val:
                self.colorSets_rb.setChecked(True)
            else:
                self.drawManager_rb.setChecked(True)
        if "smoothRepeat" in KArgs:
            val = int(KArgs["smoothRepeat"])
            self.smoothRepeat_spn.setValue(val)
        if "minColor" in KArgs:
            val = float(KArgs["minColor"])
            self.minColor_sb.setValue(val)
        if "maxColor" in KArgs:
            val = float(KArgs["maxColor"])
            self.maxColor_sb.setValue(val)
        for att in self.listCheckBoxesDirectAction:
            if att in KArgs:
                val = bool(int(KArgs[att]))
                self.__dict__[att + "_cb"].setChecked(val)

    def clearInputText(self):
        self.searchInfluences_le.clear()

    """
    def updateMirrorCB (self):
        mirrorActive = self.brushFunctions.getBSDAttr ("mirrorActive")
        with toggleBlockSignals ([self.mirrorActive_cb]) : 
            self.mirrorActive_cb.setChecked (False)

    def toggleMirror (self, val):
        if val : 
            self.getMirrorInfluenceArray ()
        self.brushFunctions.setBSDAttr("mirrorActive",val)
    """

    def checkIfSameValue(self, val):
        attr = "mirrorActive"
        deleteTheJobs("SkinPaintWin.updateMirrorCB")

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
        # self.brushFunctions.setMirrorInfluences (driverNames_oppIndices)

    # --------------------------------------------------------------
    # artAttrSkinPaintCtx
    # --------------------------------------------------------------
    def pickMaxInfluence(self):
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, pickMaxInfluence=True)
            print ("pickMaxInfluence")

    def pickInfluence(self, vertexPicking=False):
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, pickInfluence=True)

    def selectedInfluences(self):
        return [item.influence() for item in self.uiInfluenceTREE.selectedItems()]

    def influenceDoubleClicked(self, item, column):
        txt = item._influence
        if cmds.objExists(txt):
            currentCursor = QtGui.QCursor().pos()
            autoHide = not self.showLocks_btn.isChecked()
            if column == 1:
                pos = self.uiInfluenceTREE.mapFromGlobal(currentCursor)
                if pos.x() > 40:
                    cmds.select(txt)
                else:
                    item.setLocked(not item.isLocked(), autoHide=autoHide)
                    if self.isInPaint():
                        cmds.brSkinBrushContext(
                            "brSkinBrushContext1", e=True, refreshDfmColor=item._index
                        )  # refresh lock color
            elif column == 0:
                pos = currentCursor - QtCore.QPoint(355, 100)
                self.colorDialog.item = item
                with toggleBlockSignals([self.colorDialog]):
                    self.colorDialog.cancelColor = QtGui.QColor(*item.color())
                    self.colorDialog.setCurrentColor(self.colorDialog.cancelColor)
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
        text = item._influence
        # print "CLICKED " + text
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", edit=True, influenceName=text)

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
            # self.brushFunctions.setBSDAttr ( "getLockWeights", True)
            self.refreshWeightEditor(getLocks=True)
        if self.isInPaint():
            cmds.brSkinBrushContext("brSkinBrushContext1", e=True, refresh=True)

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
            # self.brushFunctions.setInfluenceIndex (ind)
        """
        else : 
            inflInd = self.brushFunctions.getCurrentInfluence ()
            if inflInd !=-1 :
                with toggleBlockSignals ([self.uiInfluenceTREE]) : 
                    self.uiInfluenceTREE.setCurrentItem (self.uiInfluenceTREE.topLevelItem(inflInd))
        #    print "clear influence"
        """

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
                    foundText = re.search(txt, nm, re.IGNORECASE) is not None
                    if foundText:
                        break
                it.setHidden(not foundText)
        else:
            for nm, item in self.uiInfluenceTREE.dicWidgName.iteritems():
                item.setHidden(not self.showZeroDeformers and item.isZeroDfm)

    def refreshBtn(self):
        self.dataOfSkin = DataOfSkin(
            useShortestNames=self.useShortestNames, createDisplayLocator=False
        )
        self.dataOfSkin.softOn = False
        self.refresh(force=True)

    def selectRefresh(self):
        cmds.select(self.dataOfSkin.deformedShape)
        self.refresh(force=True)

    # def getHighestInfluence (self, vtxIndex) :
    #     highestDriver = np.argmax(self.dataOfSkin.raw2dArray [vtxIndex] )
    #     self.highestInfluence  = self.dataOfSkin.indicesJoints [highestDriver ]
    #     return self.dataOfSkin.driverNames [highestDriver]

    # def selectPickedInfluence (self) :
    #     if self.highestInfluence in self.dataOfSkin.indicesJoints:
    #         highestDriver = self.dataOfSkin.indicesJoints.index (self.highestInfluence)
    #         #print self.highestInfluence, highestDriver
    #         self.uiInfluenceTREE.setCurrentItem (self.uiInfluenceTREE.topLevelItem(highestDriver))

    def refreshColorsAndLocks(self):
        for i in range(self.uiInfluenceTREE.topLevelItemCount()):
            item = self.uiInfluenceTREE.topLevelItem(i)
            item.setDisplay()
            if item.currentColor != item.color():
                # we need a real update :
                ind = item._index
                item.currentColor = item.color()
                # self.brushFunctions.setColor (ind, item.currentColor)
                # print ind, item._influence
        # self.brushFunctions.setBSDAttr ( "getLockWeights", True)

    def refreshCallBack(self):
        if not self.lock_btn.isChecked():
            self.refresh()

    def refresh(self, force=False, renamedCalled=False):
        # print "refresh CALLED ", force
        with GlobalContext(message="paintEditor getAllData", doPrint=False):
            resultData = self.dataOfSkin.getAllData(
                displayLocator=False, getskinWeights=True, force=force
            )
            doForce = not resultData
            doForce = (
                doForce
                and cmds.objExists(self.dataOfSkin.deformedShape)
                and self.dataOfSkin.theDeformer == ""
            )
            doForce = doForce and cmds.nodeType(self.dataOfSkin.deformedShape) in [
                "mesh",
                "nurbsSurface",
            ]
            if doForce:
                self.dataOfSkin.clearData()
                force = True
        if renamedCalled or resultData or force:
            # print "- refreshing -"

            # self.brushFunctions.setColorsOnJoints ()
            # self.brushFunctions.bsd = self.dataOfSkin.getConnectedBlurskinDisplay ()
            self.uiInfluenceTREE.clear()
            self.uiInfluenceTREE.dicWidgName = {}

            if not hasattr(self.dataOfSkin, "shapePath"):
                return
            isPaintable = self.dataOfSkin.shapePath.apiType() == OpenMaya.MFn.kMesh
            for uiObj in [
                "options_widget",
                "buttonWidg",
                "widgetAbs",
                "valueSetter",
                "sizeBrushSetter",
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
            self.updateCurrentInfluence(self.previousInfluenceName)
        self.dgParallel_btn.setChecked(cmds.optionVar(q="evaluationMode") == 3)
        self.updateWarningBtn()
        self.showHideLocks(self.showLocks_btn.isChecked())

    def fixSparseArray(self):
        if self.isInPaint():
            mel.eval("setToolTo $gMove;")
        with GlobalContext(message="fix Sparse Array", doPrint=False):
            prevSelection = cmds.ls(sl=True)
            skn = self.dataOfSkin.theSkinCluster
            if skn and cmds.objExists(skn):
                reloadSkin(skn)
                self.refresh(force=True)
                cmds.select(prevSelection)

    def updateWarningBtn(self):
        skn = self.dataOfSkin.theSkinCluster
        if skn and cmds.objExists(skn):
            matIndices = cmds.getAttr("{}.matrix".format(skn), mi=True)
            sparseArray = len(matIndices) != max(matIndices) + 1
        else:
            sparseArray = False
        self.WarningFixSkin_btn.setVisible(sparseArray)

    def paintEnd(self):  # called by the brush
        for btnName in self.uiToActivateWithPaint:
            self.__dict__[btnName].setEnabled(False)
        self.uiInfluenceTREE.setStyleSheet("")
        self.previousInfluenceName = cmds.brSkinBrushContext(
            "brSkinBrushContext1", q=True, influenceName=True
        )
        # self.changeMultiSolo(-1)

    def paintStart(self):  # called by the brush
        for btnName in self.uiToActivateWithPaint:
            self.__dict__[btnName].setEnabled(True)
        self.uiInfluenceTREE.setStyleSheet("QWidget {border : 2px solid red}\n")
        # self.updateUIwithContextValues ()

        dicValues = {
            "edit": True,
            "soloColor": self.solo_rb.isChecked(),
            "soloColorType": self.soloColor_cb.currentIndex(),
            "size": self.sizeBrushSetter.theSpinner.value(),
            "strength": self.valueSetter.theSpinner.value() * 0.01,
            "commandIndex": self.getCommandIndex(),
            "useColorSetsWhilePainting": self.colorSets_rb.isChecked(),
            "smoothRepeat": self.smoothRepeat_spn.value(),
            "maxColor": self.maxColor_sb.value(),
            "minColor": self.minColor_sb.value(),
        }
        selectedInfluences = self.selectedInfluences()
        if selectedInfluences:
            dicValues["influenceName"] = selectedInfluences[0]
        for curveIndex, nm in enumerate(["curveNone", "curveLinear", "curveSmooth", "curveNarrow"]):
            thebtn = self.__dict__[nm + "_btn"]
            if thebtn.isChecked():
                dicValues["curve"] = curveIndex
                break
        for att in self.listCheckBoxesDirectAction:
            checkBox = self.__dict__[att + "_cb"]
            dicValues[att] = checkBox.isChecked()
        cmds.brSkinBrushContext("brSkinBrushContext1", **dicValues)
        # self.checkCorrectUI()

    # def checkCorrectUI(self):
    #     if self.isInPaint():
    #         #commandIndex = self.commandArray[newCommand]
    #         commandIndex = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, commandIndex=True)
    #         soloColor = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, soloColor=True)
    #         soloColorType = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, soloColorType=True)
    #         size = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, size=True)
    #         strength = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, strength=True)
    #         influenceName = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, influenceName=True)

    #         val = cmds.brSkinBrushContext("brSkinBrushContext1", query=True, useColorSetsWhilePainting=True)
    #         if val: self.colorSets_rb.setChecked(True)
    #         else: self.drawManager_rb.setChecked(True)

    #         for att in self.listCheckBoxesDirectAction:
    #             dic = {"edit": True}
    #             dic[att] = True
    #             val = cmds.brSkinBrushContext("brSkinBrushContext1", **dic)
    #             self.__dict__[att + "_cb"].setChecked(val)

    #         if soloColor: self.solo_rb.setChecked(True)
    #         else: self.multi_rb.setChecked(True)
    #         self.soloColor_cb.setCurrentIndex(soloColorType)

    #         self.updateSizeVal(size)
    #         self.updateStrengthVal(strength)
    #         nmBtn = self.commandArray[commandIndex] + "_btn"
    #         self.__dict__[nmBtn].setChecked(True)

    #         self.previousInfluenceName = influenceName
    #         self.updateCurrentInfluence(influenceName)


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
