"""Build website/index.html from build/site_template.html and the data files next to it.

Run from anywhere:  python build/inject.py
"""
import re, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
def here(*p): return os.path.join(HERE, *p)

# Built-in area files: add a new area here (name -> CSV in area_property_lists) and rebuild.
PRELOAD_FILES = {'Gachibowli': 'Gachibowli_site.csv', 'Kokapet': 'Kokapet_site.csv', 'Kondapur': 'Kondapur_site.csv', 'Narsingi': 'Narsingi_site.csv'}

m = open(os.path.join(ROOT, 'Infosys_9km_Area_Map.html'), encoding='utf-8').read()
data = re.search(r'AREAS=(\[.*?\]);', m, re.S).group(1)
pre = {n: {'file': f, 'csv': open(os.path.join(ROOT, 'area_property_lists', f), encoding='utf-8-sig').read()} for n, f in PRELOAD_FILES.items()}

# Official revenue-village borders replace the estimated ones wherever the area is a village.
V = json.load(open(here('data', 'villages_final.json'), encoding='utf-8'))
B = json.load(open(here('data', 'borders_final.json'), encoding='utf-8'))
for v in V:
    if v['name'] in B: B[v['name']] = {'kind': 'village', 'label': v['name'] + ' revenue village', 'rings': v['rings']}

# Nearby places (OpenStreetMap), made by places/build_pois.py
pois = open(here('places', 'pois.json'), encoding='utf-8').read()

# Approach roads per map pin, made by roads/roads.py. The site does not show traffic, so those fields are left out.
roads = json.load(open(here('roads', 'approach.json'), encoding='utf-8'))
for v in roads.values(): v.pop('traffic', None)
roads = json.dumps(roads, ensure_ascii=False, separators=(',', ':'))

j = lambda o, **k: json.dumps(o, separators=(',', ':'), **k)
t = (open(here('site_template.html'), encoding='utf-8').read()
     .replace('__DATA__', data)
     .replace('__BORDERS__', j(B, ensure_ascii=False))
     .replace('__VILLAGES__', j(V))
     .replace('__POIS__', pois)
     .replace('__ROADS__', roads.replace('</', '<\\/'))
     .replace('__HOT__', '[]')
     .replace('__UNEAR__', open(here('data', 'user_near.json'), encoding='utf-8').read().replace('</', '<\\/'))
     .replace('__INFRA__', open(here('data', 'infra.json'), encoding='utf-8').read().replace('</', '<\\/'))
     .replace('__PRELOAD__', json.dumps(pre, ensure_ascii=False).replace('</', '<\\/')))
os.makedirs(os.path.join(ROOT, 'website'), exist_ok=True)
open(os.path.join(ROOT, 'website', 'index.html'), 'w', encoding='utf-8').write(t)
print('ok', len(t), {n: v['csv'].count('\n') for n, v in pre.items()})
