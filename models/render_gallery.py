# Renders each candidate game model alone (its own texture where the game data names one, grey otherwise) for choosing kit-bash pieces.
import bpy, math, json, addon_utils
from mathutils import Vector
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
W = 'E:/Claude/Kenshi/mod-builder/operating-tables/models/'
K = 'E:/SteamLibrary/steamapps/common/Kenshi/'
c = json.load(open(W + 'ref/candidates.json'))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 500; sc.render.resolution_y = 400
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.type = 'ORTHO'
for name, v in c.items():
    for o in list(bpy.data.objects):
        if o is not co: bpy.data.objects.remove(o)
    before = set(bpy.data.objects)
    try:
        IMP.kenshi_ogre_objects(filepath=K + v['mesh'], import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    except Exception as e:
        print('FAIL', name, e); continue
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    m = bpy.data.materials.new(name); m.use_nodes = True
    if v.get('png'):
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + v['png'])
        m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    for o in objs: o.data.materials.clear(); o.data.materials.append(m)
    pts = [o.matrix_world @ Vector(b) for o in objs for b in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (mn + mx) / 2; size = max((mx - mn).length, 1)
    print('SIZE', name, [round(x, 1) for x in (mx - mn)])
    cam.ortho_scale = size * 1.1
    a = math.radians(35); e = math.radians(28); r = size * 3
    co.location = (ctr.x + r * math.sin(a) * math.cos(e), ctr.y - r * math.cos(a) * math.cos(e), ctr.z + r * math.sin(e))
    co.rotation_euler = (math.radians(90) - e, 0, a)
    cam.clip_end = r * 4
    sc.render.filepath = W + 'gallery/' + name + '.png'; bpy.ops.render.render(write_still=True)
print('DONE')
