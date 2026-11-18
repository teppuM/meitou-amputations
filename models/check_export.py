# Imports the exported model files back (with the Skeleton Repair Bed's own base for the skeleton bed) and renders them, to check the export.
import bpy, math, addon_utils, xml.dom.minidom
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
D = 'E:/Claude/Kenshi/mod-builder/operating-tables/dist/'
W = 'E:/Claude/Kenshi/mod-builder/operating-tables/models/'
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/buildings/furniture/new_furniture01/'
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
def load(path, png, dx=0):
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=path, import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    m = bpy.data.materials.new(png); m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + png)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    for o in bpy.data.objects:
        if o not in before and o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(m); o.location.x += dx
            print('LOADED', path.split('/')[-1], len(o.data.vertices), 'verts')
load(D + 'optab_table_atlas.mesh', 'ref/props_atlas_rgb.png')
load(D + 'optab_table_crate.mesh', 'ref/tex/medicrate_d.png')
load(K + 'Robot Repair Bed.mesh', 'ref/robotics_bench_rgb.png', 55)
load(D + 'optab_skel_atlas.mesh', 'ref/props_atlas_rgb.png', 55)
load(D + 'optab_skel_bench.mesh', 'ref/tex/ATLAS_interior.png', 55)
load(D + 'optab_skel_limbs.mesh', 'ref/tex/BENCH Robot Limbs_DIF.png', 55)
for f in ('optab_table_COL.xml', 'optab_skel_COL.xml'):
    print('COLLISION', f, xml.dom.minidom.parse(D + f).toxml()[:0], open(D + f).read().count('<'), 'tags')
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 1400; sc.render.resolution_y = 600
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'; cam.ortho_scale = 105
a = math.radians(30); e = math.radians(28); r = 250
co.location = (28 + r * math.sin(a) * math.cos(e), -r * math.cos(a) * math.cos(e), 7 + r * math.sin(e)); co.rotation_euler = (math.radians(90) - e, 0, a)
cam.clip_end = 1000
sc.render.filepath = W + 'draft2/export_check.png'; bpy.ops.render.render(write_still=True)
print('DONE')
