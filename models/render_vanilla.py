# Renders the game's Bed and Skeleton Repair Bed from the same cameras as build_tables.py's 'table' and 'skeleton' shots, for comparison.
import bpy, math, addon_utils
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/buildings/furniture/new_furniture01/'
W = 'E:/Claude/Kenshi/mods/OperatingTables/models/'
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
def load(name, tex, dx):
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=K + name, import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + 'ref/' + tex)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    for o in bpy.data.objects:
        if o not in before and o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(m); o.location.x += dx
load('bed1.mesh', 'props_atlas_rgb.png', 0)
load('Robot Repair Bed.mesh', 'robotics_bench_rgb.png', 45)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_shadows = True
sc.render.resolution_x = 1200; sc.render.resolution_y = 650
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'
def shot(tag, cx, ang, el, scale):
    cam.ortho_scale = scale
    a = math.radians(ang); e = math.radians(el); r = 150
    co.location = (cx + r * math.sin(a) * math.cos(e), -r * math.cos(a) * math.cos(e), 6 + r * math.sin(e))
    co.rotation_euler = (math.radians(90) - e, 0, a)
    sc.render.filepath = W + f'draft/vanilla_{tag}.png'; bpy.ops.render.render(write_still=True)
shot('table', 0, 35, 30, 42)
shot('skeleton', 45, 35, 28, 46)
print('DONE')
