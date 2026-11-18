"""Writes 'Operating Tables Test.mod': a test start for the Operating Tables mod. A squad of six on level open ground east of The Hub, -44260 5960, outside every town's building block (start pos forced):
Doc Steady (human, every skill 100, First Aid and Robotics included), Doc Shaky (human, First Aid and Robotics 0), patients Pell and Moss (human)
and Bolt and Rivet (skeletons). Built from the Hub Skeleton Test start's records. Run: python build_start.py <start x> <start z>."""
import importlib.util, sys
spec = importlib.util.spec_from_file_location('b', 'E:/Claude/Kenshi/mod-builder/operating-tables/data/build_data_mod.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
FILE = 'Operating Tables Test.mod'
OUT = 'E:/Claude/Kenshi/mod-builder/operating-tables/test-start/' + FILE
X, Z = int(sys.argv[1]), int(sys.argv[2])
src = {r['type']: r for r in b.read('E:/Claude/Kenshi/testmods/Hub Skeleton Test/Hub Skeleton Test.mod')}
HUMAN, SKELETON = '17-gamedata.quack', '17946-stick_people.mod'
n = iter(range(1, 100))


def rec(template, name, **fields):
    r = {k: (dict(v) if isinstance(v, dict) else v) for k, v in template.items()}
    r['refs'] = {k: list(v) for k, v in template['refs'].items()}
    r['sid'] = f'{next(n)}-{FILE}'; r['name'] = name; r['flags'] = 0
    r['f'].update(fields)
    return r


expert = rec(src[25], 'optest expert')                                   # every skill 100
novice = rec(src[25], 'optest novice', **{k: 20.0 for k in src[25]['f']})
novice['f'].update({'medic': 0.0, 'robotics': 0.0, 'strength': 40.0, 'toughness2': 20.0})


def char(name, stats, race):
    c = rec(src[1], name)
    c['refs']['stats'] = [(stats['sid'], 0, 0, 0)]
    c['refs']['race'] = [(race, 100, 0, 0)]
    return c


people = [char('Doc Steady', expert, HUMAN), char('Doc Shaky', novice, HUMAN), char('Pell', novice, HUMAN), char('Moss', novice, HUMAN),
          char('Bolt', novice, SKELETON), char('Rivet', novice, SKELETON)]
squad = rec(src[52], 'start- operating tables test')
squad['refs'] = {'leader': [(people[0]['sid'], 1, 0, 0)], 'squad': [(p['sid'], 1, 0, 0) for p in people[1:]]}
start = rec(src[64], 'Operating Tables Test', **{'force start pos': 1, 'start pos X': X, 'start pos Z': Z,
             'description': 'Test start for the Operating Tables mod: two surgeons (one expert, one novice), two human and two skeleton patients.'})
start['refs'] = {'squad': [(squad['sid'], 0, 0, 0)], 'town': src[64]['refs']['town'], 'faction relations': src[64]['refs']['faction relations']}
records = [expert, novice] + people + [squad, start]
b.write(OUT, records)
for r in records: print(r['sid'], r['type'], r['name'], {k: [t[0] for t in v] for k, v in r['refs'].items()})
