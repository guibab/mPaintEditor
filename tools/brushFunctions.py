from maya import cmds, mel
from functools import partial
import os
from mWeightEditor.tools.utils import deleteTheJobs

# from dcc.maya import createMelProcedure


class BrushFunctions:
    verbose = False

    def __init__(self, mainWindow=None, thePaintContextName="artAttrContext"):
        self.thePaintContextName = thePaintContextName
        self.mainWindow = mainWindow
        self.bsd = ""
        mel.eval("source artAttrCreateMenuItems.mel")
        if not cmds.pluginInfo("blurSkin", query=True, loaded=True):
            cmds.loadPlugin("blurSkin")
        cmds.makePaintable("blurSkinDisplay", "paintAttr")
        import __main__

        __main__.BLURpaintSkinOnProc = self.paintSkinOnProc
        __main__.BLURpaintSkinOffProc = self.paintSkinOffProc

    def setColorsOnJoints(self):
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

    def setColorsOnSel(self):
        sel = cmds.ls(sl=True, tr=True)
        msh = cmds.listRelatives(sel, type="mesh")
        cmds.blurSkinCmd(command="colors", meshName=msh[0], verbose=False)

    def addColorNode(self):
        sel = cmds.ls(sl=True, tr=True)
        msh = cmds.listRelatives(sel, type="mesh")

        hist = cmds.listHistory(sel, lv=0, pruneDagObjects=True)
        if hist:
            skinClusters = cmds.ls(hist, type="skinCluster")
            if skinClusters:
                skinCluster = skinClusters[0]
                return self.doAddColorNode(msh[0], skinCluster)
        return ""

    def doAddColorNode(self, msh, skinCluster):
        # print msh, skinCluster
        # print "doAddColorNode"
        cmds.setAttr(msh + ".displayColors", True)
        """
        inConnection = cmds.listConnections (skinCluster+".input[0].inputGeometry", s=True, d=False)
        if cmds.nodeType (inConnection[0]) == "groupParts" : 
            skinConn, inConn = cmds.listConnections (inConnection[0]+".ig", s=True, d=False, c=True, p=True)
        else : 
            skinConn, inConn = cmds.listConnections (skinCluster+".input[0].inputGeometry", s=True, d=False, p=True, c=True, scn=True)
        """
        skinConn, inConn = cmds.listConnections(
            skinCluster + ".input[0].inputGeometry", s=True, d=False, p=True, c=True, scn=False
        )

        self.bsd = cmds.createNode("blurSkinDisplay")

        cmds.connectAttr(inConn, self.bsd + ".inMesh", f=True)
        cmds.connectAttr(self.bsd + ".outMesh", skinConn, f=True)

        # cmds.evalDeferred  (partial (cmds.connectAttr, self.bsd+".weightList", skinCluster+".weightList", f=True))
        cmds.makePaintable(self.bsd, "paintAttr")

        return self.bsd

    def setPaintMode(self, mode):
        # 0 Add - 1 Remove - 2 AddPercent - 3 Absolute - 4 Smooth - 5 Sharpen - 6 Colors
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".command", mode)

    def setStampProfile(self, profile):
        cmds.artAttrCtx(self.thePaintContextName, edit=True, stampProfile=profile)

    def togglePostSetting(self, val):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".postSetting", val)

    def deleteNode(self):
        if cmds.objExists(self.bsd):
            cmds.delete(self.bsd)

    def setInfluenceIndex(self, infl):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".influenceIndex", infl)

    def getCurrentInfluence(self):
        if cmds.objExists(self.bsd):
            return cmds.getAttr(self.bsd + ".influenceIndex")
        else:
            return -1

    def setColor(self, index, col):
        if cmds.objExists(self.bsd):
            cmds.setAttr("{0}.influenceColor[{1}]".format(self.bsd, index), *col)

    def setBSDAttr(self, attr, val):
        # print attr, val
        if cmds.objExists(self.bsd) and cmds.attributeQuery(attr, node=self.bsd, exists=True):
            cmds.setAttr(self.bsd + "." + attr, val)

    def getBSDAttr(self, attr):
        # print attr, val
        if cmds.objExists(self.bsd) and cmds.attributeQuery(attr, node=self.bsd, exists=True):
            return cmds.getAttr(self.bsd + "." + attr)

    def setSmoothOptions(self, repeatVal, depthVal):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".smoothRepeat", repeatVal)
            cmds.setAttr(self.bsd + ".smoothDepth", depthVal)

    def setMirrorInfluences(self, driverNames_oppIndices):
        if cmds.objExists(self.bsd):
            cmds.setAttr(
                self.bsd + ".mirrorInfluenceArray", driverNames_oppIndices, type="Int32Array"
            )

    def callUndo(self):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".callUndo", True)

    def paintSkinOnProc(self):
        # print "--- entering blur skin Paint -----"
        self.createScriptJob()
        self.mainWindow.paintStart()

    def paintSkinOffProc(self):
        # print "--- exiting blur skin Paint -----"
        self.mainWindow.paintEnd()

    def enterPaint(self):
        self.callAfterPaint()

        nbAtt = cmds.getAttr(self.bsd + ".wl", size=True)
        val = [0] * nbAtt
        cmds.setAttr(self.bsd + ".paintAttr", val, type="doubleArray")

        msh = cmds.ls(cmds.listHistory(self.bsd, af=True, f=True), type="mesh")[0]

        cmds.setAttr(msh + ".displayColorChannel", "Diffuse", type="string")
        cmds.setAttr(msh + ".materialBlend", 0)

        (prt,) = cmds.listRelatives(msh, p=True, path=True)

        sel = cmds.ls(sl=True)
        if prt not in sel:
            cmds.select(prt)
        mel.eval(
            'artSetToolAndSelectAttr( "{1}", "{0}.paintAttr" );'.format(
                self.bsd, self.thePaintContextName
            )
        )
        # cmds.ArtPaintAttrTool ()

        # fcProc = createMelProcedure(self.finalPaintBrush, [('int','slot')])
        # import __main__
        # __main__.applyCallBack = True
        fileVar = os.path.realpath(__file__)
        uiFolder, filename = os.path.split(fileVar)
        iconPth = os.path.join(uiFolder[:-6], "img", "icon.png")
        # print iconPth

        paintArgs = {
            "outline": True,
            "colorfeedback": False,
            "clamp": "both",
            "clamplower": 0.0,
            "clampupper": 1.0,
            "image1": iconPth,
            "toolOnProc": 'python ("BLURpaintSkinOnProc()");',
            "toolOffProc": 'python ("BLURpaintSkinOffProc()");',
        }

        cmds.artAttrCtx(self.thePaintContextName, edit=True, **paintArgs)
        cmds.setToolTo(self.thePaintContextName)

    def createScriptJob(self):
        deleteTheJobs(toSearch="BrushFunctions.callAfterPaint")
        if cmds.objExists(self.bsd + ".paintAttr"):
            theJob = cmds.scriptJob(
                runOnce=False, attributeChange=[self.bsd + ".paintAttr", self.callAfterPaint]
            )

    def callAfterPaint(self):
        currContext = cmds.currentCtx()
        # print "-- painting post -- ", currContext
        if currContext == self.thePaintContextName:
            gArtAttrCurrentAttr = mel.eval("$tmp = $gArtAttrCurrentAttr")
            typeOfNode, node, attr = gArtAttrCurrentAttr.split(".")
            # print "data " + typeOfNode,node,attr
            arrayValues = cmds.getAttr(node + "." + attr)
            # check the values ---------------
            doSetCommand = False
            for ind, val in enumerate(arrayValues):
                if val > 0.0:
                    doSetCommand = True
                    break
            if doSetCommand:
                zeroValues = [0] * len(arrayValues)
                # set values at zero
                cmds.setAttr(node + "." + attr, zeroValues, type="doubleArray")
                if cmds.nodeType(node) == "blurSkinDisplay":
                    cmds.evalDeferred(partial(cmds.setAttr, node + ".clearArray", 1))
                    # reconnect :
                    outConn = cmds.listConnections(node + ".wl", s=False, d=True)
                    if not outConn:
                        print "RECONNECT WEIGHTLIST from callAfterPaint - scriptJob"
                        outMeshConn = cmds.listConnections(
                            node + ".outMesh", s=False, d=True, type="skinCluster"
                        )
                        cmds.connectAttr(
                            node + ".weightList", outMeshConn[0] + ".weightList", f=True
                        )

    def finalPaintBrush(self, slot):
        print "FINAL Brush"

    def clearPaint(self):
        nbAtt = cmds.getAttr(self.bsd + ".wl", size=True)
        val = [0] * nbAtt
        cmds.setAttr(self.bsd + ".paintAttr", val, type="doubleArray")

        """
        currContext = cmds.currentCtx()
        val = cmds.artAttrCtx( currContext, query=True,value =True )        
        cmds.artAttrCtx( currContext, edit=True,value =0.0)
        cmds.artAttrCtx( currContext, edit=True, clear=True )
        cmds.artAttrCtx( currContext, edit=True,value =val)
        """
        # cmds.setAttr (self.bsd+".clearArray", 1)
        cmds.evalDeferred(partial(cmds.setAttr, self.bsd + ".clearArray", 1))
