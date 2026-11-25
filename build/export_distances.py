"""Export one area's listings with the same distances the website shows.

    python build/export_distances.py Gachibowli

Writes exports/<Area>_listings_with_distances.csv (plain CSV that opens in Excel).
Distances use the website's own rules: the nearest place of each kind from the listing's map pin
(straight line), Infosys by straight line, and the main road by road.
"""
import csv, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
area = sys.argv[1] if len(sys.argv) > 1 else 'Gachibowli'
HQ = (17.4350636, 78.3505964)

POIS = json.load(open(os.path.join(HERE, 'places', 'pois.json'), encoding='utf-8'))
ROADS = json.load(open(os.path.join(HERE, 'roads', 'approach.json'), encoding='utf-8'))

def fast_km(a, b, c, d):                      # same formula as the website's fastKm
    x = (d - b) * math.cos((a + c) * math.pi / 360); y = c - a
    return math.sqrt(x * x + y * y) * 111.32
def haversine(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))

HOSP_NO = re.compile(r'clinic|gynecolog|dr\.? |physician|dental|skin', re.I)
PARK_NO = re.compile(r'sez|tech|it park', re.I)
KINDS = [  # (column prefix, POI category, filter, display name) - mirrors NEAREST_KINDS on the website
    ('metro', 'metro', None, None),
    ('office', 'it', lambda p: not re.match(r'infosys', p[0], re.I), None),
    ('big_company', 'it', lambda p: len(p) > 3 and p[3] != 'Infosys', lambda p: p[3]),
    ('school', 'school', None, None),
    ('hospital', 'hospital', lambda p: not HOSP_NO.search(p[0]), None),
    ('park', 'park', lambda p: p[0] != 'Neighbourhood park' and not PARK_NO.search(p[0]), None),
    ('restaurant', 'food', None, None),
    ('landmark', 'landmark', None, lambda p: f"{p[0]} ({p[3].lower()})"),
    ('orr_exit', 'orr', None, None)]

def nearest(lat, lon, cat, ok, name):
    best, bd = None, 1e9
    for p in POIS[cat]:
        if ok and not ok(p): continue
        d = fast_km(lat, lon, p[1], p[2])
        if d < bd: best, bd = p, d
    return (name(best) if name else best[0], round(bd, 2), best[1], best[2]) if best else ('', '', None, None)
def gmaps(lat, lon, plat, plon):
    # opens Google Maps driving directions between the two points: the exact Google route distance shows there
    u = f'https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={plat},{plon}&travelmode=driving'
    return f'=HYPERLINK("{u}","Google route")'

SRC = {'osm': 'OpenStreetMap', 'addr': 'building addresses', 'listing': 'listing address', 'colony': 'colony name',
       'lane': 'no official name (described)'}
src = os.path.join(ROOT, 'area_property_lists', f'{area}_Property.csv')
rows = list(csv.DictReader(open(src, encoding='utf-8-sig')))
from urllib.parse import quote_plus
NEAR_OK = {area.lower(), '', 'gachibowli', 'smondo gachibowli', 'nanakramguda', 'khajaguda', 'kokapet', 'kondapur', 'narsingi', 'financial district', 'telecom nagar', 'indira nagar', 'whitefields', 'madhapur', 'kothaguda', 'gopanpally', 'hitech city', 'hitec city'}
pin_count = {}
for r in rows:
    v = (r.get('lat-lon') or '').strip()
    if v: pin_count[v] = pin_count.get(v, 0) + 1
def pin_quality(r):
    v = (r.get('lat-lon') or '').strip(); web = (r.get('listed by website as') or '').strip()
    if not v: return 'No exact location: the website gave only the area name, so no distances'
    if web.lower() not in NEAR_OK and web.lower() != area.lower():
        return f'CHECK: map pin is in {area} but the website lists it under {web} (address: {(r.get("address") or "").strip() or "none"})'
    if pin_count[v] >= 3: return f'Project map pin (shared by {pin_count[v]} listings of this project)'
    return "Map pin from the listing website"
def link(u, label): return f'=HYPERLINK("{u}","{label}")'
extra = ['pin_quality', 'pin_on_google_maps', 'search_property_on_google', 'infosys_straight_km', 'infosys_google_route']
for pre, *_ in KINDS: extra += [f'nearest_{pre}', f'{pre}_straight_km', f'{pre}_location', f'{pre}_google_route']
extra += ['approach_road', 'main_road']

out_dir = os.path.join(ROOT, 'exports'); os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f'{area}_listings_distances.csv')
with open(out, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + extra)
    w.writeheader()
    for r in rows:
        v = (r.get('lat-lon') or '').strip(); o = {k: '' for k in extra}
        o['pin_quality'] = pin_quality(r)
        q = ', '.join(x for x in [r.get('name of the project', '').strip(), (r.get('address') or '').strip(), area, 'Hyderabad'] if x and not x.lower().startswith('unnamed'))
        o['search_property_on_google'] = link('https://www.google.com/maps/search/?api=1&query=' + quote_plus(q), 'Search name')
        if v:
            lat, lon = (float(x) for x in v.split(','))
            o['pin_on_google_maps'] = link(f'https://www.google.com/maps/search/?api=1&query={lat},{lon}', 'Pin')
            o['infosys_straight_km'] = round(haversine(lat, lon, *HQ), 2); o['infosys_google_route'] = gmaps(lat, lon, *HQ)
            for pre, cat, ok, name in KINDS:
                n, dk, plat, plon = nearest(lat, lon, cat, ok, name)
                o[f'nearest_{pre}'], o[f'{pre}_straight_km'] = n, dk
                if plat is not None: o[f'{pre}_location'] = f'{plat},{plon}'; o[f'{pre}_google_route'] = gmaps(lat, lon, plat, plon)
            x = ROADS.get(f'{lat},{lon}')
            if x:
                a = x['app']
                o['approach_road'] = a['name'] or a['kind']; o['main_road'] = x['main']['name']
        w.writerow({**r, **o})
print('wrote', out, len(rows), 'rows')
