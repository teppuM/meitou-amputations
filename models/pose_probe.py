import bpy, math, addon_utils
from mathutils import Vector
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
IMP.kenshi_ogre_objects(filepath='E:/Claude/Kenshi/tools/clothing-test/cache/hum/human_male.mesh', import_animations=True, create_materials=True, cleanup_vertices='DEFAULT', import_shapekeys=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print('ACTS', [a.name for a in bpy.data.actions if 'sleep' in a.name.lower() or 'bed' in a.name.lower()])
act = bpy.data.actions['sleepinbed']
arm.animation_data.action = act
if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
print('RANGE', act.frame_range)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 700; sc.render.resolution_y = 500
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'; cam.ortho_scale = 34
for frac in (0.0, 0.5, 0.95):
    f0, f1 = act.frame_range; sc.frame_set(int(round(f0 + (f1 - f0) * frac))); bpy.context.view_layer.update()
    pel = arm.matrix_world @ arm.pose.bones['Bip01 Pelvis'].head
    print('PELVIS', frac, [round(x, 1) for x in pel])
    a = math.radians(35); e = math.radians(30); r = 80
    co.location = (pel.x + r*math.sin(a)*math.cos(e), pel.y - r*math.cos(a)*math.cos(e), pel.z + r*math.sin(e)); co.rotation_euler = (math.radians(90)-e, 0, a)
    sc.render.filepath = f'E:/Claude/Kenshi/mod-builder/operating-tables/models/draft/pose_{int(frac*100)}.png'; bpy.ops.render.render(write_still=True)
