import importlib.util, json
BS = chr(92)
spec = importlib.util.spec_from_file_location('b', 'E:/Claude/Kenshi/mods/OperatingTables/data/build_data_mod.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
m = b.merged('E:/SteamLibrary/steamapps/common/Kenshi/data')
want = ['CannibalCamp Butchery Table01', 'CannibalCamp Butchery Table02', 'CannibalCamp Butchery Table03', 'CannibalCamp Butchery Table04', 'metaltable01', 'medicrate',
        'Old-World_Flouresc-Light', 'Indoor_Gas-Lamp', 'Ceiling Fan Lamp_BULB', 'Peeler-Blade stack 01', 'BENCH Robot Limb-pieces', 'BENCH Robot Limbs', 'Robotics Bench',
        'Machine Bench', 'boiler_tank1', 'prisoner_pole', 'smithy_chain', 'signboard2 tools', 'Bench tanning leather', 'cabinet1', 'strip_light1', 'Peeler Machine']
def clean(p): return p.replace(BS, '/').lstrip('./') if isinstance(p, str) else None
out = {}
for sid, x in m.items():
    mesh = x['f'].get('phs or mesh') or x['f'].get('mesh')
    if not isinstance(mesh, str) or not mesh: continue
    base = clean(mesh).split('/')[-1][:-5]
    if base in want and base not in out:
        mats = x['refs'].get('material', [])
        tex = m[mats[0][0]]['f'].get('texture map') if mats and mats[0][0] in m else None
        out[base] = {'mesh': clean(mesh), 'tex': clean(tex), 'part': x['name'], 'type': x['type']}
for k in want: print(k, out.get(k))
json.dump(out, open('E:/Claude/Kenshi/mods/OperatingTables/models/ref/candidates.json', 'w'), indent=1)
