"""Data for Kokapet_Boundary_Map.html: Kokapet's official village border, the villages that touch it,
and each project in the user's checked Kokapet file, marked inside or outside the border.

    python build/kokapet_boundary_data.py
"""
import csv, json, os, re, statistics
from shapely.geometry import Polygon, Point
from shapely.ops import transform
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
V = {v['name']: v for v in json.load(open(os.path.join(HERE, 'data', 'villages_final.json'), encoding='utf-8'))}
M = lambda lat, lon: (lon * 106.2 * 1000, lat * 110.6 * 1000)          # metres, good enough at this scale
poly = lambda v: Polygon([M(a, b) for a, b in v['rings'][0]]).buffer(0)
K = poly(V['Kokapet'])
touch = sorted(n for n, v in V.items() if n != 'Kokapet' and poly(v).distance(K) < 40)
shared = {n: round(poly(V[n]).buffer(40).intersection(K.exterior).length) for n in touch}

pins = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', 'Kokapet_checked_with_places.csv'), encoding='utf-8-sig')):
    if r['Listing from'] != 'your checked file': continue
    n = re.sub(r'\s+', ' ', (r['Name of the Project'] or '').strip()); 
    try: a, b = (float(x) for x in r['Lat-Lon'].replace('"', '').split(','))
    except Exception: continue
    pins.setdefault(n.lower(), [n, []])[1].append((a, b))
projects = []
for n, L in pins.values():
    a, b = statistics.median(x[0] for x in L), statistics.median(x[1] for x in L); p = Point(M(a, b))
    inside = K.contains(p)
    vil = next((x for x, v in V.items() if x != 'Kokapet' and poly(v).contains(p)), None) if not inside else 'Kokapet'
    projects.append(dict(name=n, lat=a, lon=b, n=len(L), inside=inside, village=vil or 'not in any mapped village',
                         m=0 if inside else round(K.exterior.distance(p))))
projects.sort(key=lambda x: (not x['inside'], x['m'], x['name']))
out = dict(kokapet=V['Kokapet']['rings'], neighbours=[dict(name=n, rings=V[n]['rings'], shared_m=shared[n]) for n in touch], projects=projects,
           nearby=[dict(name=n, rings=v['rings'], m=round(poly(v).distance(K))) for n, v in V.items() if n != 'Kokapet' and n not in touch and poly(v).distance(K) < 1600])
json.dump(out, open(os.path.join(HERE, 'data', 'kokapet_boundary.json'), 'w', encoding='utf-8'), separators=(',', ':'))
print('touching:', {n: shared[n] for n in touch})
print('inside', sum(p['inside'] for p in projects), 'outside', [(p['name'], p['village'], p['m']) for p in projects if not p['inside']])

# the map page: build/kokapet_boundary_template.html with the data filled in
t = open(os.path.join(HERE, 'kokapet_boundary_template.html'), encoding='utf-8').read()
page = t.replace('__DATA__', json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
for dst in ('Kokapet_Boundary_Map.html', os.path.join('website', 'kokapet_boundary.html')):   # local copy, and the live site's copy
    open(os.path.join(ROOT, dst), 'w', encoding='utf-8').write(page); print('->', dst)
