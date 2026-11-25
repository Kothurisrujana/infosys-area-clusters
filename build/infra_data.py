"""Road distances for the website, one record per map pin.

  Gachibowli          -> Google Maps best-route km, from the user's sheet (build/data/Gachibowli_google_distances.xlsx)
  Kokapet, Narsingi   -> Mapbox driving km, from build/mapbox/mapbox_distances.json

    python build/infra_data.py      (then python build/inject.py)

Writes build/data/infra.json: {"lat,lon": {"s": "google"|"mapbox", "inf": km, "metro": [name, km], "co": [name, km],
                               "orr": [name, km], "H": [[name, km], ...], "S": [...], "P": [...]}}  (lists sorted, nearest first)
"""
import json, os
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data', 'infra.json')
MAPBOX_AREAS = {'Kokapet', 'Narsingi', 'Kondapur'}
key = lambda la, lo: f'{float(la)},{float(lo)}'
num = lambda v: round(float(v), 2) if v not in (None, '') else None
infra = {}

# ---------- Gachibowli: Google Maps (user's sheet) ----------
ws = openpyxl.load_workbook(os.path.join(HERE, 'data', 'Gachibowli_google_distances.xlsx')).active
H = [str(c.value).strip() if c.value else '' for c in ws[1]]
col = H.index
h0, s0 = col('AIG Hospitals'), col('Delhi Public School')
# parks start at the first park / garden column after the schools (the user may add or drop columns)
p0 = next(i for i in range(s0, len(H)) if any(w in H[i].lower() for w in ('park', 'garden')))
end = max(i for i, h in enumerate(H) if h) + 1
for r in ws.iter_rows(min_row=2, values_only=True):
    ll = r[col('lat-lon')]
    if not ll: continue
    la, lo = str(ll).replace(' ', '').split(',')
    pick = lambda a, b: sorted([[H[i], num(r[i])] for i in range(a, b) if num(r[i]) is not None], key=lambda x: x[1])
    infra[key(la, lo)] = {
        's': 'google', 'inf': num(r[col('infosys distance_km')]),
        'metro': [r[col('nearest_metro')], num(r[col('metro distance_km')])],
        'co': [r[col('nearest_large_company')], num(r[col('large_company_km')])],
        'orr': [r[col('ORR_near')], num(r[col('ORR_distance_km')])],
        'H': pick(h0, s0), 'S': pick(s0, p0), 'P': pick(p0, end)}
g = len(infra)

# ---------- Kokapet and Narsingi: Mapbox ----------
M = json.load(open(os.path.join(HERE, 'mapbox', 'mapbox_distances.json'), encoding='utf-8'))
FIXED_KIND = {}
for k, nm, *_ in [('Hospital', 'AIG Hospitals'), ('Hospital', 'CARE Hospitals Hitec City'), ('Hospital', 'Himagiri Hospitals'), ('Hospital', 'KIMS Arete Hospital'),
                  ('Hospital', 'Medicover Hospitals Hitech City'), ('Hospital', 'Omega Hospital Gachibowli'), ('Hospital', 'Apollo Spectra Kondapur'),
                  ('Hospital', 'Gaman Hospitals'), ('School', 'Delhi Public School Sr Sec Campus'), ('School', 'Kendriya Vidyalaya Gachibowli'),
                  ('School', 'EuroSchool (CBSE)'), ('School', 'Nasr School (ICSE)'), ('School', 'Oakridge International Gachibowli'),
                  ('School', 'CHIREC International Kondapur'), ('School', 'Meridian School'), ('School', 'Resonance School Gachibowli')]:
    FIXED_KIND[nm] = k
short = lambda n: n.split(' | ')[0].strip()
# the same filters the Mapbox script now uses: keep real schools and hospitals only
_src = open(os.path.join(HERE, 'mapbox', 'mapbox_distances.py'), encoding='utf-8').read()
_ns = {}; exec(_src[_src.index('import re\n# Mapbox'):_src.index("NEAR = {'School': {}, 'Hospital': {}}")], _ns)
real_place = _ns['real_place']
first = lambda lst: [short(lst[0][0][1]), round(lst[0][1][0], 2)] if lst else None
for k, v in M.items():
    if not MAPBOX_AREAS & set(v['areas']) or k in infra: continue
    def merged(kind, near):
        d = {}
        for nm, val in v['fixed'].items():
            if FIXED_KIND.get(nm) == kind and val: d[nm] = round(val[0], 2)
        for (q, val) in v[near]:
            n = short(q[1])
            if not real_place(kind, q[1]): continue
            if val and (n not in d or val[0] < d[n]): d[n] = round(val[0], 2)
        return sorted([[n, km] for n, km in d.items()], key=lambda x: x[1])
    infra[k] = {'s': 'mapbox', 'inf': round(v['infosys'][0], 2) if v['infosys'] else None,
                'metro': first(v['metro']), 'co': first(v['big_company']), 'orr': first(v['orr_exit']),
                'H': merged('Hospital', 'nearest_hospitals'), 'S': merged('School', 'nearest_schools'), 'P': []}
# A dedicated Mapbox run for the Kokapet construction file (cleaned school/hospital list) wins when present.
KJ = os.path.join(HERE, 'mapbox', 'mapbox_distances_Kokapet.json')
if os.path.exists(KJ):
    for k, v in json.load(open(KJ, encoding='utf-8')).items():
        def merged2(kind, near):
            d = {}
            for nm, val in v['fixed'].items():
                if FIXED_KIND.get(nm) == kind and val: d[nm] = round(val[0], 2)
            for (q, val) in v[near]:
                n = short(q[1])
                if real_place(kind, q[1]) and val and (n not in d or val[0] < d[n]): d[n] = round(val[0], 2)
            return sorted([[n, km] for n, km in d.items()], key=lambda x: x[1])
        infra[k] = {'s': 'mapbox', 'inf': round(v['infosys'][0], 2) if v['infosys'] else None, 'metro': first(v['metro']),
                    'co': first(v['big_company']), 'orr': first(v['orr_exit']), 'H': merged2('Hospital', 'nearest_hospitals'),
                    'S': merged2('School', 'nearest_schools'), 'P': []}
    print('Kokapet construction pins from the dedicated Mapbox run:', len(json.load(open(KJ, encoding='utf-8'))))
# Kokapet construction file: its pins differ by a few metres from the pins Mapbox measured; reuse the record of the
# same building when the two pins are within 60 m, otherwise leave the pin without road distances.
import math
kmf = lambda a, b: math.hypot((b[1] - a[1]) * math.cos(a[0] * math.pi / 180), b[0] - a[0]) * 111.32
MB = [(tuple(map(float, k.split(','))), v) for k, v in infra.items() if v['s'] == 'mapbox']
import csv as _csv
_rows = [r for f in ('Kokapet_merged.csv', 'Kokapet_site.csv', 'Narsingi_site.csv', 'Kondapur_site.csv')
         for r in _csv.DictReader(open(os.path.join(os.path.dirname(HERE), 'area_property_lists', f), encoding='utf-8-sig'))]
matched = unmatched = 0
for r in _rows:
    ll = r.get('lat-lon')
    if not ll: continue
    q = tuple(float(x) for x in str(ll).replace(' ', '').split(','))
    k = key(*q)
    if k in infra: continue
    best = min(MB, key=lambda m: kmf(q, m[0]))
    if kmf(q, best[0]) <= 0.06: infra[k] = dict(best[1]); matched += 1
    else: unmatched += 1
print('Listings matched to a Mapbox pin of the same building:', matched, '| without road data:', unmatched)
json.dump(infra, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wrote', OUT, '| Google pins:', g, '| Mapbox pins:', len(infra) - g, '| size', os.path.getsize(OUT))
