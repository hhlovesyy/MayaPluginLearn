from maya import cmds
# Duplicate pCube1 over surface.
# cmds.duplicateOverSurface("pCone1")

# Duplicate selected object over surface.
# cmds.duplicateOverSurface(cmds.ls(sl=True, long=True)[0], rotation=True, instanceLeaf=True)

# Duplicate selected object over surface but keep original rotations.
cmds.MyDuplicateOverSurface("pTorus1", rotation=True, instanceLeaf=True)

# 停止使用插件
# cmds.unloadPlugin("duplicateOverSurface")
# -r -s True False