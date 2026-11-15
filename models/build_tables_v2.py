# Draft 2 of the Operating Tables models, kit-bashed from the game's own models (no new geometry except the leather straps).
# Operating Table (all on the furniture atlas, props_atlas_regular, like the Bed and the items): the Bed's frame and mattress raised to table height,
# three leather straps; at the foot a small table with a hacksaw, an angle grinder, pliers, medical supplies and a first-aid kit; a wooden bowl under
# the middle to catch blood; the standing strip light at the head as the surgery lamp; the medical crate beside the head (its own texture).
# Skeleton Operating Bed: the Skeleton Repair Bed; the boiler tank at the foot as its oil drum, joined by an exhaust pipe; the peeler blade stack at the
# side as the cutting tower; a metal table beside it with robot limb pieces, a robotics repair kit, a grinder and a wrench.
# Renders only (draft2/*.png). Run: blender -b --factory-startup -P build_tables_v2.py
import bpy, bmesh, math, os, addon_utils
from mathutils import Vector

addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/'
W = 'E:/Claude/Kenshi/mods/OperatingTables/models/'
OUT = W + 'draft2/'
os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

RAISE = 1.3
MATS = {}


def mat(png):
    if png not in MATS:
        m = bpy.data.materials.new(png); m.use_nodes = True
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(W + png)
        m.node_tree.links.new(t.outputs['Color'], m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        MATS[png] = m
    return MATS[png]


ATLAS = 'ref/props_atlas_rgb.png'
ROBO = 'ref/robotics_bench_rgb.png'


def piece(path, png, at=(0, 0, 0), rot=(0, 0, 0), scale=1.0, name=None):
    """A game model placed at (at), turned by rot (degrees about X, Y, Z) and scaled, with the texture its game record names."""
    bpy.ops.object.select_all(action='DESELECT')
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=K + path, import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(mat(png))
        o.rotation_euler = tuple(math.radians(r) for r in rot)
        o.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
        o.location = at
        if name: o.name = name
    bpy.context.view_layer.update()
    return objs[0]


def bounds(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def sit_on(o, z):
    """Drops or lifts o so its lowest point is at z."""
    bpy.context.view_layer.update()
    o.location.z += z - bounds(o)[0].z
    bpy.context.view_layer.update()


def strap(name, x, top, width, region=(420, 3072 + 150, 505, 3072 + 620)):
    """A leather strap over the mattress: a thin band arched across the table with its ends tucked down the sides (furniture atlas strap strip)."""
    bm = bmesh.new()
    n = 12
    half = width / 2
    prof = []
    for i in range(n + 1):
        y = -half - 0.5 + (width + 1.0) * i / n
        z = top + 0.35 * math.cos(math.pi * (i / n - 0.5)) if abs(y) < half else top - 1.4
        prof.append((y, z))
    t = 0.55
    for side in (-1, 1):
        for y, z in prof:
            bm.verts.new((x + side * t, y, z))
    bm.verts.ensure_lookup_table()
    for i in range(n):
        a, b2 = bm.verts[i], bm.verts[i + 1]
        c, d = bm.verts[n + 1 + i + 1], bm.verts[n + 1 + i]
        bm.faces.new((a, b2, c, d))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    uv = me.uv_layers.new(name='UVMap')
    x0, y0, x1, y1 = region
    for f in me.polygons:
        for k, li in enumerate(f.loop_indices):
            v = me.vertices[me.loops[li].vertex_index].co
            s = (v.y + half + 0.5) / (width + 1.0)
            uv.data[li].uv = (x0 / 512 + (x1 - x0) / 512 * (0 if v.x < x else 1), 1 - y1 / 4096 + (y1 - y0) / 4096 * s)
    me.materials.append(mat(ATLAS))
    mod = o.modifiers.new('thick', 'SOLIDIFY'); mod.thickness = 0.12
    return o


def operating_table():
    bed = piece('buildings/furniture/new_furniture01/bed1.mesh', ATLAS, name='table_frame')
    me = bed.data
    for v in me.vertices:
        v.co.z = v.co.z * RAISE if v.co.z <= 5.15 else v.co.z + 5.15 * (RAISE - 1)   # frame raised; mattress lifted with it, kept its own shape
    # Bedposts cut at the frame's top rail.
    for v in me.vertices:
        if (abs(v.co.x) > 10.9 and abs(v.co.y) > 6.4) and v.co.z > 5.6 * RAISE: v.co.z = 5.6 * RAISE
    me.update()
    top = max(v.co.z for v in me.vertices)
    parts = [bed]
    for i, x in enumerate((-3.0, 3.2, 8.4)):
        parts.append(strap(f'strap{i}', x, top, 13.6))
    # Instrument table at the foot, with tools; a bowl underneath; the lamp at the head; the medical crate beside the head.
    tray = piece('buildings/furniture/new_furniture01/small_table1.mesh', ATLAS, at=(19.5, 2.0, 0), rot=(0, 0, 90), name='instrument_table')
    sit_on(tray, 0)
    tt = bounds(tray)[1].z
    tools = [piece('items/meshes/Item_Hacksaw.mesh', ATLAS, at=(18.8, 0.0, 0), rot=(0, 0, 80)),
             piece('items/meshes/Item_Tools3.mesh', ATLAS, at=(20.6, 3.6, 0), rot=(0, 0, -30)),
             piece('items/meshes/Item_Tools.mesh', ATLAS, at=(18.4, 4.4, 0), rot=(0, 0, 15)),
             piece('items/meshes/Item_Medical_Supplies.mesh', ATLAS, at=(21.0, -0.6, 0), rot=(0, 0, 10)),
             piece('items/meshes/Item_Advanced_First_Aid_Kit.mesh', ATLAS, at=(20.4, 6.4, 0), rot=(0, 0, 95))]
    for t in tools: sit_on(t, tt)
    bowl = piece('items/meshes/Item_Bowl_Wood.mesh', ATLAS, at=(1.5, 0, 0), scale=1.6, name='blood_bowl'); sit_on(bowl, 0)
    lamp = piece('buildings/lights/strip_light1.mesh', ATLAS, at=(-15.5, -5.5, 0), name='surgery_lamp'); sit_on(lamp, 0)
    crate = piece('buildings/furniture/medicrate.mesh', 'ref/tex/medicrate_d.png', at=(-19.5, 6.5, 0), rot=(0, 0, 90), scale=0.45, name='medical_crate')
    sit_on(crate, 0)
    return parts + [tray, bowl, lamp, crate] + tools, top


def skeleton_bed(dx):
    base = piece('buildings/furniture/new_furniture01/Robot Repair Bed.mesh', ROBO, at=(dx, 0, 0), name='skeleton_bed_base')
    tank = piece('buildings/furniture/new_furniture01/boiler_tank1.mesh', ATLAS, at=(dx + 19.5, -4.0, 0), scale=0.7, name='oil_drum'); sit_on(tank, 0)
    pipe = piece('buildings/furniture/new_furniture01/exaust_pipe1.mesh', ATLAS, at=(dx + 15.5, -4.0, 4.0), rot=(0, 90, 0), scale=0.6, name='oil_pipe')
    blades = piece('buildings/furniture/new_furniture01/Peeler-Blade stack 01.mesh', 'ref/tex/Peeler_DIF_HI.png', at=(dx + 4.0, -12.5, 0), scale=0.75,
                   name='blade_tower')
    sit_on(blades, 0)
    bench = piece('buildings/furniture/metaltable01.mesh', 'ref/tex/ATLAS_interior.png', at=(dx - 2.0, 15.5, 0), scale=0.7, name='parts_bench')
    sit_on(bench, 0)
    bt = bounds(bench)[1].z
    limbs = piece('buildings/crafting/BENCH Robot Limb-pieces.mesh', 'ref/tex/BENCH Robot Limbs_DIF.png', at=(dx - 2.0, 15.5, 0), scale=0.28,
                  name='limb_pieces')
    sit_on(limbs, bt - 0.2)
    kit = piece('items/meshes/Item_Robot_Repair_Kit.mesh', ATLAS, at=(dx + 6.5, 15.0, 0), rot=(0, 0, 20)); sit_on(kit, bt)
    grinder = piece('items/meshes/Item_Tools3.mesh', ATLAS, at=(dx - 9.0, 15.8, 0), rot=(0, 0, -60)); sit_on(grinder, bt)
    wrench = piece('items/meshes/Item_Tools2.mesh', ATLAS, at=(dx - 5.5, 14.2, 0), rot=(0, 0, 10)); sit_on(wrench, bt)
    return [base, tank, pipe, blades, bench, limbs, kit, grinder, wrench]


HUM = 'E:/Claude/Kenshi/tools/clothing-test/cache/hum/'


def figure():
    bpy.ops.object.select_all(action='DESELECT')
    before = set(bpy.data.objects)
    IMP.kenshi_ogre_objects(filepath=HUM + 'human_male.mesh', import_animations=True, create_materials=True, cleanup_vertices='DEFAULT',
                            import_shapekeys=False)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    for o in new:
        if o.type == 'MESH':
            o.data.materials.clear(); m = bpy.data.materials.new('skin'); m.diffuse_color = (0.6, 0.45, 0.35, 1); o.data.materials.append(m)
            if o.parent is None: o.parent = arm; o.matrix_parent_inverse = arm.matrix_world.inverted()
    act = bpy.data.actions['sleepinbed']
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(0)
    return new, arm


def place(arm, bodies, at, surface):
    arm.rotation_euler.z = 0; bpy.context.view_layer.update()
    pel = arm.matrix_world @ arm.pose.bones['Bip01 Pelvis'].head; head = arm.matrix_world @ arm.pose.bones['Bip01 Head'].head
    d = head - pel
    arm.rotation_euler.z = math.pi - math.atan2(d.y, d.x); bpy.context.view_layer.update()
    pel = arm.matrix_world @ arm.pose.bones['Bip01 Pelvis'].head
    arm.location += Vector((at[0] - 1.5, at[1], 0)) - Vector((pel.x, pel.y, 0)); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    low = min((o.matrix_world @ v.co).z for o in bodies if o.type == 'MESH' for v in o.evaluated_get(dg).to_mesh().vertices)
    arm.location.z += surface - low; bpy.context.view_layer.update()


table, top = operating_table()
skel = skeleton_bed(55)
body, arm = figure()

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_shadows = True
sc.render.resolution_x = 1200; sc.render.resolution_y = 700
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cam.type = 'ORTHO'


def shot(tag, cx, ang, el, scale, patient=None):
    for o in body: o.hide_render = patient is None
    if patient: place(arm, body, *patient)
    cam.ortho_scale = scale
    a = math.radians(ang); e = math.radians(el); r = 200
    co.location = (cx + r * math.sin(a) * math.cos(e), -r * math.cos(a) * math.cos(e), 7 + r * math.sin(e))
    co.rotation_euler = (math.radians(90) - e, 0, a)
    cam.clip_end = 1000
    sc.render.filepath = OUT + f'{tag}.png'; bpy.ops.render.render(write_still=True)


shot('table', 2, 35, 30, 50)
shot('table_patient', 2, 35, 30, 50, ((0, 0), top - 0.3))
shot('table_low', 2, 200, 6, 50)
shot('table_back', 2, 215, 30, 50)
shot('skeleton', 57, 35, 30, 56)
shot('skeleton_patient', 57, 35, 30, 56, ((55, 0), 7.4))
shot('skeleton_back', 57, 215, 30, 56)
bpy.ops.wm.save_as_mainfile(filepath=OUT + 'tables_draft2.blend')
print('DONE')
