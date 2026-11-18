import importlib.util, json, os
from PIL import Image
BS = chr(92)
spec = importlib.util.spec_from_file_location('b', 'E:/Claude/Kenshi/mod-builder/operating-tables/data/build_data_mod.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
m = b.merged('E:/SteamLibrary/steamapps/common/Kenshi/data')
W = 'E:/Claude/Kenshi/mod-builder/operating-tables/models/'
K = 'E:/SteamLibrary/steamapps/common/Kenshi/'
names = ['Item_Hacksaw', 'Item_Tools', 'Item_Tools2', 'Item_Tools3', 'Item_Medical_Supplies', 'Item_Advanced_First_Aid_Kit', 'Item_Basic_First_Aid_Kit',
         'Item_Bowl_Wood', 'Item_Bowl_Ceramic', 'Item_Robot_Repair_Kit', 'medkit', 'Item_Advanced_Splint']
c = json.load(open(W + 'ref/candidates.json'))
def clean(p): return p.replace(BS, '/').lstrip('./')
for sid, x in m.items():
    strs = {k: v for k, v in x['f'].items() if isinstance(v, str) and v}
    meshes = [clean(v) for k, v in strs.items() if v.lower().endswith('.mesh')]
    for mp in meshes:
        base = mp.split('/')[-1][:-5]
        if base in names and base not in c:
            tex = next((clean(v) for k, v in strs.items() if v.lower().endswith('.dds') and ('diffuse' in k.lower() or 'texture' in k.lower())), None)
            if not tex: continue
            png = 'ref/tex/' + os.path.basename(tex)[:-4] + '.png'
            if not os.path.exists(W + png): Image.open(K + tex).convert('RGB').save(W + png)
            c[base] = {'mesh': mp, 'tex': tex, 'png': png, 'part': x['name'], 'type': x['type']}
            print(base, x['name'], tex)
json.dump(c, open(W + 'ref/candidates.json', 'w'), indent=1)
print('missing', [n for n in names if n not in c])
