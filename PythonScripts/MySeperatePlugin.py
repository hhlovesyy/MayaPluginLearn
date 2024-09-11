# import modules
import maya.cmds as cmds
import maya.OpenMaya as OM
import random
import math
import re

class UVToolKit():
    def __init__(self, *args):
        if cmds.window("windowUI", exists=True): # exists=True 意味着窗口已经存在
            cmds.deleteUI("windowUI")
        cmds.window("windowUI", title="Separate Toolkit: ChrisZhang", resizeToFitChildren=True, sizeable=True)  # sizeable=False 禁止调整窗口大小
        # base object layout
        cmds.frameLayout(label="General", collapsable=False, mw=5, mh=5)
        cmds.rowColumnLayout(nc=4, cal=[(1, "right")], cw=[(1, 80), (2, 200), (3, 95), (4, 150)])
        cmds.text(l="选择的物体: ")
        cmds.textField("baseObject")
        cmds.button("baseObjectButton", l="选择", c=self.selectBaseObject)
        cmds.setParent("..")

        cmds.separator(h=10, st='in')
        cmds.rowColumnLayout(w=380)
        # 创建复选框
        cmds.checkBox('PREVIEW', label='预览模式', value=True)
        cmds.checkBox('SINGLE_MODE', label='单个模式', value=False)
        cmds.checkBox('USE_PLANE', label='使用平面', value=False)
        cmds.checkBox('FLAT', label='FLAT', value=False)
        cmds.checkBox('RESULT_ONLY', label='仅显示结果', value=False)

        cmds.checkBox('LEGACY', label='LEGACY', value=False)
        cmds.setParent("..")

        cmds.separator(h=10, st='in')
        cmds.rowColumnLayout(w=380)
        # 创建 textFieldGrp 控件
        cmds.textFieldGrp(
            "textFieldGroup",
            label="GROUP NAME",
            text="pl_shattered_GRP",
            annotation="group name for the result",
            width=350,
            columnAlign=[1, 'left'],
            columnWidth=[1, 45],
            adjustableColumn=True,
        )
        # 创建滑块
        cmds.floatSliderGrp('MIN_SCALE', label='最小比例', field=True, minValue=0.1, maxValue=100.0, fieldMinValue=0.1, fieldMaxValue=10.0, value=5.0)
        cmds.floatSliderGrp('MAX_SCALE', label='最大比例', field=True, minValue=0.1, maxValue=100.0, fieldMinValue=0.1, fieldMaxValue=10.0, value=10.0)
        cmds.intSliderGrp('MIN_DIV', label='最小分割', field=True, minValue=1, maxValue=100, fieldMinValue=1, fieldMaxValue=100, value=2)
        cmds.intSliderGrp('MAX_DIV', label='最大分割', field=True, minValue=1, maxValue=100, fieldMinValue=1, fieldMaxValue=100, value=2)

        cmds.separator(h=10, st='in')
        cmds.button(
            label="CUT",
            width=400,
            height=35,
            command=lambda x: self.setCutMode(
                cmds.checkBox('PREVIEW', query=True, v=True),  # value1=True 意味着查询第一个checkbox
                cmds.checkBox('SINGLE_MODE', query=True, v=True),
                cmds.checkBox('USE_PLANE', query=True, v=True),
                cmds.checkBox('FLAT', query=True, v=True),
                cmds.checkBox('RESULT_ONLY', query=True, v=True),
                cmds.checkBox('LEGACY', query=True, v=True),
                cmds.floatSliderGrp('MIN_SCALE', query=True, value=True),
                cmds.floatSliderGrp('MAX_SCALE', query=True, value=True),
                cmds.intSliderGrp('MIN_DIV', query=True, value=True),
                cmds.intSliderGrp('MAX_DIV', query=True, value=True)
            ),
            annotation="DO IT!!!"
        )

        # cmds.button(label="Check Status", command=lambda x: self.print_checkbox_status(preview_model_id))
        cmds.text("showInfo", l='maya separate plugin v1.0', w=370, h=30, ww=True, fn="smallPlainLabelFont")
        # 显示窗口
        cmds.showWindow("windowUI")
        cmds.setParent("..")

    def pl_vector(self):
        '''
        计算在 Maya 中选择的多边形的法线方向，并基于该法线生成一个局部坐标系
        :return:X 代表沿法线方向的横向（类似于切线方向？），
                Y 代表加工后的纵向，
                Z 是法线方向，
                pos 是当前工具的位置。
        '''
        # 切换到选择工具和移动工具
        Y = [0, 1, 0]
        # 获取当前移动工具的坐标
        pos = cmds.manipMoveContext('Move', q=True, p=True)
        # 获取多边形每个顶点的法线
        nms = cmds.polyNormalPerVertex(q=True, xyz=True)
        Z = [0, 0, 0]
        # 将法线值累加到 Z 向量中
        for i in range(0, len(nms), 3):
            Z[0] += nms[i]
            Z[1] += nms[i + 1]
            Z[2] += nms[i + 2]
        if Z == [0, 0, 0]:
            Z = [0, 0, 1]
        else:  # 将Z向量进行归一化处理
            norm_Z = (Z[0] ** 2 + Z[1] ** 2 + Z[2] ** 2) ** 0.5
            Z = [Z[0] / norm_Z, Z[1] / norm_Z, Z[2] / norm_Z]

        if all(abs(Y[j]) == abs(Z[j]) for j in range(3)):
            Y = [1, 0, 0]  # 替代 Y 向量

        # 计算 X 向量
        X = [
            Y[1] * Z[2] - Y[2] * Z[1],
            Y[2] * Z[0] - Y[0] * Z[2],
            Y[0] * Z[1] - Y[1] * Z[0]
        ]

        # 将 X 向量归一化
        norm_X = (X[0] ** 2 + X[1] ** 2 + X[2] ** 2) ** 0.5
        X = [X[0] / norm_X, X[1] / norm_X, X[2] / norm_X]

        # 重新计算 Y 向量
        Y = [
            Z[1] * X[2] - Z[2] * X[1],
            Z[2] * X[0] - Z[0] * X[2],
            Z[0] * X[1] - Z[1] * X[0]
        ]

        # 将 Y 向量归一化
        norm_Y = (Y[0] ** 2 + Y[1] ** 2 + Y[2] ** 2) ** 0.5
        Y = [Y[0] / norm_Y, Y[1] / norm_Y, Y[2] / norm_Y]

        # 返回 X、Y、Z 向量和位置的组合
        return [X[0], X[1], X[2], 0, Y[0], Y[1], Y[2], 0, Z[0], Z[1], Z[2], 0, pos[0], pos[1], pos[2], 1]

    def pl_bbox_comp(self):
        bb = cmds.polyEvaluate(bc=True)  # 比如((-5.0, 5.0), (-5.0, -5.0), (-5.0, 5.0))
        print("bb", bb)
        width = bb[0][1] - bb[0][0]  # x 最大值 - x 最小值
        height = bb[1][1] - bb[1][0]  # y 最大值 - y 最小值
        depth = bb[2][1] - bb[2][0]  # z 最大值 - z 最小值
        return [width, height, depth]

    def pl_chipOffsphere(self, minScale, maxScale, minDiv, maxDiv, singleMode, name):
        self.showMsg("pl_chipOffsphere", [0.2, 0.2, 0.2])
        # 生成一个变形，加noise的球体
        if not cmds.objExists("Chips_pl_chipOff"):
            shader = cmds.shadingNode("lambert", asShader=True, name="Chips_pl_chipOff")
            cmds.setAttr(shader + ".transparency", 0.8, 0.8, 0.8, type="double3")
        X, YZ = 0, 0

        if singleMode > 0: # singleMode下，会考虑选中的所有顶点，并且根据这些顶点的位置来计算球体的大小
            bb = self.pl_bbox_comp()
            if -1 < bb[0] < 1: bb[0] = -1
            if -1 < bb[1] < 1: bb[1] = 1
            if -1 < bb[2] < 1: bb[2] = 1
            YZ = sum(bb)
            X = -0.5 * YZ
        else:
            YZ = random.uniform(minScale, maxScale)
            X = 0.5 * YZ
        div = random.randint(minDiv, maxDiv)
        cube = cmds.polyCube(width=1, height=1, depth=1, sx=1, sy=1, sz=1, ax=(0, 1, 0), ch=True, name=name + "_pl_sphere1")[0]
        geo = cmds.listRelatives(cube, allDescendents=True, fullPath=True)
        cmds.hyperShade(assign="Chips_pl_chipOff")
        cmds.move(0, 0, -0.15, r=True, os=True)
        cmds.move(0, 0, 0.15)
        cmds.makeIdentity(cube, apply=True, translate=True, rotate=False, scale=False, normal=False, pn=1)  # pn=1 意味着应用父节点的变化
        cmds.polySmooth(cube, mth=0, dv=3, bnr=1, c=1, kb=0, ksb=1, khe=0, kt=1, kmb=1, suv=0, peh=0, sl=1, dpe=1,
                        ps=0.1, ro=1, ch=1)  #  参数太多了，看结果就行，后面有需求再进行补充
        cmds.scale(100, 100, 100, cube, a=True)
        cmds.polyMoveFacet(cube, ch=True, random=10, ltz=(4.5 / div))  # cmds.polyMoveFacet 是 Maya 中用于移动多边形面的命令,ch=True 意味着创建历史记录,random=10 意味着随机移动10个单位,ltz=(4.5 / div) 意味着在Z轴上移动4.5/div个单位
        cmds.scale(1, 1, 1, cube, a=True)
        cmds.ConvertSelectionToUVs()  # 将当前选中的对象（如多边形面、点等）转换为其对应的 UV 坐标选择
        cmds.polyEditUV(u=0, v=2) # 将V坐标移动到2

        allHistory = cmds.listHistory(cube)
        polyCube = cmds.ls(allHistory, type="polyCube")
        noiseNode = cmds.ls(allHistory, type="polyMoveFace")
        polySmooth = cmds.ls(allHistory, type="polySmoothFace")
        # 从历史记录当中拿出数据，做进一步处理
        # 添加属性并获取初始值
        if polyCube:
            cmds.addAttr(cube, longName="width", keyable=True, at="double", dv=cmds.getAttr(f"{polyCube[0]}.width"))
            cmds.addAttr(cube, longName="height", keyable=True, at="double",
                         dv=cmds.getAttr(f"{polyCube[0]}.height"))
            cmds.addAttr(cube, longName="depth", keyable=True, at="double", dv=cmds.getAttr(f"{polyCube[0]}.depth"))
            cmds.addAttr(cube, longName="subdivisionsWidth", keyable=True, at="long",
                         dv=cmds.getAttr(f"{polyCube[0]}.subdivisionsWidth"))
            cmds.addAttr(cube, longName="subdivisionsHeight", keyable=True, at="long",
                         dv=cmds.getAttr(f"{polyCube[0]}.subdivisionsHeight"))
            cmds.addAttr(cube, longName="subdivisionsDepth", keyable=True, at="long",
                         dv=cmds.getAttr(f"{polyCube[0]}.subdivisionsDepth"))

        # 假设 $div 是一个已定义的变量
        cmds.addAttr(cube, longName="divisions", keyable=True, at="long", dv=int(div))

        # 添加噪声属性
        if noiseNode:
            cmds.addAttr(cube, longName="noise", keyable=True, at="double",
                         dv=cmds.getAttr(f"{noiseNode[0]}.localTranslateZ"))

        # 连接属性,todo:现在CUT预览之后结果是不能修改的，后面可以改成用户可以对结果进行修改
        if polyCube:
            cmds.connectAttr(f"{cube}.width", f"{polyCube[0]}.width")
            cmds.connectAttr(f"{cube}.height", f"{polyCube[0]}.height", force=True)
            cmds.connectAttr(f"{cube}.depth", f"{polyCube[0]}.depth", force=True)
            cmds.connectAttr(f"{cube}.subdivisionsWidth", f"{polyCube[0]}.subdivisionsWidth", force=True)
            cmds.connectAttr(f"{cube}.subdivisionsHeight", f"{polyCube[0]}.subdivisionsHeight", force=True)
            cmds.connectAttr(f"{cube}.subdivisionsDepth", f"{polyCube[0]}.subdivisionsDepth", force=True)

        if polySmooth:
            cmds.connectAttr(f"{cube}.divisions", f"{polySmooth[0]}.divisions", force=True)

        if noiseNode:
            cmds.connectAttr(f"{cube}.noise", f"{noiseNode[0]}.localTranslateZ", force=True)

        cmds.scale(YZ, YZ, X, geo[0], r=True)
        cmds.select(geo[0])

        return geo[0]


    def pl_chipOffshatterBy(self):
        print("pl_chipOffshatterBy!!!!")


    def setCutMode(self, preview, single_mode, use_plane, flat, result_only, legacy, min_scale, max_scale, min_div,
                     max_div):
        # 这里是处理按钮点击后逻辑的地方
        print("Button clicked with parameters:")
        print(f"Preview: {preview}, Single Mode: {single_mode}, Use Plane: {use_plane}, Flat: {flat}")
        print(
            f"Result Only: {result_only}, Legacy: {legacy}, Min Scale: {min_scale}, Max Scale: {max_scale}, Min Div: {min_div}, Max Div: {max_div}")

        # 注：明天主要补充这里面的代码
        # 获取当前选中的对象及其完整路径
        selected = cmds.ls(selection=True, flatten=True, long=True)
        size_selected = len(selected) # 获取选中对象的数量

        # 获取当前选中的所有对象及其形状
        # flatten=True 意味着返回一个扁平列表，而不是一个嵌套列表,当设置为 True 时，返回的结果将是一个展平的列表。如果你选择了一个层次结构（例如，一个组节点及其子节点），启用 flatten 会将所有选中的子节点合并到同一个列表中，而不是保留层次结构。
        all_shapes = cmds.ls(selection=True, flatten=True, long=True, objectsOnly=True) # 获取结果例如：['|pCube1|pCubeShape1']
        # 列出所有形状对象的父变换节点,这个函数接口也可以用来获取孩子节点，兄弟节点
        all_trans = cmds.listRelatives(all_shapes, parent=True, type="transform") if all_shapes else [] # 获取结果例如：['pCube1']
        # 使用正则表达式替换匹配到的部分
        if all_trans:
            # 获取第一个变换节点
            first_trans = all_trans[0]

            # 使用正则表达式匹配并进行替换
            match_pattern = re.search(r"_pl_chunk.*", first_trans)  # 如果你正在处理场景中的对象，并且看到有 _pl_chunk 后缀的对象，这意味着这些对象很可能是在某个过程中生成或转换出的特定数据块，例如在进行切割、分割或物体拆分时产生的效果。
            if match_pattern:
                first_trans = first_trans.replace(match_pattern.group(), "")

            # 更新 all_trans 列表中的第一个元素
            all_trans[0] = first_trans

        # 假设 all_shapes 是已定义的几何体列表
        all_shapes = cmds.ls(selection=True, flatten=True, long=True, objectsOnly=True)
        print("all_shapes,", all_shapes)  # all_shapes, |pCube2|pCube3 (此时pCube3是pCube2的子节点，并且比如pCube1是隐藏的，就不会显示)

        all_trans_full = cmds.listRelatives(all_shapes, fullPath=True, parent=True,
                                            type="transform") if all_shapes else []
        print("all_trans_full,", all_trans_full)  # all_trans_full, ['|pCube2']
        checker = 1 if (size_selected == 1 and cmds.nodeType(selected[0]) == "transform") else 0
        # 比如说在点模式下选择了Cube的四个点，那么checker=0，并且cmds.nodeType(selected[0])是mesh，all_trans_full倒是依然是['|pCube2']
        size_sel = 1 if (single_mode > 0) else size_selected
        chunk = []
        self.showMsg(checker, [0.2, 0.2, 0.2])
        print("selected[0]", selected[0], cmds.nodeType(selected[0]))
        if checker > 0:
            self.showMsg("选择的物体：" + selected[0], [0.2, 0.2, 0.2])
            selected = cmds.ls(selection=True)  # 获取当前选择的对象
            all_trans = cmds.ls(long=True, selection=True)  # 长名称列表
            if all_trans:  # 确保存在选中的对象
                # 替换字符串
                all_trans[0] = all_trans[0].replace(all_trans[0].split('|')[-1], '')  # 去掉最后一个管道符分隔的部分
                all_trans[0] = all_trans[0].replace('_pl_chunk', '')  # 替换掉 "_pl_chunk"
                all_trans_full = selected  # 保存原始选择

        if selected and ('.' in selected[0] or (checker > 0 and use_plane > 0)):  # 当比如选择了四个点之后，'.' in selected[0]就满足了
            if not cmds.objExists("pl_chipOff_GRP") and not cmds.objExists(all_trans[0] + "_pl_chipOff"):
                cmds.createNode("transform", name="pl_chipOff_GRP")

            if not cmds.objExists(all_trans[0] + "_pl_chipOff"):
                cmds.createNode("transform", name=all_trans[0] + "_pl_chipOff", parent="pl_chipOff_GRP")

            chunk = []
            for i in range(size_sel):
                chipObj = ""
                if single_mode > 0:
                    cmds.select(selected)
                else:
                    cmds.select(selected[i])
                trot = self.pl_vector()

                # todo: 暂时先不管plane的情况，就用变形的cube切
                if use_plane > 0:
                    pass
                else:
                    self.pl_chipOffsphere(min_scale, max_scale, min_div, max_div, single_mode, all_trans[0])

                if checker > 0:
                    pos = cmds.getAttr(selected[0] + ".center")
                    bb = cmds.getAttr(selected[0] + ".boundingBoxSize")
                    scale = bb[0] + bb[1] + bb[2]
                    cmds.move(pos[0], pos[1], pos[2])
                    cmds.scale(scale, scale, scale)
                else:
                    cmds.pickWalk(direction='up')  # cmds.pickWalk 是一个非常有用的命令，用于在场景中的选择元素之间进行导航。这个命令允许用户通过逐步选择相邻的组件（如顶点、边或面）来快速地在模型中移动选择。
                    # pickWalk, 比如'up': 向上选择相邻的父级（例如，从面选择到相应的多边形物体）。
                    # cmds.xform(relative=True, matrix=trot)  # 使用 trot 的值进行变换
                    print("trot", trot)
                    cmds.xform(relative=True, matrix=trot)

                # 获取当前选择的对象
                selected_objects = cmds.ls(selection=True, long=True)

                # 目标对象名称
                target_object = f"{all_trans[0]}_pl_chipOff"
                # 选择目标对象，如果它存在
                if cmds.objExists(target_object):
                    cmds.select(selected_objects + [target_object], replace=True)

                # 尝试进行父级连接并捕获异常
                try:
                    cmds.parent()  # 也就是说做一个父子关系的绑定，让那几个生成的Cube绑定在父节点下面
                except Exception as e:
                    pass  # 忽略任何异常
                # 获取当前选择的对象并转换为字符串
                achunk = "".join(cmds.ls(selection=True, long=True))
                chunk.append(achunk)

            # print("chunk!!!", chunk)  # ['|pl_chipOff_GRP|pCube2_pl_chipOff|pCube2_pl_sphere1', '|pl_chipOff_GRP|pCube2_pl_chipOff|pCube2_pl_sphere2', '|pl_chipOff_GRP|pCube2_pl_chipOff|pCube2_pl_sphere3', '|pl_chipOff_GRP|pCube2_pl_chipOff|pCube2_pl_sphere4']
            cmds.select(all_trans_full + chunk, replace=True)  # 将两个列表合并并选中，将 replace 参数设为 True 时，这意味着你希望用新的选择替换掉当前已经选中的对象
            if preview == 0:
                self.pl_chipOffshatterBy()
        else:  # 第二次点击CUT按钮，会进入else
            print("now in else!!!")
            self.pl_chipOffshatterBy()


    def showMsg(self, msg, color):
        # 显示对应的message在"showInfo"文本中，颜色为color
        cmds.text("showInfo", e=True, l=msg, bgc=color)

    def selectBaseObject(self, *args):
        selectedObject = cmds.ls(sl=True, tr=True)  # tr=True 意味着只选择transform节点, 当设置为True时，返回的结果将仅包括选定对象的变换节点。如果选择的是一个多层次的对象（例如，一个组或一个模型），那么该选项确保你只获得与变换相关的节点，而不是它们的子组件（如顶点、边或面）。
        if len(selectedObject) > 1 or len(selectedObject) == 0:
            cmds.textField("baseObject", e=True, tx="Please select only one object")
        else:
            self.baseObject = selectedObject[0]
            cmds.textField("baseObject", e=True, tx=self.baseObject)



UVToolKit()