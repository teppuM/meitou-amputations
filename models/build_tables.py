# Draft models for the Operating Tables mod, built from the game's Bed (bed1.mesh) and Skeleton Repair Bed (Robot Repair Bed.mesh).
# Operating Table: the Bed's frame raised to table height, its planks and bedding replaced by a padded top with a head cushion and three leather
# straps; an instrument tray on a stand with a saw and a knife; a bucket underneath. Textured from the game's furniture atlas (props_atlas_regular).
# Skeleton Operating Bed: the Skeleton Repair Bed unchanged, plus a separate part: a post at the foot with an arm reaching over the bed that holds a
# circular saw, and clamp bars across the arms and legs. Textured from the same furniture atlas.
# Draft stage: renders only (OUT/draft_*.png) and a .blend; no export yet. Run: blender -b --factory-startup -P build_tables.py
import bpy, bmesh, math, os, addon_utils
from mathutils import Vector

addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/'
W = 'E:/Claude/Kenshi/mod-builder/operating-tables/models/'
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

RAISE = 1.3          # the Bed's frame height times this: top at about 8 units (80 cm)
ATLAS_W, ATLAS_H = 512, 4096

# Atlas regions in pixels (x0, y0, x1, y1), y from the top of the 512 x 4096 furniture atlas.
CUSHION = (40, 2048 + 60, 470, 2048 + 470)      # stitched canvas pad
STRAP = (420, 3072 + 150, 505, 3072 + 620)      # brown leather strip
STEEL = (10, 3072 + 140, 400, 3072 + 400)       # blue-grey sheet metal
RUST = (10, 3072 + 420, 400, 3072 + 630)        # rusty iron
WOOD = (10, 1024 + 600, 500, 1024 + 760)        # planks
BLADE = (90, 640, 232, 790)                      # round bolted flange (col 1)
PLATE = (10, 10, 500, 480)                       # riveted rusty plate


def mat(name, png):
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + 'ref/' + png)
    m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m


UV_NAME = 'UVMap'
ATLAS = mat('atlas', 'props_atlas_rgb.png')     # the game's alpha channel is not see-through; dropped for the render
ROBO = mat('robo', 'robotics_bench_rgb.png')


def import_mesh(path):
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=K + path, import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    return [o for o in bpy.data.objects if o not in before and o.type == 'MESH'][0]


def map_uv(obj, region):
    """Every face's UVs stretched over one atlas region, by the face's own two longest axes."""
    x0, y0, x1, y1 = region
    u0, u1 = x0 / ATLAS_W, x1 / ATLAS_W
    v0, v1 = 1 - y1 / ATLAS_H, 1 - y0 / ATLAS_H
    me = obj.data
    uv = me.uv_layers.new(name=UV_NAME) if not me.uv_layers else me.uv_layers[0]
    uv.name = UV_NAME          # the imported mesh's layer name, so joined pieces share one layer
    for f in me.polygons:
        n = f.normal
        axes = sorted(range(3), key=lambda i: abs(n[i]))[:2]
        pts = [me.vertices[me.loops[li].vertex_index].co for li in f.loop_indices]
        lo = [min(p[a] for p in pts) for a in axes]; hi = [max(p[a] for p in pts) for a in axes]
        for li in f.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            s = (p[axes[0]] - lo[0]) / max(hi[0] - lo[0], 1e-6); t = (p[axes[1]] - lo[1]) / max(hi[1] - lo[1], 1e-6)
            uv.data[li].uv = (u0 + (u1 - u0) * s, v0 + (v1 - v0) * t)


def box(name, size, at, region, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    map_uv(o, region); o.data.materials.append(ATLAS)
    return o


def cyl(name, r, h, at, region, rot=(0, 0, 0), n=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h, location=at, rotation=rot)
    o = bpy.context.object; o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    map_uv(o, region); o.data.materials.append(ATLAS)
    return o


def operating_table():
    global UV_NAME
    bed = import_mesh('buildings/furniture/new_furniture01/bed1.mesh')
    bed.name = 'operating_table_frame'
    UV_NAME = bed.data.uv_layers.active.name
    bed.data.materials.clear(); bed.data.materials.append(ATLAS)
    bm = bmesh.new(); bm.from_mesh(bed.data)
    # Drop the bedding: the long planks, the two cover halves and the small decals above the cross slats (everything starting above z 5.15).
    comps, seen = [], set()
    for v in bm.verts:
        if v in seen: continue
        stack, comp = [v], []
        while stack:
            x = stack.pop()
            if x in seen: continue
            seen.add(x); comp.append(x); stack += [e.other_vert(x) for e in x.link_edges]
        comps.append(comp)
    drop = [v for c in comps if min(x.co.z for x in c) > 5.15 for v in c]
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    # Raise to table height, and cut the four bedposts off at the top.
    for v in bm.verts:
        v.co.z = min(v.co.z * RAISE, 5.25 * RAISE)
    bm.to_mesh(bed.data); bm.free()
    top = 5.25 * RAISE
    parts = [bed,
             box('pad', (24.4, 14.2, 1.0), (0, 0, top + 0.5), CUSHION),
             box('head_cushion', (4.0, 8.0, 0.9), (-10.0, 0, top + 1.3), CUSHION)]
    for i, x in enumerate((-4.5, 2.0, 8.0)):           # chest, hips, knees
        parts.append(box(f'strap{i}', (1.1, 14.6, 1.25), (x, 0, top + 0.55), STRAP))
    # The instrument tray at the foot corner, on a stand, with a saw and a knife; a bucket under the middle.
    tx, ty = 15.5, 6.5
    parts += [box('tray_post', (0.7, 0.7, top + 0.4), (tx, ty, (top + 0.4) / 2), STEEL),
              box('tray_foot', (4.0, 4.0, 0.4), (tx, ty, 0.2), STEEL),
              box('tray', (5.0, 7.0, 0.35), (tx, ty, top + 0.6), STEEL),
              box('tray_lip', (5.0, 7.0, 0.5), (tx, ty, top + 0.95), STEEL),
              box('saw_blade', (0.15, 4.2, 1.1), (tx - 0.8, ty - 0.6, top + 1.4), PLATE, rot=(0, math.radians(90), 0)),
              box('saw_handle', (0.6, 1.6, 0.6), (tx - 0.8, ty + 2.2, top + 1.25), WOOD),
              box('knife', (0.15, 2.6, 0.5), (tx + 1.2, ty + 0.4, top + 1.2), STEEL, rot=(0, math.radians(90), 0)),
              box('knife_handle', (0.45, 1.1, 0.45), (tx + 1.2, ty + 2.2, top + 1.2), WOOD),
              cyl('bucket', 1.9, 2.6, (2.0, 0, 1.3), RUST)]
    # Inner lid to hide the bucket's open top is not needed: the cylinder is closed.
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = bed
    bpy.ops.object.join()
    bed.name = 'operating_table'
    return bed, top


def skeleton_bed():
    global UV_NAME
    base = import_mesh('buildings/furniture/new_furniture01/Robot Repair Bed.mesh')
    UV_NAME = base.data.uv_layers.active.name
    base.name = 'skeleton_operating_bed_base'
    base.data.materials.clear(); base.data.materials.append(ROBO)
    # The saw: a post beside the foot, an arm over the bed's middle, a short drop and a circular blade; clamp bars across the arm and leg rests.
    top = 7.0
    px, py = 11.0, -10.6
    parts = [box('saw_post', (1.4, 1.4, 16.0), (px, py, 8.0), STEEL),
             box('saw_foot', (4.0, 4.0, 0.6), (px, py, 0.3), STEEL),
             box('saw_arm', (1.2, 8.8, 1.2), (px, py + 3.9, 15.4), STEEL),
             box('saw_joint', (2.0, 2.0, 2.0), (px, py, 15.4), RUST),
             box('saw_drop', (0.9, 0.9, 3.0), (px, py + 7.8, 13.4), STEEL),
             box('saw_motor', (1.8, 2.4, 1.8), (px, py + 7.8, 11.4), RUST),
             cyl('saw_blade', 2.8, 0.2, (px - 2.2, py + 7.8, 11.0), BLADE, rot=(0, math.radians(90), 0), n=28)]
    for i, x in enumerate((-6.0, 1.0, 7.5)):
        parts.append(box(f'clamp{i}', (1.0, 15.0, 0.7), (x, -0.6, top + 0.35), RUST))
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    saw = bpy.context.object; saw.name = 'skeleton_operating_bed_saw'
    return [base, saw], top


HUM = 'E:/Claude/Kenshi/tools/clothing-test/cache/hum/'   # the body and skeleton, copied from the install for reference only


def figure(at, top, frac=0.5):
    """A human in the game's own 'sleepinbed' animation (the clip a bed's occupant plays), its pelvis put over the table's middle, for scale."""
    bpy.ops.object.select_all(action='DESELECT')
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=HUM + 'human_male.mesh', import_animations=True, create_materials=True, cleanup_vertices='DEFAULT',
                            import_shapekeys=False)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    for o in new:
        if o.type == 'MESH':
            o.data.materials.clear(); m = bpy.data.materials.new('skin'); m.diffuse_color = (0.6, 0.45, 0.35, 1); o.data.materials.append(m)
    for o in new:                      # carried with the skeleton when it is moved (the import links them by modifier only)
        if o.type == 'MESH' and o.parent is None:
            o.parent = arm; o.matrix_parent_inverse = arm.matrix_world.inverted()
    act = bpy.data.actions['sleepinbed']
    if not arm.animation_data: arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    bpy.context.scene.frame_set(int(round(f0 + (f1 - f0) * frac)))
    bpy.context.view_layer.update()
    return new, arm


def place(arm, bodies, at, top):
    """Turns the posed body so its head points to the table's -X end (the head cushion) and puts its pelvis over (at) at height top."""
    arm.rotation_euler.z = 0
    bpy.context.view_layer.update()
    pel = arm.matrix_world @ arm.pose.bones['Bip01 Pelvis'].head
    head = arm.matrix_world @ arm.pose.bones['Bip01 Head'].head
    d = head - pel
    arm.rotation_euler.z = math.pi - math.atan2(d.y, d.x)
    bpy.context.view_layer.update()
    pel = arm.matrix_world @ arm.pose.bones['Bip01 Pelvis'].head
    arm.location += Vector((at[0] - 1.5, at[1], top)) - pel
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    low = min((o.matrix_world @ v.co).z for o in bodies if o.type == 'MESH' for v in o.evaluated_get(dg).to_mesh().vertices)
    arm.location.z += top - 0.6 - low        # its back on the surface
    print('PLACED lowest', round(low, 2), 'surface', round(top - 0.6, 2))


table, ttop = operating_table()
skel, stop = skeleton_bed()
for o in skel: o.location.x += 45
fig1, arm1 = figure((0, 0), ttop + 1.0)
fig2 = []
place(arm1, fig1, (0, 0), ttop + 1.6)
for o in bpy.data.objects:
    if o.type == 'MESH':
        mn = Vector([min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
        mx = Vector([max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
        print('OBJ', o.name, len(o.data.vertices), 'verts', [round(a, 1) for a in mn], [round(a, 1) for a in mx])

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_shadows = True
sc.render.resolution_x = 1200; sc.render.resolution_y = 650
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'


def shot(tag, cx, ang, el, scale, figures_on=True):
    for f in fig1 + fig2: f.hide_render = not figures_on
    cam.ortho_scale = scale
    a = math.radians(ang); e = math.radians(el); r = 150
    co.location = (cx + r * math.sin(a) * math.cos(e), -r * math.cos(a) * math.cos(e), 6 + r * math.sin(e))
    co.rotation_euler = (math.radians(90) - e, 0, a)
    sc.render.filepath = W + f'draft/draft_{tag}.png'; bpy.ops.render.render(write_still=True)


os.makedirs(W + 'draft', exist_ok=True)
shot('pair', 22, 30, 28, 85, figures_on=False)
shot('table', 0, 35, 30, 42, figures_on=False)
shot('table_patient', 0, 35, 30, 42)
shot('skeleton', 45, 35, 28, 46, figures_on=False)
place(arm1, fig1, (45, 0), stop + 1.4)
shot('skeleton_patient', 45, 35, 28, 46)
shot('table_side', 0, 100, 15, 42, figures_on=False)
bpy.ops.wm.save_as_mainfile(filepath=W + 'draft/tables_draft.blend')
print('DONE')
