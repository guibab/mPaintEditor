"""
pth = r'C:\Users\guillaume\Documents\DEV\Maya\cpp\blurSkin\testSetColors.py'
execfile (pth, globals(),  globals())
setColorsOnJoints ()
#setColorsOnSel ()
bsd = addColorNode () 
cmds.setAttr( bsd+".influenceIndex", 10)


enterPaint (bsd)
deleteTheJobs (toSearch = "function CallAfterPaint")
"""

from maya import cmds, mel
from functools import partial

# from dcc.maya import createMelProcedure
class BrushFunctions:
    def __init__(self, mainWindow=None):
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
        print msh, skinCluster
        print "doAddColorNode"
        cmds.setAttr(msh + ".displayColors", True)

        skinConn, inConn = cmds.listConnections(
            skinCluster + ".input[0].inputGeometry", s=True, d=False, p=True, c=True, scn=False
        )

        self.bsd = cmds.createNode("blurSkinDisplay")

        cmds.connectAttr(inConn, self.bsd + ".inMesh", f=True)
        cmds.connectAttr(self.bsd + ".outMesh", skinConn, f=True)

        cmds.evalDeferred(
            partial(cmds.connectAttr, self.bsd + ".weightList", skinCluster + ".weightList", f=True)
        )
        cmds.makePaintable(self.bsd, "paintAttr")

        return self.bsd

    def setPaintMode(self, mode):
        # 0 Add - 1 Remove - 2 AddPercent - 3 Absolute - 4 Smooth - 5 Sharpen - 6 Colors
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".command", mode)

    def setStampProfile(self, profile):
        cmds.artAttrCtx("artAttrContext", edit=True, stampProfile=profile)

    def togglePostSetting(self, val):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".postSetting", val)

    def setInfluenceIndex(self, infl):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".influenceIndex", infl)

    def setSmoothOptions(self, repeatVal, depthVal):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".smoothRepeat", repeatVal)
            cmds.setAttr(self.bsd + ".smoothDepth", depthVal)

    def callUndo(self):
        if cmds.objExists(self.bsd):
            cmds.setAttr(self.bsd + ".callUndo", True)

    def paintSkinOnProc(self):
        print "--- entering blur skin Paint -----"
        self.mainWindow.EVENTCATCHER.open()

    def paintSkinOffProc(self):
        print "--- exiting blur skin Paint -----"
        self.mainWindow.EVENTCATCHER.removeFilters()

    def enterPaint(self):
        self.deleteTheJobs(toSearch="function callAfterPaint")

        nbAtt = cmds.getAttr(self.bsd + ".wl", size=True)
        val = [0] * nbAtt
        cmds.setAttr(self.bsd + ".paintAttr", val, type="doubleArray")

        msh = cmds.ls(cmds.listHistory(self.bsd, af=True, f=True), type="mesh")[0]
        (prt,) = cmds.listRelatives(msh, p=True, path=True)

        sel = cmds.ls(sl=True)
        if prt not in sel:
            cmds.select(prt)
        mel.eval('artSetToolAndSelectAttr( "artAttrCtx", "{0}.paintAttr" );'.format(self.bsd))
        cmds.ArtPaintAttrTool()
        # fcProc = createMelProcedure(self.finalPaintBrush, [('int','slot')])
        # import __main__
        # __main__.applyCallBack = True
        self.createScriptJob()

        paintArgs = {
            "outline": True,
            "colorfeedback": False,
            "clamp": "both",
            "clamplower": 0.0,
            "clampupper": 1.0,
            "toolOnProc": 'python ("BLURpaintSkinOnProc()");',
            "toolOffProc": 'python ("BLURpaintSkinOffProc()");',
        }
        cmds.artAttrCtx(cmds.currentCtx(), edit=True, **paintArgs)

    def createScriptJob(self):
        theJob = cmds.scriptJob(
            runOnce=False, attributeChange=[self.bsd + ".paintAttr", self.callAfterPaint]
        )

    def deleteTheJobs(self, toSearch="BrushFunctions.callAfterPaint"):
        res = cmds.scriptJob(listJobs=True)
        for job in res:
            if toSearch in job:
                jobIndex = int(job.split(":")[0])
                cmds.scriptJob(kill=jobIndex)

    def callAfterPaint(self):
        # print "-- painting post --"
        currContext = cmds.currentCtx()
        if currContext == "artAttrContext":
            gArtAttrCurrentAttr = mel.eval("$tmp = $gArtAttrCurrentAttr")
            typeOfNode, node, attr = gArtAttrCurrentAttr.split(".")

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
                        print "RECONNECT WEIGHTLIST"
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
