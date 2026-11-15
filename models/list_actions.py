import bpy, addon_utils
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
IMP.kenshi_ogre_objects(filepath='E:/Claude/Kenshi/tools/clothing-test/cache/hum/human_male.mesh', import_animations=True, create_materials=True, cleanup_vertices='DEFAULT', import_shapekeys=False)
print('ACTIONS', '|'.join(sorted(a.name for a in bpy.data.actions)))
