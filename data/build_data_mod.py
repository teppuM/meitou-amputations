"""Writes OperatingTables.mod: the Operating Table and the Skeleton Operating Bed, and the research that unlocks each.

The tables copy the game's Bed and Skeleton Repair Bed (their fields, parts, use nodes and building materials, after the base files merge), so they
look and work as those beds until their own models exist. Run: python -I build_data_mod.py <Kenshi data folder> <output .mod>.
"""
import struct
import sys

FILE = 'OperatingTables.mod'
BS = chr(92)    # the backslash of the game's file paths
BASE = ['gamedata.base', 'Newwworld.mod', 'Dialogue.mod', 'rebirth.mod']
KINDS = ['bool', 'float', 'int', 'vec3', 'vec4', 'str', 'file']


def read(path):
    """The records of a .mod/.base file (formats 16 and 17), each with its fields (and their kinds), reference lists and instances."""
    d = open(path, 'rb').read()
    p = [0]

    def i():
        v = struct.unpack_from('<i', d, p[0])[0]; p[0] += 4; return v

    def f():
        v = struct.unpack_from('<f', d, p[0])[0]; p[0] += 4; return v

    def s():
        n = i(); v = d[p[0]:p[0] + n].decode('utf-8', 'replace'); p[0] += n; return v

    def b():
        v = d[p[0]]; p[0] += 1; return v

    readers = {'bool': b, 'float': f, 'int': i, 'vec3': lambda: (f(), f(), f()), 'vec4': lambda: (f(), f(), f(), f()), 'str': s, 'file': s}
    if i() == 17:
        p[0] += 4 + struct.unpack_from('<I', d, p[0])[0]
    else:
        i(); s(); s(); s(); s()
    i()
    out = []
    for _ in range(i()):
        i()
        r = {'type': i(), 'id': i(), 'name': s(), 'sid': s(), 'flags': i(), 'f': {}, 'kinds': {}, 'refs': {}, 'inst': {}}
        for kind in KINDS:
            for _ in range(i()):
                k = s(); r['f'][k] = readers[kind](); r['kinds'][k] = kind
        for _ in range(i()):
            ln = s(); r['refs'][ln] = [(s(), i(), i(), i()) for _ in range(i())]
        for _ in range(i()):
            a = s(); target = s(); xyz = [f() for _ in range(7)]; r['inst'][a] = (target, xyz, [s() for _ in range(i())])
        out.append(r)
    return out


def merged(data):
    """The base files' records merged in load order: fields overwrite, references merge by target, instances by id."""
    m = {}
    for name in BASE:
        for r in read(data + '/' + name):
            x = m.setdefault(r['sid'], {'type': r['type'], 'name': r['name'], 'f': {}, 'kinds': {}, 'refs': {}, 'inst': {}})
            x['f'].update(r['f']); x['kinds'].update(r['kinds']); x['inst'].update(r['inst'])
            for ln, v in r['refs'].items():
                lst = x['refs'].setdefault(ln, [])
                for t in v:
                    lst[:] = [y for y in lst if y[0] != t[0]] + [t]
    return m


def by_name(m, type_, name):
    hits = [sid for sid, x in m.items() if x['type'] == type_ and x['name'] == name]
    assert len(hits) == 1, (name, hits)
    return hits[0]


def copy(m, sid, new_sid, name, **fields):
    x = m[sid]
    r = {'type': x['type'], 'name': name, 'sid': new_sid, 'flags': 0, 'f': dict(x['f']), 'kinds': dict(x['kinds']),
         'refs': {k: list(v) for k, v in x['refs'].items()}, 'inst': dict(x['inst'])}
    r['f'].update(fields)
    return r


def write(path, records):
    def w_s(o, v):
        b = v.encode('utf-8'); o += struct.pack('<i', len(b)) + b

    o = bytearray(struct.pack('<ii', 16, 1))
    for v in ['thenamejame', 'Operating tables for limb amputations (MeitouClient code mod).', 'gamedata.base,rebirth.mod', '']:
        w_s(o, v)
    o += struct.pack('<ii', len(records) + 1, len(records))
    for r in records:
        body = bytearray(struct.pack('<ii', r['type'], 0))
        w_s(body, r['name']); w_s(body, r['sid']); body += struct.pack('<I', r['flags'])
        for kind in KINDS:
            keys = [k for k in r['f'] if r['kinds'].get(k) == kind]
            body += struct.pack('<i', len(keys))
            for k in keys:
                w_s(body, k); v = r['f'][k]
                if kind == 'bool': body += struct.pack('<B', v)
                elif kind == 'float': body += struct.pack('<f', v)
                elif kind == 'int': body += struct.pack('<i', v)
                elif kind in ('vec3', 'vec4'): body += struct.pack('<%df' % len(v), *v)
                else: w_s(body, v)
        body += struct.pack('<i', len(r['refs']))
        for ln, v in r['refs'].items():
            w_s(body, ln); body += struct.pack('<i', len(v))
            for t in v:
                w_s(body, t[0]); body += struct.pack('<iii', *t[1:])
        body += struct.pack('<i', len(r['inst']))
        for a, (target, xyz, states) in r['inst'].items():
            w_s(body, a); w_s(body, target); body += struct.pack('<7f', *xyz) + struct.pack('<i', len(states))
            for st in states:
                w_s(body, st)
        o += struct.pack('<I', len(body) + 4) + body
    open(path, 'wb').write(o)


def main(data, out):
    m = merged(data)
    table_sid, bed_sid, surgery_sid, robots_sid = (f'{n}-{FILE}' for n in range(1, 5))

    table = copy(m, by_name(m, 0, 'Bed'), table_sid, 'Operating Table', Description=(
        'A table for surgery. Lie a patient on it, then right-click them with your surgeon selected and choose Amputate... to remove limbs. '
        "The surgeon's First Aid decides how much blood the patient loses and how often it goes wrong. Also heals like a bed."))
    bed = copy(m, by_name(m, 0, 'Skeleton Repair Bed'), bed_sid, 'Skeleton Operating Bed', Description=(
        'A repair bed for skeleton surgery. Lie a skeleton on it, then right-click them with your surgeon selected and choose Amputate... to remove '
        "limbs. The surgeon's Robotics decides how much oil the skeleton loses and how often it goes wrong. Repairs faster than a Skeleton Repair Bed."))
    bed['f']['output rate'] = 10.0    # it draws the Skeleton Repair Bed's own power, so it needs a generator as that bed does

    surgery = copy(m, by_name(m, 21, 'Advanced Medicine'), surgery_sid, 'Surgery')
    surgery['refs'] = {'requirements': [(by_name(m, 21, 'Medicine'), 0, 0, 0)], 'cost': m[by_name(m, 21, 'Advanced Medicine')]['refs']['cost'],
                       'enable buildings': [(table_sid, 0, 0, 0)]}
    robots = copy(m, by_name(m, 21, 'Skeleton Repair Beds'), robots_sid, 'Skeleton Operating Beds')
    robots['f']['level'] = 4
    robots['refs'] = {'requirements': [(by_name(m, 21, 'Skeleton Repair Beds'), 0, 0, 0)],
                      'cost': m[by_name(m, 21, 'Skeleton Repair Beds')]['refs']['cost'], 'enable buildings': [(bed_sid, 0, 0, 0)]}
    surgery['f']['description'] = 'Unlocks the Operating Table, where a surgeon can remove a patient\'s limbs.'
    robots['f']['description'] = 'Unlocks the Skeleton Operating Bed, where a surgeon can remove a skeleton\'s limbs. It also repairs faster.'

    # The models (models/build_tables_v2.py, exported to the mod folder): one part per texture, each using the game's own material record for that
    # texture; the Skeleton Operating Bed keeps the Skeleton Repair Bed's own part as its base.
    bed_part = by_name(m, 29, 'bed1_part')
    folder = '.' + BS + 'mods' + BS + 'OperatingTables' + BS
    sid = iter(range(5, 100))

    def part(name, mesh, material, collision=''):
        p = copy(m, bed_part, f'{next(sid)}-{FILE}', name)
        p['f']['phs or mesh'] = folder + mesh
        p['f']['xml collision'] = folder + collision if collision else ''
        p['refs'] = {'material': [material]}    # the source part's own reference, values included
        return p

    atlas = m[bed_part]['refs']['material'][0]
    table_parts = [part('optab table atlas', 'optab_table_atlas.mesh', atlas, 'optab_table_COL.xml'),
                   part('optab table crate', 'optab_table_crate.mesh', m[by_name(m, 29, 'medicrate')]['refs']['material'][0])]
    bed_parts = [part('optab skeleton atlas', 'optab_skel_atlas.mesh', atlas, 'optab_skel_COL.xml'),
                 part('optab skeleton bench', 'optab_skel_bench.mesh', m[by_name(m, 29, 'metal table01')]['refs']['material'][0])]
    table['refs']['parts'] = [(p['sid'], 0, 100, 0) for p in table_parts]
    bed['refs']['parts'] = list(m[by_name(m, 0, 'Skeleton Repair Bed')]['refs']['parts']) + [(p['sid'], 0, 100, 0) for p in bed_parts]

    records = [table, bed, surgery, robots] + table_parts + bed_parts
    write(out, records)
    for p in table_parts + bed_parts:
        print(p['sid'], p['name'], p['f']['phs or mesh'], p['f']['xml collision'], p['refs']['material'])
    for r in records:
        print(r['sid'], r['name'], {k: [m.get(t[0], {}).get('name', t[0]) for t in v] for k, v in r['refs'].items() if r['type'] == 21},
              {k: r['f'][k] for k in ('level', 'time', 'output rate', 'power output') if k in r['f']})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
