# Draft 2 of the Operating Tables models, kit-bashed from the game's own models (no new geometry except the leather straps).
# Operating Table (all on the furniture atlas, props_atlas_regular, like the Bed and the items): the Bed's frame and mattress raised to table height,
# three leather straps; at the foot a small table with a hacksaw, an angle grinder, pliers, medical supplies and a first-aid kit; a wooden bowl under
# the middle to catch blood; the standing strip light at the head as the surgery lamp; the medical crate beside the head (its own texture).
# Skeleton Operating Bed: the Skeleton Repair Bed; the boiler tank at the foot as its oil drum, joined by an exhaust pipe; the peeler blade stack at the
# side ... removed (Jame: no peeler parts); a metal table beside it with robot limb pieces, a robotics repair kit, a grinder and a wrench.
# Renders only (draft2/*.png). Run: blender -b --factory-startup -P build_tables_v2.py
import bpy, bmesh, math, os, addon_utils
from mathutils import Vector

addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
K = 'E:/SteamLibrary/steamapps/common/Kenshi/data/'
W = 'E:/Claude/Kenshi/mod-builder/operating-tables/models/'
OUT = W + 'draft2/'
os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

RAISE = 1.0          # the Bed's own height: the sleep animation lays the body at the Bed's mattress height (its use nodes stand on the floor)
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


def rest_on(o, support):
    """Lowers or lifts o until it rests on support's surface: rays cast straight down through o's footprint (a 5 x 5 grid) find the surface
    under each point, and o's lowest point goes to the highest surface found, so nothing hangs in the air or sinks through."""
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(support, dg)
    inv = support.matrix_world.inverted()
    lo, hi = bounds(o)
    best = None
    for i in range(5):
        for j in range(5):
            x = lo.x + (hi.x - lo.x) * (0.1 + 0.2 * i); y = lo.y + (hi.y - lo.y) * (0.1 + 0.2 * j)
            origin = inv @ Vector((x, y, hi.z + 50))
            d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
            hit = tree.ray_cast(origin, d)
            if hit[0] is not None:
                z = (support.matrix_world @ hit[0]).z
                best = z if best is None else max(best, z)
    if best is None: raise RuntimeError(f'{o.name}: no surface under it')
    sit_on(o, best)
    print('REST', o.name, 'on', support.name, round(best, 2))


def clear_of(objs):
    """Fails when two of objs overlap in plan (their footprints, shrunk by a small margin), so items on a table never clip into each other."""
    boxes = [(o.name, *bounds(o)) for o in objs]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (n1, a1, b1), (n2, a2, b2) = boxes[i], boxes[j]
            if a1.x + 0.1 < b2.x and a2.x + 0.1 < b1.x and a1.y + 0.1 < b2.y and a2.y + 0.1 < b1.y:
                raise RuntimeError(f'{n1} overlaps {n2}')
    print('CLEAR', [b[0] for b in boxes])


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
    # Laid out on the table's top without touching each other (checked below): the saw along the near edge, the kit and the supplies at the back, the
    # pliers between them.
    tlo, thi = bounds(tray)
    cx, cy = (tlo.x + thi.x) / 2, (tlo.y + thi.y) / 2
    print('TRAY TOP', [round(v, 1) for v in tlo], [round(v, 1) for v in thi])
    tools = [piece('items/meshes/Item_Hacksaw.mesh', ATLAS, at=(cx - 2.3, cy, 0), rot=(0, 0, 90)),
             piece('items/meshes/Item_Advanced_First_Aid_Kit.mesh', ATLAS, at=(cx + 1.7, cy - 2.6, 0), rot=(0, 0, 90)),
             piece('items/meshes/Item_Medical_Supplies.mesh', ATLAS, at=(cx + 1.7, cy + 3.4, 0), rot=(0, 0, 90))]
    for t in tools: rest_on(t, tray)
    clear_of(tools)
    bowl = piece('items/meshes/Item_Bowl_Wood.mesh', ATLAS, at=(1.5, 0, 0), scale=1.6, name='blood_bowl'); sit_on(bowl, 0)
    lamp = piece('buildings/lights/strip_light1.mesh', ATLAS, at=(-15.5, -5.5, 0), name='surgery_lamp'); sit_on(lamp, 0)
    crate = piece('buildings/furniture/medicrate.mesh', 'ref/tex/medicrate_d.png', at=(-19.5, 6.5, 0), rot=(0, 0, 90), scale=0.45, name='medical_crate')
    sit_on(crate, 0)
    return parts + [tray, bowl, lamp, crate] + tools, top


def skeleton_bed(dx):
    base = piece('buildings/furniture/new_furniture01/Robot Repair Bed.mesh', ROBO, at=(dx, 0, 0), name='skeleton_bed_base')
    tank = piece('buildings/furniture/new_furniture01/boiler_tank1.mesh', ATLAS, at=(dx + 19.5, -4.0, 0), scale=0.7, name='oil_drum'); sit_on(tank, 0)
    pipe = piece('buildings/furniture/new_furniture01/exaust_pipe1.mesh', ATLAS, at=(dx + 15.5, -4.0, 4.0), rot=(0, 90, 0), scale=0.6, name='oil_pipe')
    bench = piece('buildings/furniture/metaltable01.mesh', 'ref/tex/ATLAS_interior.png', at=(dx - 2.0, 15.5, 0), scale=0.7, name='parts_bench')
    sit_on(bench, 0)
    bt = bounds(bench)[1].z
    blo, bhi = bounds(bench)
    bx, by_ = (blo.x + bhi.x) / 2, (blo.y + bhi.y) / 2
    print('BENCH TOP', [round(v, 1) for v in blo], [round(v, 1) for v in bhi])
    kit = piece('items/meshes/Item_Robot_Repair_Kit.mesh', ATLAS, at=(bx + 7.0, by_, 0), rot=(0, 0, 0)); rest_on(kit, bench)
    grinder = piece('items/meshes/Item_Tools3.mesh', ATLAS, at=(bx - 8.5, by_, 0), rot=(0, 0, 0)); rest_on(grinder, bench)
    wrench = piece('items/meshes/Item_Tools2.mesh', ATLAS, at=(bx - 0.5, by_, 0), rot=(0, 0, 0)); rest_on(wrench, bench)
    clear_of([kit, grinder, wrench])
    return [base, tank, pipe, bench, kit, grinder, wrench]


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
RENDER = os.environ.get('RENDER', '1') == '1'
EXPORT = os.environ.get('EXPORT', '0') == '1'

if RENDER:
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

    tag = os.environ.get('TAG', '')
    shot('table' + tag, 2, 35, 30, 50)
    shot('table_patient' + tag, 2, 35, 30, 50, ((0, 0), top - 0.3))
    shot('table_low' + tag, 2, 200, 6, 50)
    shot('skeleton' + tag, 57, 35, 30, 56)
    shot('skeleton_patient' + tag, 57, 35, 30, 56, ((55, 0), 7.4))
    shot('skeleton_back' + tag, 57, 215, 30, 56)
    for o in body: bpy.data.objects.remove(o)

if EXPORT:
    import json
    EXP = getattr(bpy.ops, 'export')
    DIST = os.environ['DIST']
    os.makedirs(DIST, exist_ok=True)
    report = {}

    def flatten(objs):
        """Each object made a plain mesh in building space: modifiers applied, transforms applied, one UV layer named UVMap."""
        for o in objs:
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
            if o.modifiers: bpy.ops.object.convert(target='MESH')
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            uvs = o.data.uv_layers
            while len(uvs) > 1: uvs.remove(uvs[-1])
            if len(uvs): uvs[0].name = 'UVMap'

    def join(name, objs, shift=0.0):
        flatten(objs)
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = name
        if shift:
            o.data.transform(__import__('mathutils').Matrix.Translation((-shift, 0, 0)))
        o.data.materials.clear(); o.data.materials.append(o.data.materials.get(name) or bpy.data.materials.new(name))
        return o

    def export_mesh(o, fname):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        path = os.path.join(DIST, fname)
        r = EXP.kenshi_ogre_objects(filepath=path, export_version='V_1_10', tangent_format='TANGENT_4')
        report[fname] = (str(r), os.path.getsize(path) if os.path.exists(path) else None)

    def col_box(name, lo, hi):
        if bpy.context.scene.rigidbody_world is None: bpy.ops.rigidbody.world_add()
        bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2 for a, b in zip(lo, hi)])
        o = bpy.context.object; o.name = name; o.scale = [b - a for a, b in zip(lo, hi)]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bpy.ops.rigidbody.object_add(); o.rigid_body.type = 'PASSIVE'; o.rigid_body.collision_shape = 'BOX'
        return o

    def export_collision(objs, fname):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        path = os.path.join(DIST, fname)
        r = EXP.kenshi_physx_objects(filepath=path, objects='SELECTED', transform='SCENE')
        report[fname] = (str(r), os.path.getsize(path) if os.path.exists(path) else None)

    def box_of(objs, shift=0.0, pad=0.0):
        lo = Vector((1e9, 1e9, 1e9)); hi = -lo
        for o in objs:
            a, b = bounds(o)
            lo = Vector(map(min, lo, a)); hi = Vector(map(max, hi, b))
        lo.x -= shift; hi.x -= shift
        return [lo.x - pad, lo.y - pad, max(lo.z, 0)], [hi.x + pad, hi.y + pad, hi.z]

    by = {o.name: o for o in table}
    frame = by['table_frame']; tray = by['instrument_table']; crate = by['medical_crate']; lamp = by['surgery_lamp']
    tcol = [col_box('optab_table_COL0', *box_of([frame])), col_box('optab_table_COL1', *box_of([tray])),
            col_box('optab_table_COL2', *box_of([crate])), col_box('optab_table_COL3', *box_of([lamp], pad=0.3))]
    by2 = {o.name: o for o in skel}
    scol = [col_box('optab_skel_COL0', *box_of([by2['oil_drum']], 55)), col_box('optab_skel_COL1', *box_of([by2['parts_bench']], 55))]
    for o in tcol + scol: o.location.x += 0
    for o in scol:
        o.location.x -= 0
    export_collision(tcol, 'optab_table_COL.xml')
    export_collision(scol, 'optab_skel_COL.xml')
    for o in tcol + scol: bpy.data.objects.remove(o)

    t_crate = [crate]
    t_atlas = [o for o in table if o is not crate]
    export_mesh(join('optab_table_atlas', t_atlas), 'optab_table_atlas.mesh')
    export_mesh(join('optab_table_crate', t_crate), 'optab_table_crate.mesh')
    s_atlas = [by2[n] for n in ('oil_drum', 'oil_pipe')] + [o for o in skel if o.name.startswith('Item_')]
    export_mesh(join('optab_skel_atlas', s_atlas, 55), 'optab_skel_atlas.mesh')
    export_mesh(join('optab_skel_bench', [by2['parts_bench']], 55), 'optab_skel_bench.mesh')
    for k, v in report.items(): print('EXPORT', k, v)
    json.dump(report, open(os.path.join(DIST, 'export_report.json'), 'w'), indent=1)

print('DONE')
