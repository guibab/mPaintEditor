from Qt import QtGui, QtCore, QtWidgets
from Qt.QtWidgets import QApplication, QSplashScreen, QDialog, QMainWindow
from maya import OpenMaya, OpenMayaUI, OpenMayaAnim, cmds, mel
from functools import partial


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


class GetClosestVert(QtWidgets.QLabel):
    def __init__(self):
        super(GetClosestVert, self).__init__(rootWindow())
        self._font = QtGui.QFont("Myriad Pro", 10)
        self._metrics = QtGui.QFontMetrics(self._font)
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint
        )  # (QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        self.currentText = ""
        self.radiusIntersect = 10  # select from screen
        self.setStyleSheet(
            "margin-left: 0px; border-radius: 25px; background: yellow; color: black; border: 1px solid black;"
        )

    def drawText(self, txt):
        if self.currentText != txt:
            self.setText(txt)
            sz = self._metrics.size(QtCore.Qt.TextSingleLine, txt)
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
                    self.mainWindow.highestInfluence = ind
                    txt = nd
                    break
            self.drawText(txt)
            # txt = self.getUnderCursor ()


class CatchEventsWidget(QtWidgets.QWidget):
    # transparent widget over viewport to catch rightclicks
    verbose = False
    filterInstalled = False
    displayLabel = None

    def __init__(self, connectedWindow=None):
        super(CatchEventsWidget, self).__init__(rootWindow())
        self.setMask(QtGui.QRegion(0, 0, 1, 1))
        self.mainWindow = connectedWindow
        self.NPressed = False
        self.brushValUpdate = False
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
        self.filterInstalled = True
        QApplication.instance().installEventFilter(self)

    def removeFilters(self):
        self.hide()
        self.filterInstalled = False
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseMove and event.modifiers() != QtCore.Qt.AltModifier:
            if self.NPressed:
                self.brushValUpdate = True
            if self.displayLabel:
                self.displayLabel.applyPos(event.globalPos())
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        if (
            event.type() in [QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease]
            and event.modifiers() != QtCore.Qt.AltModifier
        ):
            # if event.button() == QtCore.Qt.RightButton  : print "Right Click"
            # elif event.button() == QtCore.Qt.LeftButton  : print "Left Click"

            # theModifiers = QtCore.Qt.KeyboardModifiers (QtCore.Qt.NoModifier )
            if event.modifiers() == QtCore.Qt.NoModifier:
                if event.type() == QtCore.QEvent.MouseButtonRelease:
                    if self.brushValUpdate:
                        self.brushValUpdate = False
                        # print "!!! update Value of Brush !!!"
                        self.mainWindow.changeOfValue()
                elif self.displayLabel and event.type() == QtCore.QEvent.MouseButtonPress:
                    self.mainWindow.selectPickedInfluence()
                    self.deleteDisplayLabel()
                    event.ignore()
                    return True
                return super(CatchEventsWidget, self).eventFilter(obj, event)
            else:
                # remove the alt and control
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
        elif event.type() == QtCore.QEvent.KeyRelease:
            if event.key() in [QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control]:
                if self.verbose:
                    print "custom SHIFT released"
                event.ignore()
                self.prevButton.click()
                return True
            elif event.key() == QtCore.Qt.Key_N:
                self.NPressed = False  # the value of the brush
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Control:
                if self.verbose:
                    print "custom CONTROL pressed"
                event.ignore()
                self.prevButton = self.mainWindow.getEnabledButton()
                self.mainWindow.smooth_btn.click()
                return True
            elif event.key() == QtCore.Qt.Key_Shift:
                if self.verbose:
                    print "custom SHIFT pressed"
                event.ignore()
                self.prevButton = self.mainWindow.getEnabledButton()
                self.mainWindow.rmv_btn.setChecked(True)
                # self.mainWindow.rmv_btn.click()
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
            if event.key() == QtCore.Qt.Key_D:
                if self.verbose:
                    if altPressed:
                        print "custom pressed Alt D"
                    else:
                        print "custom pressed D"
                # self.mainWindow.pickMaxInfluence ()
                self.mainWindow.prepareToGetHighestInfluence()
                self.createDisplayLabel(vertexPicking=altPressed)
                event.ignore()
                return True
            return super(CatchEventsWidget, self).eventFilter(obj, event)
        else:
            return super(CatchEventsWidget, self).eventFilter(obj, event)

    def createDisplayLabel(self, vertexPicking=True):
        self.displayLabel = GetClosestVert()
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
