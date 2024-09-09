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
                cmds.checkBoxGrp('PREVIEW', query=True, value1=True),
                cmds.checkBoxGrp('SINGLE_MODE', query=True, value1=True),
                cmds.checkBoxGrp('USE_PLANE', query=True, value1=True),
                cmds.checkBoxGrp('FLAT', query=True, value1=True),
                cmds.checkBoxGrp('RESULT_ONLY', query=True, value1=True),
                cmds.checkBoxGrp('LEGACY', query=True, value1=True),
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

    # 假设这个函数已经定义
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

        # 获取所有相关变换节点的完整路径
        all_trans_full = cmds.listRelatives(all_shapes, fullPath=True, parent=True,
                                            type="transform") if all_shapes else []
        checker = 1 if (size_selected == 1 and cmds.nodeType(selected[0]) == "transform") else 0
        size_sel = 1 if (single_mode > 0) else size_selected
        chunk = []
        self.showMsg(checker, [0.2, 0.2, 0.2])
        if checker > 0:
            print(selected[0]) # 比如：|pCube1
            self.showMsg(selected[0], [0.2, 0.2, 0.2])


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