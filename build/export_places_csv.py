"""Write each area's listings with the place data the website shows (key distances, and schools, hospitals,
offices and other places within 5 km) to area_property_lists/<Area>_with_places.csv.

Same rules as the listing card on the website:
  - key distances: Infosys office, metro, ORR, airport, big company; road distances (Google Maps / Mapbox) when
    collected, else the user's Google Maps values from the FMV files, else OpenStreetMap
  - places within 5 km: from the user's FMV files when the listing matches one (project or map pin within 150 m),
    else OpenStreetMap
  - road-measured hospitals, schools and parks where they were collected

    python build/export_places_csv.py      (run python build/user_places.py first if the FMV files changed)
"""
import csv, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
AREAS = ['Gachibowli', 'Kokapet', 'Kondapur', 'Narsingi']
HQ = (17.4350636, 78.3505964)
U = json.load(open(os.path.join(HERE, 'data', 'user_near.json'), encoding='utf-8'))
INFRA = json.load(open(os.path.join(HERE, 'data', 'infra.json'), encoding='utf-8'))
POIS = json.load(open(os.path.join(HERE, 'places', 'pois.json'), encoding='utf-8'))
ROAD_SRC = {'google': 'Google Maps, by road', 'mapbox': 'Mapbox, by road'}
KINDS = [('school', 'Schools & colleges'), ('hospital', 'Hospitals & clinics'), ('office', 'Offices'), ('shop', 'Shops & malls'),
         ('park', 'Parks & lakes'), ('fitness', 'Gyms & sports'), ('worship', 'Temples, mosques & churches'), ('transport', 'Metro & bus')]
OSM_KIND = {'school': 'school', 'hospital': 'hospital', 'it': 'office', 'metro': 'transport', 'park': 'park'}

def hv(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
r2 = lambda x: None if x is None else round(x, 2)
def num(v):
    try: x = float(re.sub(r'[^\d.]', '', str(v or ''))); return x if x > 0 else None
    except ValueError: return None
def nearest(lat, lon, kind, ok=lambda p: True, name=lambda p: p[0]):
    best = min(((hv(lat, lon, p[1], p[2]), p) for p in POIS[kind] if ok(p)), default=None, key=lambda x: x[0])
    return (name(best[1]), best[0]) if best else None
park_ok = lambda p: p[0] != 'Neighbourhood park' and not re.search(r'sez|tech|it park', p[0], re.I)
hosp_ok = lambda p: not re.search(r'clinic|dental|skin|physician', p[0], re.I)
lst = lambda L: '; '.join(f'{n} ({km_txt(d)})' for n, d in L)
def km_txt(d): return f'{round(d * 1000 / 10) * 10:.0f} m' if d < 1 else f'{d:.1f} km'

NEW_COLS = ['Infosys office km', 'Infosys office source', 'Metro', 'Metro km', 'Metro source', 'ORR km', 'ORR name', 'ORR source',
            'ORR estimated range (km)', 'Airport km', 'Airport source', 'Airport estimated range (km)', 'Big company', 'Big company km',
            'Big company source', 'Places source']
for _, lab in KINDS: NEW_COLS += [f'{lab}: nearest', f'{lab}: nearest km', f'{lab}: count within 5 km', f'{lab}: all within 5 km']
NEW_COLS += ['Hospitals by road', 'Schools by road', 'Parks by road', 'Road distances from']

def enrich(lat, lon, name, g_orr=None, g_air=None, near_list=None, g_metro=None, allow_est=True):
    """Place columns for one listing at (lat, lon). g_orr/g_air: the user's Google values if known.
    near_list: [(name, kind, km), ...] from the user's files, if already matched."""
    o = {}; pin = f'{lat!r},{lon!r}'; I = INFRA.get(pin); rd = ROAD_SRC.get(I['s']) if I else None
    est = None; key = pin + '|' + norm(name)
    G = U['gm'].get(key) or U['gm'].get(pin)
    if G:
        g_orr = g_orr if g_orr is not None else G[0]; g_air = g_air if g_air is not None else G[1]
        g_metro = g_metro if g_metro is not None else G[2]
    elif g_orr is None and g_air is None and allow_est:
        est = U.get('est', {}).get(pin)
    inf = (I['inf'], rd) if I and I.get('inf') is not None else (hv(lat, lon, *HQ), 'OpenStreetMap')
    o['Infosys office km'], o['Infosys office source'] = r2(inf[0]), inf[1]
    m = (I['metro'][0], I['metro'][1], rd) if I and I.get('metro') else ('', g_metro, 'your Google Maps data') if g_metro is not None else (*nearest(lat, lon, 'metro'), 'OpenStreetMap')
    o['Metro'], o['Metro km'], o['Metro source'] = m[0], r2(m[1]), m[2]
    q = ('', g_orr, 'your Google Maps data') if g_orr is not None else (I['orr'][0], I['orr'][1], rd) if I and I.get('orr') else (*nearest(lat, lon, 'orr'), 'OpenStreetMap')
    o['ORR km'], o['ORR name'], o['ORR source'] = r2(q[1]), q[0], q[2]
    o['Airport km'], o['Airport source'] = (r2(g_air), 'your Google Maps data') if g_air is not None else ('', '')
    if est: o['ORR estimated range (km)'] = f'{est[0]}–{est[1]}'; o['Airport estimated range (km)'] = f'{est[2]}–{est[3]}'
    b = (I['co'][0], I['co'][1], rd) if I and I.get('co') else (*nearest(lat, lon, 'it', lambda p: len(p) > 3 and p[3] != 'Infosys', lambda p: p[3]), 'OpenStreetMap')
    o['Big company'], o['Big company km'], o['Big company source'] = b[0], r2(b[1]), b[2]
    if near_list is None:
        L = U['near'].get(key) or U['near'].get(pin)
        near_list = [(U['places'][i][0], U['places'][i][1], d) for i, d in L] if L else None
    if near_list:
        places = list(near_list); o['Places source'] = 'your files'
    else:
        places = []
        for k, kind in OSM_KIND.items():
            for p in POIS[k]:
                if (k == 'park' and not park_ok(p)) or (k == 'hospital' and not hosp_ok(p)): continue
                d = hv(lat, lon, p[1], p[2])
                if d <= 5: places.append((p[0], kind, d))
        o['Places source'] = 'OpenStreetMap'
    places.sort(key=lambda x: x[2])
    for kind, lab in KINDS:
        P = [(n, d) for n, k, d in places if k == kind]
        o[f'{lab}: nearest'] = P[0][0] if P else ''; o[f'{lab}: nearest km'] = r2(P[0][1]) if P else ''
        o[f'{lab}: count within 5 km'] = len(P); o[f'{lab}: all within 5 km'] = lst(P)
    if I:
        o['Hospitals by road'] = lst(I.get('H', [])); o['Schools by road'] = lst(I.get('S', [])); o['Parks by road'] = lst(I.get('P', []))
        o['Road distances from'] = rd
    return o

def site_rows(area):
    """The website's listings for one area, each with its place columns."""
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', f'{area}_site.csv'), encoding='utf-8-sig')))
    out = []
    for r in rows:
        o = dict(r)
        try: lat, lon = (float(x) for x in str(r.get('lat-lon') or '').replace('"', '').split(','))
        except ValueError: out.append(o); continue
        o.update(enrich(lat, lon, r.get('name of the project'), num(r.get('orr connectivity')), num(r.get('airport distance'))))
        out.append(o)
    return list(rows[0].keys()), out

if __name__ == '__main__':
    total = 0
    for area in AREAS:
        cols, out = site_rows(area)
        dst = os.path.join(ROOT, 'area_property_lists', f'{area}_with_places.csv')
        w = csv.DictWriter(open(dst, 'w', newline='', encoding='utf-8-sig'), cols + NEW_COLS, extrasaction='ignore')
        w.writeheader(); w.writerows(out); total += len(out)
        print(area, len(out), 'rows ->', os.path.basename(dst))
    print('total', total)
