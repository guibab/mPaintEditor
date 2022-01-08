from __future__ import print_function
from __future__ import absolute_import
from maya import cmds, OpenMaya as om, OpenMayaAnim as oma
import six
from six.moves import range
from six.moves import zip


def getThreeIndices(div_s, div_t, div_u, *args):
    if len(args) == 1:
        (simpleIndex,) = args
        s = simpleIndex % div_s
        t = (simpleIndex - s) / div_s % div_t
        u = (simpleIndex - s - t * div_s) / (div_s * div_t)
        return s, t, u
    elif len(args) == 3:
        s, t, u = args
        simpleIndex = u * div_s * div_t + t * div_s + s
        return simpleIndex


def getFastData(skinClusterName, indices=None, shapePathIndex=0):
    selList = om.MSelectionList()
    om.MGlobal.getSelectionListByName(skinClusterName, selList)
    depNode = om.MObject()
    selList.getDependNode(0, depNode)
    sknFn = oma.MFnSkinCluster(depNode)

    ###################################
    jointPaths = om.MDagPathArray()
    sknFn.influenceObjects(jointPaths)
    nbDrivers = jointPaths.length()

    influencesIndices = {}
    for i in range(nbDrivers):
        influenceFn = om.MFnDependencyNode(jointPaths[i].node())
        ind = sknFn.indexForInfluenceObject(jointPaths[i])
        influencesIndices[influenceFn.name()] = ind

    shapePath = om.MDagPath()
    sknFn.getPathAtIndex(shapePathIndex, shapePath)
    shapeName = shapePath.fullPathName()
    vertexCount = 0

    fnComponent = om.MFnSingleIndexedComponent()
    componentAlreadyBuild = False

    if shapePath.apiType() == om.MFn.kNurbsCurve:
        componentType = om.MFn.kCurveCVComponent
        crvFn = om.MFnNurbsCurve(shapePath)
        vertexCount = crvFn.numCVs()

    elif shapePath.apiType() == om.MFn.kNurbsSurface:
        componentAlreadyBuild = True
        componentType = om.MFn.kSurfaceCVComponent
        MfnSurface = om.MFnNurbsSurface(shapePath)
        numCVsInV_ = MfnSurface.numCVsInV()
        numCVsInU_ = MfnSurface.numCVsInU()
        fnComponent = om.MFnDoubleIndexedComponent()
        fullComponent = fnComponent.create(componentType)
        if not indices:
            fnComponent.setCompleteData(numCVsInU_, numCVsInV_)
        else:
            for indVtx in indices:
                indexV = indVtx % numCVsInV_
                indexU = indVtx / numCVsInV_
                fnComponent.addElement(indexU, indexV)

    elif shapePath.apiType() == om.MFn.kLattice:  # lattice
        componentAlreadyBuild = True
        componentType = om.MFn.kLatticeComponent
        fnComponent = om.MFnTripleIndexedComponent()
        fullComponent = fnComponent.create(componentType)
        div_s = cmds.getAttr(shapeName + ".sDivisions")
        div_t = cmds.getAttr(shapeName + ".tDivisions")
        div_u = cmds.getAttr(shapeName + ".uDivisions")
        if not indices:
            fnComponent.setCompleteData(div_s, div_t, div_u)
        else:
            for indVtx in indices:
                s, t, v = getThreeIndices(div_s, div_t, div_u, indVtx)
                fnComponent.addElement(s, t, v)

    elif shapePath.apiType() == om.MFn.kMesh:  # mesh
        componentType = om.MFn.kMeshVertComponent
        mshFn = om.MFnMesh(shapePath)
        vertexCount = mshFn.numVertices()
    else:
        return None

    if not componentAlreadyBuild:  # for mesh and nurbsCurve
        fullComponent = fnComponent.create(componentType)
        if not indices:
            fnComponent.setCompleteData(vertexCount)
        else:
            for ind in indices:
                fnComponent.addElement(ind)

    return sknFn, shapePath, fullComponent, nbDrivers, influencesIndices


def skinClusterHasSparceArray(skinClusterName):
    matIndices = (
        cmds.getAttr("{}.matrix".format(skinClusterName), multiIndices=True) or []
    )
    return len(matIndices) != max(matIndices) + 1


def reloadSkin(skinClusterName, newGeometrie=None, resetBindAtt=True):
    """
    reloadingSkincluster fixes sparce array problem
    """
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
    for influenceName, influencesIndex in six.iteritems(influencesIndices):
        bindPreAtt = "{}.bindPreMatrix[{}]".format(skinClusterName, influencesIndex)
        bindPreConn = cmds.listConnections(bindPreAtt, s=True, d=False, p=True)
        if bindPreConn:
            listBindPreMat[influenceName] = bindPreConn[0]
        else:
            listBindPreMat[influenceName] = cmds.getAttr(bindPreAtt)

        influenceColorAtt = "{}.influenceColor[{}]".format(
            skinClusterName, influencesIndex
        )
        influenceColorConn = cmds.listConnections(
            influenceColorAtt, s=True, d=False, p=True
        )
        if influenceColorConn:
            listInfluenceColor[influenceName] = influenceColorConn[0]
        else:
            listInfluenceColor[influenceName] = cmds.getAttr(influenceColorAtt)

    geometries = cmds.skinCluster(skinClusterName, q=True, geometry=True)
    lstInfluences = cmds.skinCluster(skinClusterName, q=True, influence=True)
    deformerList = cmds.ls(
        cmds.listHistory(geometries, lv=0, pruneDagObjects=True), type="geometryFilter"
    )
    # that's the get part------------------------------------------
    if not newGeometrie:
        cmds.delete(skinClusterName)
        newGeometries = geometries
    else:
        newGeometries = [newGeometrie]
    # recreate the skin -----------------------------------
    prevTweaks = cmds.ls(type="tweak")
    valRetrieve = []
    for att in [".lodVisibility", ".visibility", ".overrideVisibility"]:
        fullAtt = newGeometries[0] + att
        val = cmds.getAttr(fullAtt)
        if not val:
            valRetrieve.append(fullAtt)
            cmds.setAttr(fullAtt, True)

    try:
        newSkinName = cmds.skinCluster(
            lstInfluences + newGeometries,
            toSelectedBones=True,
            includeHiddenSelections=False,
        )[0]
    except RuntimeError as errorMessage:
        if errorMessage.message.endswith(" is already connected to a skinCluster\n"):
            (prt,) = cmds.listRelatives(geometries, parent=True, path=True)
            origShapes = set(cmds.listRelatives(prt, path=True, shapes=True)) - set(
                cmds.listRelatives(prt, path=True, shapes=True, noIntermediate=True)
            )
            inConns = []
            for shp in origShapes:
                inConns.extend(
                    cmds.listConnections(shp, s=True, d=False, p=True, c=True)
                )
            for mast, slave in zip(inConns[1::2], inConns[0::2]):
                cmds.disconnectAttr(mast, slave)
            newSkinName = cmds.skinCluster(
                lstInfluences + newGeometries,
                toSelectedBones=True,
                includeHiddenSelections=False,
            )[0]
            for mast, slave in zip(inConns[1::2], inConns[0::2]):
                cmds.connectAttr(mast, slave)
        else:
            print(errorMessage)

    for fullAtt in valRetrieve:
        cmds.setAttr(fullAtt, False)

    (
        sknFnNew,
        shapePathNew,
        fullComponentNew,
        nbDriversNew,
        influencesIndicesNew,
    ) = getFastData(newSkinName, indices=None, shapePathIndex=0)
    postTweaks = cmds.ls(type="tweak")
    createdTweaks = set(postTweaks) - set(prevTweaks)
    if createdTweaks:
        cmds.delete(list(createdTweaks))

    # reset the weights
    undoValues = om.MDoubleArray()
    tmpInflInd = list(range(len(lstInfluences)))
    tmpInflInd = om.MIntArray(len(lstInfluences))
    for i in range(len(lstInfluences)):
        tmpInflInd.set(i, i)
    sknFnNew.setWeights(
        shapePathNew, fullComponentNew, tmpInflInd, weights, False, undoValues
    )

    # reconnect the Atts -----------------------
    for influenceName, influencesIndex in six.iteritems(influencesIndicesNew):
        bindPreAtt = "{}.bindPreMatrix[{}]".format(newSkinName, influencesIndex)
        bindPreValue = listBindPreMat[influenceName]
        if isinstance(bindPreValue, six.string_types):
            cmds.connectAttr(bindPreValue, bindPreAtt, f=True)
        elif resetBindAtt:
            cmds.setAttr(bindPreAtt, bindPreValue, typ="matrix")

        influenceColorAtt = "{}.influenceColor[{}]".format(newSkinName, influencesIndex)
        influenceColorValue = listInfluenceColor[influenceName]

        if not isinstance(influenceColorValue, six.string_types):
            cmds.setAttr(influenceColorAtt, *influenceColorValue, type="float3")
    # rename ----------------------
    cmds.rename(newSkinName, skinClusterName)

    newDeformerList = cmds.ls(
        cmds.listHistory(geometries, lv=0, pruneDagObjects=True), type="geometryFilter"
    )
    if newDeformerList != deformerList:
        oldInd = deformerList.index(skinClusterName)
        if oldInd != 0:
            nextDfm = deformerList[oldInd - 1]
            cmds.reorderDeformers(nextDfm, skinClusterName, geometries[0])
