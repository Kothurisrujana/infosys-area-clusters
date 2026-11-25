"""Driving distances from every property map pin to the places buyers care about, using Mapbox.

What it measures, for every map pin in the six built-in areas:
  * Infosys (Gachibowli campus)
  * the 8 hospitals and 8 schools chosen for Gachibowli (fixed list, same for every area)
  * the 4 nearest hospitals and 4 nearest schools BY ROAD (found with Mapbox category search around each area)
  * the nearest metro station, big company office and ORR exit BY ROAD (from the OpenStreetMap lists the website uses)

How to run (PowerShell):
    $env:MAPBOX_TOKEN = "pk.your-token-here"        # your own token; never put it in the website files
    python build/mapbox/mapbox_distances.py --dry-run  # shows the plan and how many requests it will make (no token needed)
    python build/mapbox/mapbox_distances.py            # runs it; safe to stop and start again (answers are cached)

Output: build/mapbox/mapbox_distances.json and exports/<Area>_mapbox_distances.csv
Mapbox APIs used: Search Box API (category search) and Matrix API (driving profile, up to 25 points per request,
60 requests a minute). Billing is per element (one property-to-place pair).
"""
import csv, hashlib, json, math, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); BUILD = os.path.dirname(HERE); ROOT = os.path.dirname(BUILD)
CACHE = os.path.join(HERE, 'cache'); os.makedirs(CACHE, exist_ok=True)
DRY = '--dry-run' in sys.argv
TOKEN = os.environ.get('MAPBOX_TOKEN', '')
if not DRY and not TOKEN: sys.exit('Set MAPBOX_TOKEN first (see the top of this file), or run with --dry-run.')

AREAS = ['Gachibowli', 'Nanakramguda', 'Khajaguda', 'Kokapet', 'Kondapur', 'Narsingi']
HQ = (17.4350636, 78.3505964)
FIXED = [  # (kind, name, lat, lon): Google Maps positions of the places chosen for Gachibowli
    ('Hospital', 'AIG Hospitals', 17.443272, 78.366276), ('Hospital', 'CARE Hospitals Hitec City', 17.430537, 78.372244),
    ('Hospital', 'Himagiri Hospitals', 17.442311, 78.358711), ('Hospital', 'KIMS Arete Hospital', 17.427863, 78.375024),
    ('Hospital', 'Medicover Hospitals Hitech City', 17.446669, 78.380126), ('Hospital', 'Omega Hospital Gachibowli', 17.436443, 78.367457),
    ('Hospital', 'Apollo Spectra Kondapur', 17.459689, 78.366037), ('Hospital', 'Gaman Hospitals', 17.436943, 78.356673),
    ('School', 'Delhi Public School Sr Sec Campus', 17.435981, 78.364384), ('School', 'Kendriya Vidyalaya Gachibowli', 17.439305, 78.355025),
    ('School', 'EuroSchool (CBSE)', 17.433263, 78.373661), ('School', 'Nasr School (ICSE)', 17.444518, 78.362673),
    ('School', 'Oakridge International Gachibowli', 17.419876, 78.364388), ('School', 'CHIREC International Kondapur', 17.462607, 78.35144),
    ('School', 'Meridian School', 17.453441, 78.383856), ('School', 'Resonance School Gachibowli', 17.43933, 78.360334)]
N_NEAR_CAND = 5      # candidates per kind sent to Mapbox (closest in a straight line); the 4 shortest drives are kept
N_KEEP = 4

def km(a, b, c, d):
    x = (d - b) * math.cos((a + c) * math.pi / 360); y = c - a; return math.sqrt(x * x + y * y) * 111.32

def get(url, what):
    """GET with a disk cache, so a stopped run can resume without paying twice."""
    key = hashlib.sha1(url.encode()).hexdigest(); f = os.path.join(CACHE, key + '.json')
    if os.path.exists(f): return json.load(open(f, encoding='utf-8'))
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url + ('&' if '?' in url else '?') + 'access_token=' + TOKEN, timeout=30) as r:
                data = json.load(r)
            json.dump(data, open(f, 'w', encoding='utf-8')); time.sleep(1.05)   # stay under 60 requests a minute
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(20); continue                          # rate limited: wait and retry
            if e.code in (401, 403): sys.exit(f'Mapbox refused the token ({e.code}). Check MAPBOX_TOKEN.')
            print(f'  {what}: HTTP {e.code}, retrying'); time.sleep(5)
        except Exception as e:
            print(f'  {what}: {e}, retrying'); time.sleep(5)
    raise SystemExit(f'Gave up on {what}')

# ---------- property pins ----------
PINS = {}   # (lat, lon) -> {'areas': set, 'exact': bool}
# --file <csv in area_property_lists> --area <name>: measure only that file's pins (writes mapbox_distances_<area>.json)
ONLY = sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else None
ONLY_AREA = sys.argv[sys.argv.index('--area') + 1] if '--area' in sys.argv else None
SOURCES = [(ONLY_AREA, ONLY)] if ONLY else [(a, f'{a}_Property.csv') for a in AREAS]
for a, fname in SOURCES:
    for r in csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', fname), encoding='utf-8-sig')):
        r = {k.strip().lower(): v for k, v in r.items() if k}
        v = (r.get('lat-lon') or '').strip()
        if not v: continue
        p = tuple(float(x) for x in v.split(','))
        e = PINS.setdefault(p, {'areas': set(), 'exact': True}); e['areas'].add(a)
        if 'label only' in (r.get('location basis') or ''): e['exact'] = False

# ---------- places from the website's lists (OpenStreetMap) ----------
POIS = json.load(open(os.path.join(BUILD, 'places', 'pois.json'), encoding='utf-8'))
METRO = [('Metro', p[0], p[1], p[2]) for p in POIS['metro']]
BIG = [('Big company', f"{p[3]} ({p[0]})" if p[3].lower() not in p[0].lower() else p[0], p[1], p[2]) for p in POIS['it'] if len(p) > 3 and p[3] != 'Infosys']
ORR = [('ORR exit', p[0], p[1], p[2]) for p in POIS['orr']]

# ---------- schools and hospitals near each area (Mapbox category search) ----------
def area_centres():
    """about 1 km groups of pins: search around each so no corner of an area is missed"""
    g = {}
    for (la, lo) in PINS: g.setdefault((round(la / 0.009), round(lo / 0.0094)), []).append((la, lo))
    return [(sum(x[0] for x in v) / len(v), sum(x[1] for x in v) / len(v)) for v in g.values()]
CENTRES = area_centres()

def category_ids():
    if DRY: return {'School': 'school', 'Hospital': 'hospital'}
    L = get('https://api.mapbox.com/search/searchbox/v1/list/category?language=en', 'category list')
    ids = [c['canonical_id'] for c in L.get('listItems', [])]
    pick = lambda want: next((i for i in ids if i == want), next((i for i in ids if want in i), want))
    return {'School': pick('school'), 'Hospital': pick('hospital')}

import re
# Mapbox's categories are loose ("school" includes driving and music classes, "hospital" includes doctors and first aid),
# so keep only real schools and hospitals by name.
SCHOOL_YES = re.compile(r"school|vidyala|vidyalay|vidya niketan|vidyaniketan|gurukul|academy|high school|public school", re.I)
SCHOOL_NO = re.compile(r"pre[-\s]*school|play ?school|anganwadi|\bart\b|football|cricket|basketball|badminton|tennis|sports|\bgate\b|parking|\broad$|"
                       r"kids|kidz|daycare|day care|creche|nursery|montessori|driving|motor|music|guitar|violin|"
                       r"piano|dance|martial|kickbox|taekwondo|karate|yoga|swim|chess|coaching|tuition|hostel|collage|"
                       r"abacus|beauty|aviation|language|spoken english|computer", re.I)
HOSP_YES = re.compile(r"hospital|hospitals|medical college|nursing home|medicover|kims|aig|apollo|care hospitals|continental|rainbow|cloudnine", re.I)
HOSP_NO = re.compile(r"clinic|dr\.?\s|^dr\b|doctor|first aid|eye|vision|dental|homeo|herbal|ayur|auervedic|ivf|fertility|pharmacy|medical (and|&)? ?general|"
                     r"store|diagnostic|department|health cent|\bphc\b|primary health|vaccine|physio|skin|hair|veterinary|\bpet\b|"
                     r"pan mahal|cleaning|pest|office|^hospital$|^clinic$|upcoming|taxi|pick ?up|drop ?off|\bopd\b|outpatient|out-patient|"
                     r"parking|entrance|\bgate\b|emergency helpline|lounge", re.I)
def real_place(kind, name):
    if kind == 'School': return bool(SCHOOL_YES.search(name)) and not SCHOOL_NO.search(name)
    return bool(HOSP_YES.search(name)) and not HOSP_NO.search(name)

NEAR = {'School': {}, 'Hospital': {}}
if not DRY:
    CAT = category_ids()
    for kind, cid in CAT.items():
        for la, lo in CENTRES:
            d = get(f'https://api.mapbox.com/search/searchbox/v1/category/{urllib.parse.quote(cid)}?language=en&limit=25'
                    f'&proximity={lo:.5f},{la:.5f}&radius=0.03', f'{kind} search')
            for f in d.get('features', []):
                pr = f.get('properties', {}); name = (pr.get('name') or '').strip(); c = f['geometry']['coordinates']
                if name and real_place(kind, name): NEAR[kind][(name.lower(), round(c[1], 4), round(c[0], 4))] = (kind, name, c[1], c[0])
def dedupe(lst):
    keep = []
    for q in sorted(lst, key=lambda q: len(q[1])):
        key = ' '.join(re.sub(r'[^a-z0-9 ]', ' ', q[1].lower()).split()[:2])
        if any(' '.join(re.sub(r'[^a-z0-9 ]', ' ', k[1].lower()).split()[:2]) == key and km(q[2], q[3], k[2], k[3]) < 0.3 for k in keep): continue
        keep.append(q)
    return keep
NEAR = {k: dedupe(list(v.values())) for k, v in NEAR.items()}

def closest(lst, p, n):
    return sorted(lst, key=lambda q: km(p[0], p[1], q[2], q[3]))[:n]

# ---------- one Matrix call per 24 places ----------
def drive(p, dests):
    out = []
    for i in range(0, len(dests), 24):
        chunk = dests[i:i + 24]
        coords = ';'.join([f'{p[1]:.6f},{p[0]:.6f}'] + [f'{q[3]:.6f},{q[2]:.6f}' for q in chunk])
        if DRY: out += [None] * len(chunk); continue
        d = get(f'https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coords}?sources=0&annotations=distance,duration', 'matrix')
        dist = d['distances'][0][1:]; dur = d['durations'][0][1:]
        out += [(round(x / 1000, 2), round(t / 60)) if x is not None else None for x, t in zip(dist, dur)]
    return out

requests = elements = 0; result = {}
for n, (p, info) in enumerate(sorted(PINS.items()), 1):
    plan = [('Infosys', 'Infosys (Gachibowli campus)', HQ[0], HQ[1])] + FIXED
    plan += closest(METRO, p, 2) + closest(BIG, p, 2) + closest(ORR, p, 1)
    plan += closest(NEAR['Hospital'], p, N_NEAR_CAND) + closest(NEAR['School'], p, N_NEAR_CAND)
    requests += math.ceil(len(plan) / 24) if not DRY else math.ceil((len(plan) + 2 * N_NEAR_CAND) / 24)
    elements += len(plan) if not DRY else len(plan) + 2 * N_NEAR_CAND
    res = drive(p, plan)
    if DRY: continue
    rows = [(q, r) for q, r in zip(plan, res)]
    best = lambda kind: sorted([(q, r) for q, r in rows if q[0] == kind and r], key=lambda z: z[1][0])
    o = {'areas': sorted(info['areas']), 'exact_pin': info['exact'],
         'infosys': rows[0][1], 'fixed': {q[1]: r for q, r in rows[1:1 + len(FIXED)]},
         'metro': best('Metro')[:1], 'big_company': best('Big company')[:1], 'orr_exit': best('ORR exit')[:1],
         # the 4 shortest drives among nearby schools / hospitals (a fixed-list place appears here too if it is one of the nearest)
         'nearest_hospitals': best('Hospital')[:N_KEEP], 'nearest_schools': best('School')[:N_KEEP]}
    result[f'{p[0]},{p[1]}'] = o
    if n % 25 == 0: print(f'{n}/{len(PINS)} pins done')

print(f'pins: {len(PINS)} | search areas: {len(CENTRES)} | matrix requests: {requests} (+{2 * len(CENTRES) + 1} searches) | '
      f'elements: {elements} | about {round((requests + 2 * len(CENTRES)) / 55)} minutes at 60 requests a minute')
if DRY: sys.exit(0)
json.dump(result, open(os.path.join(HERE, f'mapbox_distances_{ONLY_AREA}.json' if ONLY else 'mapbox_distances.json'), 'w', encoding='utf-8'), ensure_ascii=False)
if ONLY: sys.exit(print('wrote', f'mapbox_distances_{ONLY_AREA}.json'))

# ---------- one plain CSV per area ----------
fmt = lambda z: (z[0][1], z[1][0]) if z else ('', '')
for a in AREAS:
    out = os.path.join(ROOT, 'exports', f'{a}_mapbox_distances.csv')
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', f'{a}_Property.csv'), encoding='utf-8-sig')))
    cols = ['infosys_road_km', 'infosys_drive_min', 'nearest_metro', 'metro_road_km', 'nearest_big_company', 'big_company_road_km',
            'nearest_orr_exit', 'orr_exit_road_km']
    cols += [f'{k}: {nm} road_km' for k, nm, _, _ in FIXED]
    for i in range(1, N_KEEP + 1): cols += [f'nearest_hospital_{i}', f'nearest_hospital_{i}_road_km']
    for i in range(1, N_KEEP + 1): cols += [f'nearest_school_{i}', f'nearest_school_{i}_road_km']
    cols += ['pin_is_exact']
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + cols); w.writeheader()
        for r in rows:
            o = {c: '' for c in cols}; v = (r.get('lat-lon') or '').strip()
            x = result.get(','.join(str(float(t)) for t in v.split(','))) if v else None
            if x:
                if x['infosys']: o['infosys_road_km'], o['infosys_drive_min'] = x['infosys']
                for key, col in [('metro', 'metro'), ('big_company', 'big_company'), ('orr_exit', 'orr_exit')]:
                    if x[key]: o[f'nearest_{col}'], o[f'{col}_road_km'] = fmt(x[key][0])
                for k, nm, _, _ in FIXED:
                    rr = x['fixed'].get(nm); o[f'{k}: {nm} road_km'] = rr[0] if rr else ''
                for kind, key in [('hospital', 'nearest_hospitals'), ('school', 'nearest_schools')]:
                    for i, z in enumerate(x[key], 1): o[f'nearest_{kind}_{i}'], o[f'nearest_{kind}_{i}_road_km'] = fmt(z)
                o['pin_is_exact'] = 'yes' if x['exact_pin'] else 'no (placed from the area name)'
            w.writerow({**r, **o})
    print('wrote', out)
