from maya import cmds, mel
import re
import time
import datetime
from collections import OrderedDict
import random


from dcc.maya.skinCluster import getFastData
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
from pymel.core import PyNode

"""
import brSkinBrush_pythonFunctions
reload (brSkinBrush_pythonFunctions)
brSkinBrush_pythonFunctions.addWireFrameToMesh()

brSkinBrush_pythonFunctions.setColorsOnJoints ()


updateWireFrameColorSoloMode
"""
# To make your color choice reproducible, uncomment the following line:
# random.seed(10)


class disableUndoContext(object):
    """
    **CONTEXT** class (*use* ``with`` *statement*)
    """

    def __init__(self, raise_error=True, disableUndo=True, disableSoft=False):
        self.raise_error = raise_error
        self.disableUndo = disableUndo
        # self.disableSoft = disableSoft

    def __enter__(self):
        if self.disableUndo:
            cmds.undoInfo(state=False)
        # if self.disableSoft:
        #     cmds.softSelect(e=True, softSelectEnabled=False)
        #     self.isSoftSelect = cmds.softSelect(q=True, softSelectEnabled=True)
        # self.isSymetry = cmds.symmetricModelling(q=True, symmetry=True)
        # cmds.symmetricModelling(e=True, symmetry=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Turn refresh on again and raise errors if asked"""
        if self.disableUndo:
            cmds.undoInfo(state=True)
        # cmds.symmetricModelling(e=True, symmetry=self.isSymetry )
        # if self.disableSoft:
        #     cmds.softSelect(e=True, softSelectEnabled=self.isSoftSelect)


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


def setColorsOnJoints():
    _colors = []
    for i in xrange(1, 9):
        col = cmds.displayRGBColor("userDefined{0}".format(i), q=True)
        _colors.append(col)
    for jnt in cmds.ls(type="joint"):
        theInd = cmds.getAttr(jnt + ".objectColor")
        currentCol = cmds.getAttr(jnt + ".wireColorRGB")[0]
        if currentCol == (0.0, 0.0, 0.0):
            cmds.setAttr(jnt + ".wireColorRGB", *_colors[theInd])
        for destConn in (
            cmds.listConnections(
                jnt + ".objectColorRGB", d=True, s=False, p=True, type="skinCluster"
            )
            or []
        ):
            cmds.connectAttr(jnt + ".wireColorRGB", destConn, f=True)


def filterInfluences():
    items = cmds.treeView("brSkinBrushJointTree", query=True, children="")
    newText = cmds.textFieldGrp("brSkinBrushSearchField", query=True, text=True)
    hideLocked = cmds.checkBoxGrp("brSkinBrushHideLockCheck", q=True, value1=True)
    itemsState = [True] * len(items)
    newTexts = []
    if newText:
        newTexts = newText.split(" ")
        while "" in newTexts:
            newTexts.remove("")
    for i, nm in enumerate(items):
        isLocked = cmds.getAttr(nm + ".lockInfluenceWeights")

        showItem = not (isLocked and hideLocked)
        if showItem and newTexts:
            showItem = False
            for txt in newTexts:
                txt = txt.replace("*", ".*")
                showItem = re.search(txt, nm, re.IGNORECASE) != None
                if showItem:
                    break
        itemsState[i] = showItem
        cmds.treeView("brSkinBrushJointTree", edit=True, itemVisible=[nm, showItem])
    """
    else : 
        for nm , item in self.uiInfluenceTREE.dicWidgName.iteritems ():
            item.setHidden (not self.showZeroDeformers and item.isZeroDfm )
    """


def addInfluences():
    sel = cmds.ls(sl=True, tr=True)
    skn = cmds.brSkinBrushContext("brSkinBrushContext1", q=True, skinClusterName=True)

    deformedShape = cmds.skinCluster(skn, q=True, geometry=True)
    prt = (
        cmds.listRelatives(deformedShape, path=-True, parent=True)[0]
        if not cmds.nodeType(deformedShape) == "transform"
        else deformedShape
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
            cmds.skinCluster(skn, edit=True, lockWeights=False, weight=0.0, addInfluence=toAdd)
            """
            toSelect = range(self.uiInfluenceTREE.topLevelItemCount(), self.uiInfluenceTREE.topLevelItemCount()+len(toAdd))
            cmds.evalDeferred (self.selectRefresh)
            cmds.evalDeferred (partial (self.reselectIndices,toSelect))
            """


def removeUnusedInfluences(self):
    skn = cmds.brSkinBrushContext("brSkinBrushContext1", q=True, skinClusterName=True)

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


def doRemoveColorSets():
    msh = mel.eval("global string $gSkinBrushMesh; $tmp = $gSkinBrushMesh;")
    if cmds.objExists(msh):
        skinnedMesh_history = cmds.listHistory(msh, lv=0, pruneDagObjects=True) or []
        cmds.setAttr(msh + ".displayColors", 0)
    else:
        return
    while skinnedMesh_history:
        nd = skinnedMesh_history.pop(0)
        if cmds.nodeType(nd) != "createColorSet":
            break
        cmds.delete(nd)


def createWireframe(meshNode, hideOther=True, valAlpha=0.25):
    if hideOther:
        wireDisplay = cmds.listRelatives(meshNode, s=True, path=True, type="wireframeDisplay")
        if wireDisplay:
            cmds.hide(wireDisplay)
    meshes = cmds.listRelatives(meshNode, s=True, path=True, type="mesh")
    if not meshes:
        return None
    meshes = [shp for shp in meshes if not cmds.getAttr(shp + ".intermediateObject")]

    if cmds.objExists("SkinningWireframe"):
        cmds.delete("SkinningWireframe")
    prt = cmds.createNode("transform", n="SkinningWireframe", p=meshNode)
    # prt,=cmds.parent (prt, w=True)
    for msh in meshes:
        loc = cmds.createNode("wireframeDisplay", p=prt, n="SkinningWireframeShape")
        cmds.connectAttr(msh + ".outMesh", loc + ".inMesh", f=True)
        cmds.setAttr(loc + ".ihi", False)
    return prt


def getMeshTransfrom():
    currentContext = cmds.currentCtx()
    mshShape = cmds.brSkinBrushContext(currentContext, query=True, meshName=True)
    if mshShape and cmds.objExists(mshShape):
        (theMesh,) = cmds.listRelatives(mshShape, parent=True, path=True)
        return theMesh
    return None


def getShapesSelected(returnTransform=False):
    selectionShapes = cmds.ls(sl=True, o=True, type="mesh")
    if not selectionShapes:
        selection = cmds.ls(sl=True, tr=True) + cmds.ls(hilite=True)
        selectedMesh = cmds.listRelatives(selection, type="mesh")
        selectionShapes = cmds.ls(sl=True, o=True, type="mesh")
        if selectedMesh:
            selectionShapes += selectedMesh
        selectionShapes = [
            el for el in selectionShapes if not cmds.getAttr(el + ".intermediateObject")
        ]
    if selectionShapes and returnTransform:
        return cmds.listRelatives(selectionShapes, path=True, parent=True)
    return selectionShapes


def addLockVerticesAttribute():  # not used
    currentContext = cmds.currentCtx()
    mshShape = cmds.brSkinBrushContext(currentContext, query=True, meshName=True)
    if not cmds.attributeQuery("lockedVertices", node=mshShape, exists=True):
        cmds.addAttr(mshShape, longName="lockedVertices", dataType="Int32Array")


def addControllersToJoints():
    allJnts = cmds.ls(type="joint")
    for jnt in allJnts:
        if not cmds.listConnections(jnt, type="controller"):
            cmds.controller(jnt)


######################################################
# used by cpp tool to get the font size for display
def fnFonts(txt):
    from PySide2.QtGui import QFont, QFontMetrics

    sz = QFontMetrics(QFont("MS Shell Dlg 2", 14)).boundingRect(txt)
    return [sz.width() + 2, sz.height() + 2]


def toolOnSetupStart():
    cmds.optionVar(intValue=["startTime", time.time()])

    goodMode = "off"  # "serial" anmd "serialUncached" and "parallel" crashes
    if cmds.evaluationManager(q=True, mode=True) != [goodMode]:
        val = cmds.optionVar(q="evaluationMode")
        cmds.evaluationManager(mode=goodMode)
        cmds.optionVar(intValue=["revertParallelEvaluationMode", val])
    else:
        cmds.optionVar(intValue=["revertParallelEvaluationMode", 0])
        # cmds.optionVar(q="evaluationMode")
    cmds.optionVar(
        clearArray="colorShadedDisplay"
    )  # found that if not Shannon paint doesn't swap deformers
    cmds.optionVar(
        intValueAppend=["colorShadedDisplay", 1]
    )  # found that if not Shannon paint doesn't swap deformers
    cmds.optionVar(
        intValueAppend=["colorShadedDisplay", 1], intValue=["colorizeSkeleton", 1]
    )  # found that if not Shannon paint doesn't swap deformers
    # addControllersToJoints ()
    shapeSelected = getShapesSelected(returnTransform=True)
    if not shapeSelected:  # if nothing selected
        mshShape = mel.eval("global string $gSkinBrushMesh; $temp = $gSkinBrushMesh")
        # print mshShape
        if mshShape and cmds.objExists(mshShape):
            (theMesh,) = cmds.listRelatives(mshShape, parent=True, path=True)
            cmds.select(theMesh)
    else:
        cmds.select(shapeSelected)
    mshShapeSelected = getShapesSelected(returnTransform=False)
    # for colors
    for mshShape in mshShapeSelected:
        cmds.polyOptions(mshShape, colorShadedDisplay=True)
        # mshShape = "pCylinderShape3"
        if not cmds.attributeQuery("lockedVertices", node=mshShape, exists=True):
            cmds.addAttr(mshShape, longName="lockedVertices", dataType="Int32Array")
        cmds.setAttr(mshShape + ".colorSet", size=2)
        cmds.setAttr(mshShape + ".colorSet[0].colorName", "multiColorsSet", type="string")
        cmds.setAttr(mshShape + ".colorSet[1].colorName", "soloColorsSet", type="string")
        cmds.setAttr(mshShape + ".vertexColorSource", 2)
        cmds.setAttr(mshShape + ".displayColors", 1)
        # cmds.setAttr (mshShape +".backfaceCulling", 3)
    callEventCatcher()


def callEventCatcher():
    # print ("-- callEventCatcher --")
    # from mPaintEditor.brushTools import catchEventsUI
    import catchEventsUI

    # print catchEventsUI.__file__
    reload(catchEventsUI)
    catchEventsUI.EVENTCATCHER = catchEventsUI.CatchEventsWidget()
    catchEventsUI.EVENTCATCHER.open()


def closeEventCatcher():
    # print ("-- closeEventCatcher --")
    import catchEventsUI

    if hasattr(catchEventsUI, "EVENTCATCHER"):
        catchEventsUI.EVENTCATCHER.close()
    """
        mel.eval ("setToolTo $gMove;")
    """


def toolOnSetupEndDeferred():
    with disableUndoContext():
        addWireFrameToMesh()
        cmds.select(clear=True)
        currentContext = cmds.currentCtx()
        mshShape = cmds.brSkinBrushContext(currentContext, query=True, meshName=True)
        mel.eval('global string $gSkinBrushMesh; $gSkinBrushMesh="' + mshShape + '";')
        cmds.evalDeferred(doUpdateWireFrameColorSoloMode)
        # ------ compute time ----------------------------------
        startTime = cmds.optionVar(q="startTime")
        completionTime = time.time() - startTime
        timeRes = str(datetime.timedelta(seconds=int(completionTime))).split(":")
        # result = "{} hours {} mins {} secs".format (*timeRes)

        callPaintEditorFunction("paintStart")
        print "----- load BRUSH for {} in  [{:.2f} secs] ------".format(mshShape, completionTime)


def toolOnSetupEnd():
    toolOnSetupEndDeferred()
    # cmds.evalDeferred(toolOnSetupEndDeferred)


def toolOffCleanup():
    cmds.evalDeferred(toolOffCleanupDeferred)


def toolOffCleanupDeferred():
    # print "finishing tool\n"
    with disableUndoContext():
        closeEventCatcher()

        if cmds.objExists("SkinningWireframe"):
            cmds.delete("SkinningWireframe")
        # unhide previous wireFrames :
        theMesh = getMeshTransfrom()
        if theMesh:
            try:
                wireDisplay = cmds.listRelatives(
                    theMesh, s=True, path=True, type="wireframeDisplay"
                )
                if wireDisplay:
                    cmds.showHidden(wireDisplay)
            except RuntimeError:  # RuntimeError: Unknown object type: wireframeDisplay
                pass
        # delete colors on Q pressed
        doRemoveColorSets()
        cmds.evalDeferred(retrieveParallelMode)
        callPaintEditorFunction("paintEnd")


def retrieveParallelMode():
    val = cmds.optionVar(q="revertParallelEvaluationMode")
    if val != 0:
        cmds.optionVar(intValue=["revertParallelEvaluationMode", 0])
        mode = "parallel" if val == 3 else "serial"
        cmds.evaluationManager(mode=mode)


def escapePressed():
    doRemoveColorSets()


def addWireFrameToMesh():
    wireframeCB = callPaintEditorFunction("wireframe_cb")
    if wireframeCB and not wireframeCB.isChecked():
        print "no wireframe"
        return
    theMesh = cmds.ls(sl=True, tr=True)[0]  # getMeshTransfrom()
    # print currentContext, theMesh
    createWireframe(theMesh)


def updateWireFrameColorSoloMode(soloColor):
    ctx = cmds.currentCtx()
    # soloColor = cmds.brSkinBrushContext (ctx, q=True, soloColor=True  )
    if cmds.objExists("SkinningWireframeShape"):
        if not soloColor:
            overrideColorRGB = [0.1, 0.1, 0.1]
        else:
            overrideColorRGB = [0.8, 0.8, 0.8]
        cmds.setAttr("SkinningWireframeShape.overrideEnabled", 1)
        cmds.setAttr("SkinningWireframeShape.overrideRGBColors", 1)
        cmds.setAttr("SkinningWireframeShape.overrideColorRGB", *overrideColorRGB)


def doUpdateWireFrameColorSoloMode():
    currentContext = cmds.currentCtx()
    soloColor = cmds.brSkinBrushContext(currentContext, q=True, soloColor=True)
    updateWireFrameColorSoloMode(soloColor)


def setSoloMode(soloColor):
    ctx = cmds.currentCtx()
    cmds.brSkinBrushContext(ctx, e=True, soloColor=soloColor)
    updateWireFrameColorSoloMode(soloColor)


def toggleSoloMode():
    # print "brSkinBrush_pythonFunctions  toggleSoloMode "
    ctx = cmds.currentCtx()
    soloColor = cmds.brSkinBrushContext(ctx, q=True, soloColor=True)
    setSoloMode(not soloColor)
    callPaintEditorFunction("upateSoloModeRBs", not soloColor)


def fixOptionVarContext(**inputKargsToChange):
    kwargs = OrderedDict()
    if cmds.optionVar(exists="brSkinBrushContext1"):
        cmd = cmds.optionVar(q="brSkinBrushContext1")
        # remove command name and command object at the end : brSkinBrushContext anmd brSkinBrushContext1;
        splitofspaces = cmd.split(" ")
        cmd2 = " ".join(splitofspaces[1:-1])
        spl = cmd2.split("-")
        hlp = cmds.help("brSkinBrushContext")

        dicOfName = {}
        dicExpectedArgs = {}
        lsMulti = set()
        for ln in hlp.split("\n"):
            for expectedStuff in [
                "(Query Arg Mandatory)",
                "(Query Arg Optional)",
                "[...]",
                "(Query Arg Optional)",
            ]:
                ln = ln.replace(expectedStuff, "")
            ln = ln.strip()
            res = ln.split()
            if len(res) >= 2 and res[0].startswith("-") and res[1].startswith("-"):
                nmFlag = res[1][1:]
                dicOfName[res[0][1:]] = nmFlag
                dicOfName[res[1][1:]] = nmFlag
                if "(multi-use)" in res:
                    lsMulti.add(nmFlag)
                    res.remove("(multi-use)")
                finishVal = res[2:]
                dicExpectedArgs[nmFlag] = res[2:]
        newSpl = []
        for lne in spl:
            lineSplit = lne.strip().split(" ")

            if len(lineSplit) > 1:
                kArg = "-" + lineSplit[0]
                if kArg not in hlp:
                    continue
                else:
                    value = " ".join(lineSplit[1:])
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    kwargs[dicOfName[lineSplit[0]]] = value
            else:
                if lineSplit[0] in dicOfName:
                    kwargs[dicOfName[lineSplit[0]]] = True
            newSpl.append(lne)
        # now rebuild command ---------------------------------
        kwargs.update(inputKargsToChange)
        cmdNew = "brSkinBrushContext "
        for key, value in kwargs.iteritems():
            if isinstance(value, bool):
                cmdNew += "-{} ".format(key)
            else:
                try:
                    float(value)
                    cmdNew += "-{} {} ".format(key, value)
                except ValueError:
                    cmdNew += '-{} "{}" '.format(key, value)
        cmdNew += splitofspaces[-1]
        # cmdNew = "brSkinBrushContext -" + "-".join(newSpl)
        cmds.optionVar(stringValue=["brSkinBrushContext1", cmdNew])
    return kwargs


def deleteExistingColorSets():
    sel = cmds.ls(sl=True)
    for obj in sel:
        existingColorSets = cmds.polyColorSet(obj, q=True, allColorSets=True) or []
        for colSet in ["multiColorsSet", "multiColorsSet2", "soloColorsSet", "soloColorsSet2"]:
            if colSet in existingColorSets:
                cmds.polyColorSet(obj, delete=True, colorSet=colSet)


"""
matIndices =cmds.getAttr ("{}.matrix".format (newSkinName), mi=True) 
len (matIndices ) != max (matIndices )+1
"""


def reloadSkin(skinClusterName):
    sknFn, shapePath, fullComponent, nbDrivers, influencesIndices = getFastData(
        skinClusterName, indices=None, shapePathIndex=0
    )
    weights = om.MDoubleArray()

    intptrUtil = om.MScriptUtil()
    intptrUtil.createFromInt(0)
    intPtr = intptrUtil.asUintPtr()

    sknFn.getWeights(shapePath, fullComponent, weights, intPtr)

    listBindPreMat = {}
    listInfluenceColor = {}
    for influenceName, influencesIndex in influencesIndices.iteritems():
        bindPreAtt = "{}.bindPreMatrix[{}]".format(skinClusterName, influencesIndex)
        bindPreConn = cmds.listConnections(bindPreAtt, s=True, d=False, p=True)
        if bindPreConn:
            listBindPreMat[influenceName] = bindPreConn[0]
        else:
            listBindPreMat[influenceName] = PyNode(bindPreAtt).get()
        influenceColorAtt = "{}.influenceColor[{}]".format(skinClusterName, influencesIndex)
        influenceColorConn = cmds.listConnections(influenceColorAtt, s=True, d=False, p=True)
        if influenceColorConn:
            listInfluenceColor[influenceName] = influenceColorConn[0]
        else:
            listInfluenceColor[influenceName] = PyNode(influenceColorAtt).get()
    geometries = cmds.skinCluster(skinClusterName, q=True, geometry=True)
    lstInfluences = cmds.skinCluster(skinClusterName, q=True, influence=True)

    # that's the get part------------------------------------------

    cmds.delete(skinClusterName)
    # recreate the skin -----------------------------------
    newSkinName = cmds.skinCluster(
        lstInfluences + geometries, toSelectedBones=True, includeHiddenSelections=False
    )[0]
    sknFnNew, shapePathNew, fullComponentNew, nbDriversNew, influencesIndicesNew = getFastData(
        newSkinName, indices=None, shapePathIndex=0
    )

    # reset the weights
    undoValues = om.MDoubleArray()
    tmpInflInd = range(len(lstInfluences))
    tmpInflInd = om.MIntArray(len(lstInfluences))
    for i in range(len(lstInfluences)):
        tmpInflInd.set(i, i)
    sknFnNew.setWeights(shapePathNew, fullComponentNew, tmpInflInd, weights, False, undoValues)

    # reconnect the Atts -----------------------
    for influenceName, influencesIndex in influencesIndicesNew.iteritems():
        bindPreAtt = "{}.bindPreMatrix[{}]".format(newSkinName, influencesIndex)
        bindPreValue = listBindPreMat[influenceName]
        if isinstance(bindPreValue, unicode):
            cmds.connectAttr(bindPreValue, bindPreAtt, f=True)
        else:
            PyNode(bindPreAtt).set(bindPreValue)
        influenceColorAtt = "{}.influenceColor[{}]".format(newSkinName, influencesIndex)
        influenceColorValue = listInfluenceColor[influenceName]

        if not isinstance(influenceColorValue, unicode):
            PyNode(influenceColorAtt).set(influenceColorValue)


######################### --------------CALL FROM BRUSH------------------------- ###############################################


def getPaintEditor():
    import __main__

    if hasattr(__main__, "paintEditor") and __main__.paintEditor.isVisible():
        return __main__.paintEditor
    return None


def callPaintEditorFunction(function, *args, **kwargs):
    paintEditor = getPaintEditor()
    if paintEditor and hasattr(paintEditor, function):
        fn = getattr(paintEditor, function)
        if callable(fn):
            return fn(*args, **kwargs)
        else:
            return fn
    return None


def headsUpMessage(offsetX, offsetY, message, valueDisplay, precision):
    theMessage = "{}: {:.{}f}".format(message, valueDisplay, precision)
    cmds.headsUpMessage(theMessage, horizontalOffset=offsetX, verticalOffset=offsetY, time=0.1)


def pickedInfluence(jointName):
    # print "pickedInfluence from python 2.0"
    if cmds.treeView("brSkinBrushJointTree", q=True, ex=True):
        cmds.treeView("brSkinBrushJointTree", edit=True, clearSelection=True)
        cmds.treeView("brSkinBrushJointTree", edit=True, showItem=jointName)
        mel.eval(
            'global string $gSkinBrushInfluenceSelection[];    $gSkinBrushInfluenceSelection = { "'
            + jointName
            + '" };'
        )
    callPaintEditorFunction("updateCurrentInfluence", jointName)


def updateDisplayStrengthOrSize(sizeAdjust, value):
    fsg = "brSkinBrushSize" if sizeAdjust else "brSkinBrushStrength"
    if cmds.floatSliderGrp(fsg, q=True, ex=True):
        cmds.floatSliderGrp(fsg, e=True, value=value)
    if sizeAdjust:
        callPaintEditorFunction("updateSizeVal", value)
    else:
        callPaintEditorFunction("updateStrengthVal", value)


"""
jnt = "Model:Dfm_L_Clavicle_1"
CTR = cmds.createNode( "controller", name="TMPcontrollerFORPAINTSKIN")
cmds.connectAttr( jnt+".msg", CTR+".act")

createNode controller -n "TESTcontroller";
connectAttr "joint3.msg" "TESTcontroller.act";
"""
