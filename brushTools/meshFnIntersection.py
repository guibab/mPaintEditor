from __future__ import print_function
from __future__ import absolute_import
from Qt import QtGui, QtCore
from maya import OpenMaya, OpenMayaUI, cmds


class Orbit(object):
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

    def closest_mesh_intersection(self, meshFn, ray_source, ray_direction):
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

    def getValues(self, node, returnVertex=False):
        meshShpList = cmds.listRelatives(node, s=True, type="mesh")
        self.active_view = self.getTheM3dView()
        if meshShpList:
            self.meshName = meshShpList[0]
            # print self.meshName
            self.screenPos, self.screenWidth, self.screenHeight = self.getScreenPos(
                self.active_view
            )
            self.meshFn = self.getMeshFn(self.meshName)
            worldPos = QtGui.QCursor.pos()
            hit_pnt, face_idx = self.getClosestVert(worldPos)

            arr = OpenMaya.MIntArray()
            self.meshFn.getPolygonVertices(face_idx, arr)
            theVert = arr[0]
            if returnVertex:
                return theVert
            return [hit_pnt.x, hit_pnt.y, hit_pnt.z]
        else:
            posi = cmds.xform(node, q=True, ws=True, t=True)
            return posi

    def getUnderCursor(self):
        if cmds.popupMenu("testMenu", exists=True):
            cmds.deleteUI("testMenu")
        cmds.popupMenu("testMenu", parent="viewPanes")

        res = cmds.dagObjectHit(menu="testMenu")
        if res:
            popsChildren = cmds.popupMenu("testMenu", query=True, itemArray=True)
            lbl = cmds.menuItem(popsChildren[0], query=True, label=True)
            return lbl.strip(".")
            cmds.popupMenu("testMenu", e=True, deleteAllItems=True)
        else:
            return ""

    def orbitCamera(self, posiCenter):
        current_camera = OpenMaya.MDagPath()
        self.active_view.getCamera(current_camera)
        dagNode = OpenMaya.MFnDagNode(current_camera)
        cameraName = dagNode.partialPathName()
        cmds.viewLookAt(cameraName, pos=posiCenter)
        cmds.camera(cameraName, e=True, worldCenterOfInterest=posiCenter, worldUp=[0, 1, 0])

    def getClosestVert(self, worldPos):
        thePos = worldPos - self.screenPos
        x, y = thePos.x(), (self.screenHeight - thePos.y())
        # making my ray source and direction
        ray_source = OpenMaya.MPoint()
        ray_direction = OpenMaya.MVector()
        # Converting to world
        self.active_view.viewToWorld(x, y, ray_source, ray_direction)
        return self.closest_mesh_intersection(self.meshFn, ray_source, ray_direction)

    def setOrbitPosi(self):
        underCursor = self.getUnderCursor()
        if underCursor and cmds.objExists(underCursor):
            hitPoint = self.getValues(underCursor)
            self.orbitCamera(hitPoint)
            print(underCursor)
