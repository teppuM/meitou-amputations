import bpy, bmesh, addon_utils
addon_utils.enable('bl_ext.user_default.kenshi_io_tools', default_set=True)
IMP = getattr(bpy.ops, 'import')
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
IMP.kenshi_ogre_objects(filepath='E:/SteamLibrary/steamapps/common/Kenshi/data/buildings/furniture/new_furniture01/bed1.mesh', import_animations=False, create_materials=True, cleanup_vertices='DEFAULT')
o = next(x for x in bpy.data.objects if x.type == 'MESH')
bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
seen = set(); parts = []
for v in bm.verts:
    if v.index in seen: continue
    stack = [v]; comp = []
    while stack:
        x = stack.pop()
        if x.index in seen: continue
        seen.add(x.index); comp.append(x)
        for e in x.link_edges: stack.append(e.other_vert(x))
    mn = [min(c.co[i] for c in comp) for i in range(3)]; mx = [max(c.co[i] for c in comp) for i in range(3)]
    parts.append((len(comp), [round(a,1) for a in mn], [round(a,1) for a in mx]))
for p in sorted(parts, key=lambda p: (p[1][2], p[1][0])): print('PART', p)
print('UVMIN', min(l[bm.loops.layers.uv.active].uv[1] for f in bm.faces for l in f.loops), 'UVMAX', max(l[bm.loops.layers.uv.active].uv[1] for f in bm.faces for l in f.loops))
