import bpy, os, math, addon_utils
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/buildings/furniture/new_furniture01/'
W = 'E:/Claude/Kenshi/mods/OperatingTables/models/'
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
def load(name, tex):
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=K + name, import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + 'ref/' + tex)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(m)
        bb = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
        print('OBJ', name, o.name, len(o.data.vertices), 'verts', len(o.data.polygons), 'faces', 'min', [round(x,2) for x in mn], 'max', [round(x,2) for x in mx])
    return objs
a = load('bed1.mesh', 'props_atlas.png')
b = load('Robot Repair Bed.mesh', 'robotics_bench.png')
for o in b: o.location.x += 40
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 1100; sc.render.resolution_y = 600
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'; cam.ortho_scale = 80
for tag, ang, el in [('front', 35, 30), ('side', 120, 25), ('top', 35, 75)]:
    a_ = math.radians(ang); e = math.radians(el); r = 120
    co.location = (20 + r*math.sin(a_)*math.cos(e), -r*math.cos(a_)*math.cos(e), r*math.sin(e))
    co.rotation_euler = (math.radians(90) - e, 0, a_)
    sc.render.filepath = W + f'ref/vanilla_{tag}.png'; bpy.ops.render.render(write_still=True)
print('DONE')
