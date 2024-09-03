from maya import OpenMaya
from maya import OpenMayaUI
from maya import OpenMayaMPx
from maya import cmds
try:
    from PySide.QtGui import QApplication
    from PySide import QtCore
except ImportError:
    from PySide2.QtWidgets import QApplication
    from PySide2 import QtCore
import math
import sys

# 第一个插件，照着参考案例抄一份
DRAGGER = "MyDuplicateOverSurfaceDragger"
UTIL = OpenMaya.MScriptUtil()

kPluginCmdName = "MyDuplicateOverSurface"
kRotationFlag = "-r"
kRotationFlagLong = "-rotation"
kDummyFlag = "-d"
kDummyFlagLong = "-dummy"
kInstanceFlag = "-ilf"
kInstanceFlagLong = "-instanceLeaf"


def syntaxCreator():
    syntax = OpenMaya.MSyntax()
    syntax.addArg(OpenMaya.MSyntax.kString)
    syntax.addFlag(
        kDummyFlag,
        kDummyFlagLong,
        OpenMaya.MSyntax.kBoolean)
    syntax.addFlag(
        kRotationFlag,
        kRotationFlagLong,
        OpenMaya.MSyntax.kBoolean)
    syntax.addFlag(
        kInstanceFlag,
        kInstanceFlagLong,
        OpenMaya.MSyntax.kBoolean)
    return syntax

class MyDuplicateOverSurface(OpenMayaMPx.MPxCommand):
    def __init__(self):
        super(MyDuplicateOverSurface, self).__init__()
        self.SPACE = OpenMaya.MSpace.kWorld

        self.ROTATION = True
        self.InstanceFlag = False

        self.SHIFT = QtCore.Qt.ShiftModifier
        self.CTRL = QtCore.Qt.ControlModifier

        self.SOURCE = None # 存储args当中的第一个参数值，表示被复制的物体是什么
        self.ANCHOR_POINT = None # 存储鼠标点击的位置
        self.SCALE_ORIG = None
        self.MATRIX_ORIG = None
        self.TARGET_FNMESH = None
        self.DUPLICATED = None

        self.MOD_FIRST = None
        self.MOD_POINT = None

    def doIt(self, args):
        # Parse the arguments.
        argData = OpenMaya.MArgDatabase(syntaxCreator(), args)
        self.SOURCE = argData.commandArgumentString(0)
        if argData.isFlagSet(kRotationFlag) is True:
            self.ROTATION = argData.flagArgumentBool(kRotationFlag, 0) # 这里的0指的是比如-rotation True，0就是True

        if argData.isFlagSet(kInstanceFlag) is True:
            self.InstanceFlag = argData.flagArgumentBool(kInstanceFlag, 0)

        cmds.setToolTo(self.setupDragger())

    def setupDragger(self):
        """ Setup dragger context command """

        try:
            cmds.deleteUI(DRAGGER)
        except:
            pass

        dragger = cmds.draggerContext(
            DRAGGER,
            pressCommand=self.pressEvent,
            dragCommand=self.dragEvent,
            releaseCommand=self.releaseEvent,
            space='screen',
            projection='viewPlane',
            undoMode='step',
            cursor='hand')

        return dragger

    def getDragInfo(self, x, y):
        """ Get distance and angle in screen space. """

        start_x = self.MOD_POINT[0]
        start_y = self.MOD_POINT[1]
        end_x = x
        end_y = y

        cathetus = end_x - start_x
        opposite = end_y - start_y

        # Get distance using Pythagorean theorem
        length = math.sqrt(
            math.pow(cathetus, 2) + math.pow(opposite, 2))

        try:
            theta = cathetus / length
            degree = math.degrees(math.acos(theta))  # arcos图像在0,1之间单调递减，用这种方式拟合鼠标移动带动对象旋转
            if opposite < 0:
                degree = -degree
            return cathetus, degree
        except ZeroDivisionError:
            return None, None
    def pressEvent(self):
        button = cmds.draggerContext(DRAGGER, query=True, button=True) # 获取当前按下的鼠标键
        # Leave the tool by middle click
        if button == 2:
            cmds.setToolTo('selectSuperContext')
            return

        # Get clicked point in viewport screen space
        pressPosition = cmds.draggerContext(DRAGGER, query=True, ap=True) # 当 ap=True 被设置时，该查询返回的是用户在按下鼠标时的位置坐标。这些坐标通常是以屏幕空间或视图空间的形式表示的，取决于上下文设置。
        x = pressPosition[0]
        y = pressPosition[1]
        self.ANCHOR_POINT = [x, y]

        # Convert
        point_in_3d, vector_in_3d = convertTo3D(x, y)
        # Get MFnMesh of snap target
        targetDagPath = getDagPathFromScreen(x, y)  # 点击把A复制到B上面，这个返回的是B对象

        # If draggin outside of objects
        if targetDagPath is None:
            return

        # Get origianl scale information
        self.SCALE_ORIG = cmds.getAttr(self.SOURCE + ".scale")[0] # 从 Maya 场景中获取源对象（self.SOURCE）的缩放属性,得到的结果应该是个三维向量[sx,sy,sz]
        self.MATRIX_ORIG = cmds.xform(self.SOURCE, q=True, matrix=True)  # 获取源对象的变换矩阵（包括位置、旋转和缩放）。q=True表示查询，matrix=True表示查询的是变换矩阵吗，返回16个值，表示旋转、缩放、位移等信息
        self.TARGET_FNMESH = OpenMaya.MFnMesh(targetDagPath)

        transformMatrix = self.getMatrix(
            point_in_3d,
            vector_in_3d,
            self.TARGET_FNMESH,
            self.SCALE_ORIG,
            self.MATRIX_ORIG)

        if transformMatrix is None:
            return

        # Create new object to snap
        self.DUPLICATED = self.getNewObject()
        # Reset transform of current object
        cmds.setAttr(self.DUPLICATED + ".translate", *[0, 0, 0]) # 这个 * 运算符用于解包（unpacking）列表或元组,*[0, 0, 0] 等同于 0, 0, 0，这意味着将这些值作为三个独立的参数传递给 setAttr
        location = [-i for i
                    in cmds.xform(self.DUPLICATED, q=True, ws=True, rp=True)] # ws: 世界空间，rp: pivot point(对象的原点)，这里的 -i 是为了将位置取反，因为我们要将新对象放到点击的位置上
        cmds.setAttr(self.DUPLICATED + ".translate", *location)

        # Can't apply freeze to instances
        if self.InstanceFlag is not True:
            # 执行这条语句后，物体的平移信息将被标记为已应用的状态，但它在视图中的实际位置不会改变
            cmds.makeIdentity(self.DUPLICATED, apply=True, t=True)  # 将新对象的变换属性重置为默认值

        # Apply transformMatrix to the new object
        cmds.xform(self.DUPLICATED, matrix=transformMatrix)

    def getNewObject(self):
            return cmds.duplicate(self.SOURCE, ilf=self.InstanceFlag)[0]  # 如果 self.InstanceFlag 为 True，则复制的对象将是原始对象的实例。这意味着更改实例的属性会影响到所有引用同一实例的对象。如果为 False，则复制的对象将是独立的副本，彼此之间没有任何关系。

    def dragEvent(self):
        """ Event while dragging a 3d view """
        # 拖动的时候会调用这个函数，从而移动被复制的对象
        if self.TARGET_FNMESH is None:
            return
        dragPosition = cmds.draggerContext(
            DRAGGER,
            query=True,
            dragPoint=True)  # Drag point (double array) current position of dragger during drag.

        x = dragPosition[0]
        y = dragPosition[1]  # x和y会时刻更新为最新的鼠标位置
        modifier = cmds.draggerContext(
            DRAGGER,
            query=True,
            modifier=True)  # Returns the current modifier type: ctrl, alt or none.
        if modifier == "none":
            self.MOD_FIRST = True
        qtModifier = QApplication.keyboardModifiers()
        if qtModifier == self.CTRL or qtModifier == self.SHIFT:
            # If this is the first click of dragging
            if self.MOD_FIRST is True:
                self.MOD_POINT = [x, y]

                # global MOD_FIRST
                self.MOD_FIRST = False

            length, degree = self.getDragInfo(x, y)

            if qtModifier == self.CTRL:  # 按下CTRL键只控制旋转
                length = 1.0
            if qtModifier == self.SHIFT:  # 按下Shift键只控制缩放
                degree = 0.0

            # Convert
            point_in_3d, vector_in_3d = convertTo3D(
                self.MOD_POINT[0],
                self.MOD_POINT[1])
        else:
            point_in_3d, vector_in_3d = convertTo3D(x, y)
            length = 1.0
            degree = 0.0

        # Get new transform matrix for new object
        transformMatrix = self.getMatrix(
            point_in_3d,
            vector_in_3d,
            self.TARGET_FNMESH,
            self.SCALE_ORIG,
            self.MATRIX_ORIG,
            length,
            degree
        )

        if transformMatrix is None:
            return

        # Apply new transform
        cmds.xform(self.DUPLICATED, matrix=transformMatrix)
        cmds.setAttr(self.DUPLICATED + ".shear", *[0, 0, 0])

        cmds.refresh(currentView=True, force=True)


    def releaseEvent(self):
        self.MOD_FIRST = True  # 释放鼠标键后，MOD_FIRST 会被重置为 True，恢复到第一次点击的状态

    def getIntersection(self, point_in_3d, vector_in_3d, fnMesh):
        """ Return a point Position of intersection..
            Args:
                point_in_3d  (OpenMaya.MPoint)
                vector_in_3d (OpenMaya.mVector)
            Returns:
                OpenMaya.MFloatPoint : hitPoint
        """

        hitPoint = OpenMaya.MFloatPoint()
        hitFacePtr = UTIL.asIntPtr()
        idSorted = False
        testBothDirections = False
        faceIDs = None
        triIDs = None
        accelParam = None
        hitRayParam = None
        hitTriangle = None
        hitBary1 = None
        hitBary2 = None
        maxParamPtr = 99999

        # intersectPoint = OpenMaya.MFloatPoint(
        result = fnMesh.closestIntersection(
            OpenMaya.MFloatPoint(
                point_in_3d.x,
                point_in_3d.y,
                point_in_3d.z),
            OpenMaya.MFloatVector(vector_in_3d),
            faceIDs,
            triIDs,
            idSorted,
            self.SPACE,
            maxParamPtr,
            testBothDirections,
            accelParam,
            hitPoint,
            hitRayParam,
            hitFacePtr,
            hitTriangle,
            hitBary1,
            hitBary2)

        faceID = UTIL.getInt(hitFacePtr)

        if result is True:
            return hitPoint, faceID
        else:
            return None, None

    def getTangent(self, faceID, targetFnMesh):
        # 计算所有顶点切线的平均值，以形成一个整体的切线向量。
        """ Return a tangent vector of a face.
            Args:
                faceID  (int)
                mVector (OpenMaya.MVector)
            Returns:
                OpenMaya.MVector : tangent vector
        """

        tangentArray = OpenMaya.MFloatVectorArray()
        targetFnMesh.getFaceVertexTangents(
            faceID,
            tangentArray,
            self.SPACE)
        numOfVtx = tangentArray.length()
        x = sum([tangentArray[i].x for i in range(numOfVtx)]) / numOfVtx
        y = sum([tangentArray[i].y for i in range(numOfVtx)]) / numOfVtx
        z = sum([tangentArray[i].z for i in range(numOfVtx)]) / numOfVtx
        tangentVector = OpenMaya.MVector()
        tangentVector.x = x
        tangentVector.y = y
        tangentVector.z = z
        tangentVector.normalize()

        return tangentVector


    def getNormal(self, pointPosition, targetFnMesh):
        """ Return a normal vector of a face.
            Args:
                pointPosition  (OpenMaya.MFloatPoint)
                targetFnMesh (OpenMaya.MFnMesh)
            Returns:
                OpenMaya.MVector : tangent vector
                int              : faceID
        """

        ptr_int = UTIL.asIntPtr()
        origin = OpenMaya.MPoint(pointPosition)
        normal = OpenMaya.MVector()
        targetFnMesh.getClosestNormal(
            origin,
            normal,
            self.SPACE,
            ptr_int)
        normal.normalize()

        return normal

    def getMatrix(self,
                  mPoint,
                  mVector,
                  targetFnMesh,
                  scale_orig,
                  matrix_orig,
                  scale_plus=1,
                  degree_plus=0.0):

        """ Return a list of values which consist a new transform matrix.
            Args:
                mPoint  (OpenMaya.MPoint)
                mVector (OpenMaya.MVector)
            Returns:
                list : 16 values for matrixs
        """
        # Position of new object
        OP, faceID = self.getIntersection(mPoint, mVector, targetFnMesh)

        # If it doesn't intersect to any geometries, return None
        if OP is None and faceID is None:
            return None

        qtMod = QApplication.keyboardModifiers()
        if qtMod == (self.CTRL | self.SHIFT):  # Ctrl+Shift，此时OP是最近的顶点
            OP = getClosestVertex(OP, faceID, targetFnMesh)

        # Get normal vector and tangent vector
        if self.ROTATION is False:  # 如果不需要进行旋转操作，下面的代码值得记住，可以用来获取法线和切线
            NV = OpenMaya.MVector(   # 获取法线
                matrix_orig[4],
                matrix_orig[5],
                matrix_orig[6])
            NV.normalize()
            TV = OpenMaya.MVector(  # 获取切线
                matrix_orig[0],
                matrix_orig[1],
                matrix_orig[2])
            TV.normalize()
        else:
            NV = self.getNormal(OP, targetFnMesh)
            TV = self.getTangent(faceID, targetFnMesh)

        # Ctrl-hold rotation
        if qtMod == self.CTRL:
            try:
                rad = math.radians(degree_plus)
                q1 = NV.x * math.sin(rad / 2)
                q2 = NV.y * math.sin(rad / 2)
                q3 = NV.z * math.sin(rad / 2)
                q4 = math.cos(rad / 2)
                TV = TV.rotateBy(q1, q2, q3, q4)  # rotateBy(axis, angle)
            except TypeError:
                pass

        # Bitangent vector
        BV = TV ^ NV  # 注意这里不是切线空间，而是世界空间，所以切线方向是X方向，法线方向是Y方向，叉乘得到的是Z方向，即bitangent方向
        BV.normalize()

        # 4x4 Transform Matrix
        try:
            x = scale_orig[0] * (scale_plus / 100 + 1.0)
            y = scale_orig[1] * (scale_plus / 100 + 1.0)
            z = scale_orig[2] * (scale_plus / 100 + 1.0)
            TV *= x
            NV *= y
            BV *= z
        except TypeError:
            pass
        finally:
            matrix = [
                TV.x, TV.y, TV.z, 0,  # x
                NV.x, NV.y, NV.z, 0,  # y
                BV.x, BV.y, BV.z, 0,  # z
                OP.x, OP.y, OP.z, 1
            ]

        return matrix


def convertTo3D(screen_x, screen_y):
    """ Return point and vector of clicked point in 3d space.
        Args:
            screen_x  (int)
            screen_y (int)
        Returns:
            OpenMaya.MPoint : point_in_3d : 用户点击的地方在三维场景中的位置。
            OpenMaya.MVector : vector_in_3d : 从摄像机指向该点的方向向量
    """
    point_in_3d = OpenMaya.MPoint()
    vector_in_3d = OpenMaya.MVector()

    OpenMayaUI.M3dView.active3dView().viewToWorld(
        int(screen_x),
        int(screen_y),
        point_in_3d,
        vector_in_3d)

    return point_in_3d, vector_in_3d


def getDagPathFromScreen(x, y):
    # 根据鼠标的屏幕坐标获取相应的三维对象的 DAG 路径。
    """ Args:
            x  (int or float)
            y (int or float)
        Returns:
            dagpath : OpenMaya.MDagPath
    """
    # Select from screen
    OpenMaya.MGlobal.selectFromScreen(
        int(x),
        int(y),
        OpenMaya.MGlobal.kReplaceList,
        OpenMaya.MGlobal.kSurfaceSelectMethod)

    # Get dagpath, or return None if fails
    tempSel = OpenMaya.MSelectionList()
    OpenMaya.MGlobal.getActiveSelectionList(tempSel)
    dagpath = OpenMaya.MDagPath()
    if tempSel.length() == 0:
        return None
    else:
        tempSel.getDagPath(0, dagpath)
        return dagpath

def getClosestVertex(point_orig, faceID, fnMesh):
    """ Args:
            point_orig  (OpenMaya.MFloatPoint)
            faceID (int)
            fnMesh (OpenMaya.MFnMesh)
        Returns:
            closestPoint : OpenMaya.MPoint
    """

    vertexIndexArray = OpenMaya.MIntArray()
    fnMesh.getPolygonVertices(faceID, vertexIndexArray)
    basePoint = OpenMaya.MPoint(point_orig)
    closestPoint = OpenMaya.MPoint()
    length = 99999.0
    for index in vertexIndexArray:
        point = OpenMaya.MPoint()
        fnMesh.getPoint(index, point, OpenMaya.MSpace.kWorld)
        lengthVector = point - basePoint
        if lengthVector.length() < length:
            length = lengthVector.length()
            closestPoint = point

    return closestPoint

# Creator
def cmdCreator():
    return OpenMayaMPx.asMPxPtr(MyDuplicateOverSurface())


def initializePlugin(mObject):
    mPlugin = OpenMayaMPx.MFnPlugin(mObject, "LearnMayaPlugin")
    try:
        mPlugin.registerCommand(kPluginCmdName, cmdCreator)
        mPlugin.setVersion("0.10")
    except:
        sys.stderr.write("Failed to register command: %s\n" % kPluginCmdName)
        raise


def uninitializePlugin(mObject):
    mPlugin = OpenMayaMPx.MFnPlugin(mObject)
    try:
        mPlugin.deregisterCommand(kPluginCmdName)
    except:
        sys.stderr.write("Failed to unregister command: %s\n" % kPluginCmdName)