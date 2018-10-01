from Qt import QtGui, QtCore, QtWidgets
from Qt import QtCompat
from Qt.QtWidgets import QApplication, QSplashScreen, QDialog, QMainWindow
from maya import OpenMaya, OpenMayaUI, OpenMayaAnim, cmds, mel
from functools import partial
import os
from mWeightEditor.tools.utils import GlobalContext


def callMarkingMenu():
    if cmds.popupMenu("tempMM", exists=True):
        cmds.deleteUI("tempMM")

    res = mel.eval("findPanelPopupParent")
    cmds.popupMenu(
        "tempMM",
        button=1,
        ctrlModifier=False,
        altModifier=False,
        allowOptionBoxes=True,
        parent=res,
        markingMenu=True,
    )

    kwArgs = {
        "label": "add",
        "divider": False,
        "subMenu": False,
        "tearOff": False,
        "optionBox": False,
        "enable": True,
        "data": 0,
        "allowOptionBoxes": True,
        "postMenuCommandOnce": False,
        "enableCommandRepeat": True,
        "echoCommand": False,
        "italicized": False,
        "boldFont": True,
        "sourceType": "mel",
        "longDivider": True,
    }

    lstCommands = [
        ("add", "N", "add"),
        ("smooth", "W", "smooth"),
        ("absolute", "E", "abs"),
        ("addPercent", "NW", "addPerc"),
        ("remove", "S", "rmv"),
        ("locks Verts", "SE", "locks"),
    ]
    for ind, (txt, posi, btn) in enumerate(lstCommands):
        kwArgs["radialPosition"] = posi
        kwArgs["label"] = txt
        kwArgs["command"] = 'python("import __main__;__main__.paintEditor.' + btn + '_btn.click()")'
        # kwArgs ["command"] =  "print \"hi\""
        cmds.menuItem("menuEditorMenuItem{0}".format(ind + 1), **kwArgs)
    kwArgs.pop("radialPosition", None)
    kwArgs["label"] = "solo color"
    kwArgs["subMenu"] = True

    cmds.menuItem("menuEditorMenuItem{0}".format(len(lstCommands) + 1), **kwArgs)
    kwArgs["subMenu"] = False
    for ind, colType in enumerate(["white", "lava", "influence"]):
        kwArgs["label"] = colType
        kwArgs["command"] = (
            'python("import __main__;__main__.paintEditor.updateSoloColor (' + str(ind) + ')")'
        )
        cmds.menuItem("menuEditorMenuItemCol{0}".format(ind + 1), **kwArgs)
    mel.eval("setParent -menu ..;")
    # setParent -menu
    mel.eval("setParent -menu ..;")


def rootWindow():
    """
    Returns the currently active QT main window
    Only works for QT UI's like Maya
    """
    # for MFC apps there should be no root window
    window = None
    if QApplication.instance():
        inst = QApplication.instance()
        window = inst.activeWindow()
        # Ignore QSplashScreen's, they should never be considered the root window.
        if isinstance(window, QSplashScreen):
            return None
        # If the application does not have focus try to find A top level widget
        # that doesn't have a parent and is a QMainWindow or QDialog
        if window == None:
            windows = []
            dialogs = []
            for w in QApplication.instance().topLevelWidgets():
                if w.parent() == None:
                    if isinstance(w, QMainWindow):
                        windows.append(w)
                    elif isinstance(w, QDialog):
                        dialogs.append(w)
            if windows:
                window = windows[0]
            elif dialogs:
                window = dialogs[0]
        # grab the root window
        if window:
            while True:
                parent = window.parent()
                if not parent:
                    break
                if isinstance(parent, QSplashScreen):
                    break
                window = parent
    return window


class LabelDisplayInfluence(QtWidgets.QLabel):
    def __init__(self):
        super(LabelDisplayInfluence, self).__init__(rootWindow())
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint
        )  # (QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        self.currentText = ""
        self.radiusIntersect = 10  # select from screen
        self.setStyleSheet(
            "margin-left: 0px; border-radius: 25px; background: yellow; color: black; border: 1px solid black;"
        )
        # self.setFont (self._font)

    def drawText(self, txt):
        if self.currentText != txt:
            self.setText(txt)
            sz = self.fontMetrics().boundingRect(txt).size() + QtCore.QSize(10, 4)
            # sz = self.fontMetrics().size(QtCore.Qt.TextSingleLine,txt)
            self.resize(sz)
            self.currentText = txt
        # self.setAttribute (QtCore.Qt.WA_MouseNoMask, True)

    def getMeshFn(self, nodeName):
        # We expect here the fullPath of a shape mesh
        selList = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getSelectionListByName(nodeName, selList)
        depNode = OpenMaya.MObject()
        selList.getDependNode(0, depNode)

        mshPath = OpenMaya.MDagPath()
        selList.getDagPath(0, mshPath, depNode)
        meshFn = OpenMaya.MFnMesh(mshPath)

        return meshFn

    def mousePressEvent(self, event):
        self.close()
        self.deleteLater()

    def getTheM3dView(self):
        active_view = OpenMayaUI.M3dView.active3dView()
        return active_view

    def getScreenPos(self, active_view):
        utilx = OpenMaya.MScriptUtil()
        utilx.createFromInt(0)
        xPos = utilx.asIntPtr()
        utily = OpenMaya.MScriptUtil()
        utily.createFromInt(0)
        yPos = utily.asIntPtr()

        active_view.getScreenPosition(xPos, yPos)
        x = OpenMaya.MScriptUtil(xPos).asInt()
        y = OpenMaya.MScriptUtil(yPos).asInt()
        w = active_view.portWidth()
        h = active_view.portHeight()

        return QtCore.QPoint(x, y), w, h

    def getBBNodes(self):
        theBBs = []
        for nd in self.mainWindow.dataOfSkin.driverNames:
            # bbox = cmds.exactWorldBoundingBox (nd)
            # BB = OpenMaya.MBoundingBox(OpenMaya.MPoint(bbox[0],bbox[1],bbox[2]), OpenMaya.MPoint(bbox[3],bbox[4],bbox[5]))
            pos = cmds.xform(nd, q=True, ws=True, t=True)
            theBBs.append((OpenMaya.MPoint(*pos), nd))
        return theBBs

    def getDagNodes(self, skinClustName):
        print "-- getDagNodes -- ", skinClustName
        selList = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getSelectionListByName(skinClustName, selList)
        depNode = OpenMaya.MObject()
        selList.getDependNode(0, depNode)

        sknFn = OpenMayaAnim.MFnSkinCluster(depNode)

        jointPaths = OpenMaya.MDagPathArray()
        sknFn.influenceObjects(jointPaths)

        allDagNodes = []
        for jntIndex in range(jointPaths.length()):
            jntDagPath = jointPaths[jntIndex]
            dagNode = OpenMaya.MFnDagNode(jntDagPath)
            allDagNodes.append(dagNode)
            # boundingBox = dagNode.boundingBox ()
            # print dagNode.partialPathName ()
        return allDagNodes

    def getBBRay(self, view, elX, elY):
        Near = OpenMaya.MPoint()
        Far = OpenMaya.MPoint()

        theModViewMat = OpenMaya.MMatrix()
        view.modelViewMatrix(theModViewMat)

        current_camera = OpenMaya.MDagPath()
        view.getCamera(current_camera)
        real_camera = OpenMaya.MFnCamera(current_camera)

        # get cam matrix :
        current_camera_IM = current_camera.inclusiveMatrix()  # inclusiveMatrix ()
        current_camera_IMI = current_camera.inclusiveMatrixInverse()  #

        """
        view.viewToWorld(elX-self.radiusIntersect, elY-self.radiusIntersect, Near, Far )
        thePtNear = Near*current_camera_IMI

        view.viewToWorld(elX+self.radiusIntersect, elY+self.radiusIntersect, Near, Far )        
        thePtFar = Far*current_camera_IMI

        return OpenMaya.MBoundingBox (thePtNear, thePtFar)
        """
        view.viewToWorld(elX, elY, Near, Far)
        thePtFar = Far * current_camera_IMI
        thePtNear = Near * current_camera_IMI
        return OpenMaya.MBoundingBox(thePtNear, thePtFar)

        """
        # try to get with the 
        view.viewToWorld(elX, elY, Near, Far )
        
        thePtFar = Far*current_camera_IMI
        thePtNear = Near*current_camera_IMI
        
        # make boundingBox
        raySource = thePtNear
        rayDirection = OpenMaya.MVector(thePtFar -thePtNear ) #datatypes.Vector (lastTipTongue .worldMatrix.get () [0][:3])
        return (raySource,rayDirection ) 
        """

    def closest_mesh_intersection(self, meshFn, ray_source, ray_direction):
        # meshFn = OpenMaya.MFnMesh(mesh_dag)

        # Making my Hit Point
        hit_point = OpenMaya.MFloatPoint()

        ray_source_float = OpenMaya.MFloatPoint(ray_source.x, ray_source.y, ray_source.z)
        ray_direction_float = OpenMaya.MFloatVector(
            ray_direction.x, ray_direction.y, ray_direction.z
        )

        # Pointer nonsense.
        face_idx_util = OpenMaya.MScriptUtil()
        face_idx_util.createFromInt(-1)
        face_int_ptr = face_idx_util.asIntPtr()

        # Args for closest Interestion
        meshFn.closestIntersection(
            ray_source_float,  # const MFloatPoint & raySource,
            ray_direction_float,  # const MFloatVector & rayDirection,
            None,  # const MIntArray * faceIds,
            None,  # const MIntArray * triIds,
            False,  # bool idsSorted,
            OpenMaya.MSpace().kWorld,  # MSpace::Space space,
            9999,  # float maxParam,
            False,  # bool testBothDirections,
            None,  # MMeshIsectAccelParams * accelParams,
            hit_point,  # MFloatPoint & hitPoint,
            None,  # float * hitRayParam,
            face_int_ptr,  # int * hitFace,
            None,  # int * hitTriangle,
            None,  # float * hitBary1,
            None,  # float * hitBary2,
            0.000001,  # float tolerance = 1e-6,
        )

        # Again more pointer nonsense. Need to look into this more.
        face_idx = face_idx_util.getInt(face_int_ptr)
        return (hit_point, face_idx)

    def startFn(self, vertexPicking=True):
        self.vertexPicking = vertexPicking
        self.prevVtx = -1
        self.theInfluence = ""
        sel = cmds.ls(sl=True)
        self.meshName = cmds.listRelatives(sel, s=True, type="mesh")[0]
        # print self.meshName

        self.active_view = self.getTheM3dView()
        self.screenPos, self.screenWidth, self.screenHeight = self.getScreenPos(self.active_view)
        if self.vertexPicking:
            self.meshFn = self.getMeshFn(self.meshName)
            self.pointsPosi = OpenMaya.MFloatPointArray()
            self.meshFn.getPoints(self.pointsPosi)
        else:
            # self.jointsDagNodes = self.getDagNodes (self.mainWindow.dataOfSkin.theSkinCluster)
            self.BBnodes = self.getBBNodes()

            # if cmds.popupMenu ("testMenu", exists=True ) : cmds.deleteUI ("testMenu")
            # cmds.popupMenu ("testMenu",parent ="viewPanes")

    def applyPos(self, worldPos):
        self.move(worldPos + QtCore.QPoint(-20, 20))
        self.getClosestVert(worldPos)

    def getUnderCursor(self):
        res = cmds.dagObjectHit(menu="testMenu")
        if res:
            popsChildren = cmds.popupMenu("testMenu", query=True, itemArray=True)
            lbl = cmds.menuItem(popsChildren[0], query=True, label=True)
            return lbl.strip(".")
            cmds.popupMenu("testMenu", e=True, deleteAllItems=True)
        else:
            return "          "

    def getClosestVert(self, worldPos):
        thePos = worldPos - self.screenPos
        x, y = thePos.x(), (self.screenHeight - thePos.y())
        # print x,y
        if self.vertexPicking:
            # making my ray source and direction
            ray_source = OpenMaya.MPoint()
            ray_direction = OpenMaya.MVector()

            # Converting to world
            self.active_view.viewToWorld(x, y, ray_source, ray_direction)
            hit_pnt, face_idx = self.closest_mesh_intersection(
                self.meshFn, ray_source, ray_direction
            )
            if face_idx != -1:
                vertices = OpenMaya.MIntArray()
                self.meshFn.getPolygonVertices(face_idx, vertices)
                closestDst = None
                closestVert = None
                for vert in vertices:
                    vertPos = self.pointsPosi[vert]
                    dist = vertPos.distanceTo(hit_pnt)
                    if closestDst == None or dist < closestDst:
                        closestDst = dist
                        closestVert = vert
                if self.prevVtx != closestVert:
                    theInfluence = self.mainWindow.getHighestInfluence(closestVert)
                    if theInfluence != self.theInfluence:
                        self.theInfluence = theInfluence
                        self.drawText(" " + self.theInfluence)
                    # self.drawText ("vtx [{0}]".format (closestVert))
                    self.prevVtx = closestVert
                    # cmds.select ("{0}.f[{1}]".format (self.meshName, face_idx))
        else:
            """
            nearPt = OpenMaya.MPoint()
            farPt = OpenMaya.MPoint()
            self.active_view.viewToWorld (x,y,nearPt, farPt)
            rayBB  = OpenMaya.MBoundingBox (nearPt, farPt)
            txt = "          "
            rayBBRect = QtCore.QRectF(QtCore.QPointF(x-self.radiusIntersect,y-self.radiusIntersect ), QtCore.QPointF(x+self.radiusIntersect,y+self.radiusIntersect ))

            utilx = OpenMaya.MScriptUtil()
            utilx.createFromInt(0)
            xPos = utilx.asShortPtr ()
            utily = OpenMaya.MScriptUtil()
            utily.createFromInt(0)
            yPos = utily.asShortPtr()

            sizeToBeat = 0
            for dagNode in self.jointsDagNodes :
                theBB = dagNode.boundingBox()
                matrix = dagNode.dagPath().inclusiveMatrix()
                theBB.transformUsing( matrix )

                minBB, maxBB = theBB.max(),theBB.min()

                self.active_view.worldToView (minBB,xPos, yPos)
                min_x = OpenMaya.MScriptUtil(xPos).asShort()
                min_y = OpenMaya.MScriptUtil(yPos).asShort()

                self.active_view.worldToView (maxBB,xPos, yPos)
                max_x = OpenMaya.MScriptUtil(xPos).asShort()
                max_y = OpenMaya.MScriptUtil(yPos).asShort()
                theRectBB = QtCore.QRectF(QtCore.QPointF(min_x,min_y ), QtCore.QPointF(max_x,max_y ))
                #if rayBB.intersects (theBB) :

                if rayBBRect.intersects (theRectBB) :
                    theIntersect = rayBBRect.intersected (theRectBB)
                    theSize = theIntersect.width() * theIntersect.height()
                    if theSize > sizeToBeat :
                        txt = dagNode.partialPathName ()
                        sizeToBeat = theSize
                    #break
            self.drawText (txt)

            """
            hitNodes = []
            utilx = OpenMaya.MScriptUtil()
            utilx.createFromInt(0)
            xPos = utilx.asShortPtr()
            utily = OpenMaya.MScriptUtil()
            utily.createFromInt(0)
            yPos = utily.asShortPtr()

            self.mainWindow.highestInfluence = -1
            txt = "          "
            for ind, (jntCenter, nd) in enumerate(self.BBnodes):
                self.active_view.worldToView(jntCenter, xPos, yPos)
                jnt_x = OpenMaya.MScriptUtil(xPos).asShort()
                jnt_y = OpenMaya.MScriptUtil(yPos).asShort()

                if (
                    jnt_x > x - self.radiusIntersect
                    and jnt_x < x + self.radiusIntersect
                    and jnt_y > y - self.radiusIntersect
                    and jnt_y < y + self.radiusIntersect
                ):
                    # self.mainWindow.highestInfluence = ind
                    self.mainWindow.highestInfluence = self.mainWindow.dataOfSkin.indicesJoints[ind]
                    txt = nd
                    break
            self.drawText(txt)
            # txt = self.getUnderCursor ()


class CatchEventsWidget(QtWidgets.QWidget):
    # transparent widget over viewport to catch rightclicks
    verbose = False
    filterInstalled = False
    displayLabel = None
    EventFilterWidgetReceiver = None

    def __init__(self, connectedWindow=None, thePaintContextName="artAttrContext"):
        super(CatchEventsWidget, self).__init__(rootWindow())
        self.thePaintContextName = thePaintContextName
        self.setMask(QtGui.QRegion(0, 0, 1, 1))
        self.mainWindow = connectedWindow
        self.NPressed = False
        self.brushValUpdate = False

        self.OPressed = False
        self.markingMenuShown = False
        self.closingNextPressMarkingMenu = False

        self.CtrlOrShiftPressed = False
        self.CtrlOrShiftPaint = False
        self.rootWin = rootWindow()
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        self.mainMaya = QtCompat.wrapInstance(long(ptr), QtWidgets.QWidget)
        # self.setAttribute (QtCore.Qt.WA_MouseNoMask, True)

    def open(self):
        if not self.filterInstalled:
            self.installFilters()
        self.show()

    def deleteDisplayLabel(self):
        if self.displayLabel != None:
            self.displayLabel.close()
            self.displayLabel.deleteLater()
            self.displayLabel = None

    def fermer(self):
        self.deleteDisplayLabel()
        self.removeFilters()

    def installFilters(self):
        listModelPanels = [
            el for el in cmds.getPanel(vis=True) if cmds.getPanel(to=el) == "modelPanel"
        ]
        ptr = OpenMayaUI.MQtUtil.findControl(listModelPanels[0])
        model_panel_4 = QtCompat.wrapInstance(long(ptr), QtWidgets.QWidget)
        self.EventFilterWidgetReceiver = model_panel_4.parent().parent()

        self.filterInstalled = True
        # self.EventFilterWidgetReceiver.installEventFilter(self)
        QApplication.instance().installEventFilter(self)

    def removeFilters(self):
        self.hide()
        self.filterInstalled = False
        QApplication.instance().removeEventFilter(self)
        # self.EventFilterWidgetReceiver.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseMove:  # move
            if event.modifiers() != QtCore.Qt.AltModifier:  # not orbit in scene
                if event.buttons() == QtCore.Qt.LeftButton:  # painting
                    if self.CtrlOrShiftPressed:
                        self.CtrlOrShiftPaint = True
                if self.NPressed:
                    self.brushValUpdate = True
                if self.displayLabel:
                    self.displayLabel.applyPos(event.globalPos())
            else:
                if self.CtrlOrShiftPressed:
                    self.CtrlOrShiftPaint = True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        # retun in mouseMove
        if (
            event.type() in [QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease]
            and event.modifiers() != QtCore.Qt.AltModifier
        ):
            """
            if obj is self : print "self"
            elif obj is self.parent() : print "self Prt"
            elif obj is self.parent().parent() : print "self Prt Prt"
            elif obj is self.rootWin : print "self.rootWin"
            else : print obj
            """
            if event.modifiers() == QtCore.Qt.NoModifier:  # regular click
                if event.type() == QtCore.QEvent.MouseButtonPress:  # click
                    if self.displayLabel:  # let's close the label
                        self.mainWindow.selectPickedInfluence()
                        self.deleteDisplayLabel()
                        event.ignore()
                        return True
                    elif self.OPressed:
                        if not self.markingMenuShown:
                            callMarkingMenu()
                            self.markingMenuShown = True
                            self.closingNextPressMarkingMenu = False
                            # print "-- callMarkingMenu --"
                    elif self.closingNextPressMarkingMenu:
                        if cmds.popupMenu("tempMM", exists=True):
                            cmds.deleteUI("tempMM")
                        self.markingMenuShown = False
                        self.OPressed = False
                        self.closingNextPressMarkingMenu = False
                elif event.type() == QtCore.QEvent.MouseButtonRelease:  # click release
                    if self.markingMenuShown:
                        # print "Closing markingMenu !!"
                        self.closingNextPressMarkingMenu = True
                    if self.brushValUpdate:  # update the brush size
                        self.brushValUpdate = False
                        self.mainWindow.changeOfValue()
                    if self.CtrlOrShiftPaint:  # change to regular paint
                        self.CtrlOrShiftPaint = False
                        if not self.CtrlOrShiftPressed:
                            # ctrl or shift has been released previously so we change button ---
                            # we need to do it in the script job, no other way ---
                            currContext = cmds.currentCtx()
                            if currContext == self.thePaintContextName:
                                gArtAttrCurrentAttr = mel.eval("$tmp = $gArtAttrCurrentAttr")
                                typeOfNode, node, attr = gArtAttrCurrentAttr.split(".")
                                theFn = partial(cmds.evalDeferred, self.prevButton.click)
                                cmds.scriptJob(
                                    runOnce=True, attributeChange=[node + "." + attr, theFn]
                                )
                return super(CatchEventsWidget, self).eventFilter(obj, event)
            else:  # remove the shift and control modifiers
                if obj is not self.parent() and not self.mainWindow.uiInfluenceTREE.isOn:
                    altShift = (
                        event.modifiers()
                        == QtCore.Qt.AltModifier | event.modifiers()
                        == QtCore.Qt.ShiftModifier
                    )
                    altCtrl = (
                        event.modifiers()
                        == QtCore.Qt.AltModifier | event.modifiers()
                        == QtCore.Qt.ControlModifier
                    )
                    theModifiers = QtCore.Qt.KeyboardModifiers(QtCore.Qt.NoModifier)
                    if altShift or altCtrl:
                        theModifiers = QtCore.Qt.KeyboardModifiers(QtCore.Qt.AltModifier)
                    theMouseEvent = QtGui.QMouseEvent(
                        event.type(), event.pos(), event.button(), event.buttons(), theModifiers
                    )
                    QApplication.instance().postEvent(obj, theMouseEvent)
                    event.ignore()
                    return True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        # return in mouseButton Press or Release

        if event.type() == QtCore.QEvent.KeyRelease:
            if event.key() in [QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control]:
                if self.verbose:
                    print "custom SHIFT released"
                self.CtrlOrShiftPressed = False
                if not self.CtrlOrShiftPaint:
                    self.prevButton.click()
                # event.ignore ()

                # return True
            elif event.key() == QtCore.Qt.Key_N:
                self.NPressed = False  # the value of the brush
            elif event.key() == QtCore.Qt.Key_O:
                # delete marking menu
                # self.OPressed = False
                # self.markingMenuShown = False
                # if self.markingMenuShown :

                # if cmds.popupMenu( "tempMM", exists=True): cmds.deleteUI ("tempMM")
                if obj is self.EventFilterWidgetReceiver and self.OPressed:
                    # print "  OReleased"
                    self.OPressed = False
                    event.ignore()
                    return True
                return super(CatchEventsWidget, self).eventFilter(obj, event)
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_P:  # print info of the click press
                active_view = OpenMayaUI.M3dView.active3dView()
                sw = active_view.widget()
                res = QtCompat.wrapInstance(long(sw), QtWidgets.QWidget)

                listModelPanels = [
                    el for el in cmds.getPanel(vis=True) if cmds.getPanel(to=el) == "modelPanel"
                ]
                ptr = OpenMayaUI.MQtUtil.findControl(listModelPanels[0])
                model_panel_4 = QtCompat.wrapInstance(long(ptr), QtWidgets.QWidget)

                if res is obj:
                    print "ViewPort"
                elif res is self.mainMaya:
                    print
                elif obj is self.mainMaya:
                    print "self.mainMaya"
                elif obj is self:
                    print "self"
                elif obj is self.parent():
                    print "self Prt"
                elif obj is self.parent().parent():
                    print "self Prt Prt"
                elif obj is self.rootWin:
                    print "self.rootWin"
                elif obj is model_panel_4:
                    print "model_panel_4"
                elif obj is model_panel_4.parent():
                    print "model_panel_4 Prt"
                elif obj is model_panel_4.parent().parent():
                    print "model_panel_4 Prt PRT"
                else:
                    print obj
                return super(CatchEventsWidget, self).eventFilter(obj, event)
            if event.key() == QtCore.Qt.Key_O:
                if obj is self.EventFilterWidgetReceiver:
                    self.OPressed = True
                    # print "  OPressed"
                    return True
                if self.OPressed:
                    event.ignore()
                    return True
                else:
                    return super(CatchEventsWidget, self).eventFilter(obj, event)
                # delete marking menu
                #
                # self.markingMenuShown = False
                # print "set self.markingMenuShown False  OPressed"
                # event.accept ()
                # return True
            elif event.key() == QtCore.Qt.Key_Control and not (
                self.CtrlOrShiftPressed or self.CtrlOrShiftPaint
            ):
                if QApplication.mouseButtons() == QtCore.Qt.NoButton:
                    if self.verbose:
                        print "custom CONTROL pressed"
                    event.ignore()
                    self.CtrlOrShiftPressed = True
                    self.CtrlOrShiftPaint = False
                    self.prevButton = self.mainWindow.getEnabledButton()
                    if self.prevButton == self.mainWindow.add_btn:
                        self.mainWindow.rmv_btn.setChecked(True)
                        self.mainWindow.brushFunctions.setPaintMode(1)  # remove
                    elif self.prevButton == self.mainWindow.locks_btn:
                        self.mainWindow.brushFunctions.setPaintMode(7)  # remove
                        self.mainWindow.locks_btn.setText("UNLOCK")
                    # self.mainWindow.rmv_btn.click()
                    return True
            elif event.key() == QtCore.Qt.Key_Shift and not (
                self.CtrlOrShiftPressed or self.CtrlOrShiftPaint
            ):
                if QApplication.mouseButtons() == QtCore.Qt.NoButton:

                    if self.verbose:
                        print "custom SHIFT pressed"
                    event.ignore()
                    self.CtrlOrShiftPressed = True
                    self.CtrlOrShiftPaint = False
                    self.prevButton = self.mainWindow.getEnabledButton()
                    self.mainWindow.smooth_btn.click()
                    return True
            elif event.key() == QtCore.Qt.Key_N:
                self.NPressed = True
            elif event.key() == QtCore.Qt.Key_Escape:
                print "CLOSING"
                event.ignore()
                self.close()
                return True
            shiftPressed = event.modifiers() == QtCore.Qt.ShiftModifier
            ctrlPressed = event.modifiers() == QtCore.Qt.ControlModifier
            altPressed = event.modifiers() == QtCore.Qt.AltModifier
            if ctrlPressed and event.key() == QtCore.Qt.Key_Z:
                if self.verbose:
                    print "custom UNDO"
                event.ignore()
                self.mainWindow.undo_btn.click()
                return True
            if event.key() == QtCore.Qt.Key_X and altPressed:
                listModelPanels = [
                    el for el in cmds.getPanel(vis=True) if cmds.getPanel(to=el) == "modelPanel"
                ]
                val = not cmds.modelEditor(listModelPanels[0], query=True, jointXray=True)
                for pnel in listModelPanels:
                    cmds.modelEditor(pnel, edit=True, jointXray=val)
                event.ignore()
                return True
            if event.key() == QtCore.Qt.Key_W and altPressed:
                currCtx = cmds.currentCtx()
                prevVal = cmds.artAttrCtx(currCtx, query=True, showactive=True)
                cmds.artAttrCtx(currCtx, edit=True, showactive=not prevVal)
                event.ignore()
                return True
            if event.key() == QtCore.Qt.Key_S and altPressed:
                if self.mainWindow.multi_rb.isChecked():
                    self.mainWindow.solo_rb.toggle()
                else:
                    self.mainWindow.multi_rb.toggle()

                event.ignore()
                return True
            if event.key() == QtCore.Qt.Key_M and altPressed:
                self.mainWindow.mirrorActive_cb.toggle()
                event.ignore()
                return True
            if event.key() == QtCore.Qt.Key_D:
                if self.verbose:
                    if altPressed:
                        print "custom pressed Alt D"
                    else:
                        print "custom pressed D"
                # self.mainWindow.pickMaxInfluence ()
                self.mainWindow.pickInfluence(vertexPicking=altPressed)
                event.ignore()
                return True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        return super(CatchEventsWidget, self).eventFilter(obj, event)

    def createDisplayLabel(self, vertexPicking=True):
        if not self.displayLabel:
            self.displayLabel = LabelDisplayInfluence()
            self.displayLabel.mainWindow = self.mainWindow
            self.displayLabel.show()
            self.displayLabel.drawText("          ")
        self.displayLabel.startFn(vertexPicking=vertexPicking)

    def closeEvent(self, e):
        """
        Make sure the eventFilter is removed
        """
        self.removeFilters()
        return super(CatchEventsWidget, self).closeEvent(e)


"""
a = CatchEventsWidget ()
"""
