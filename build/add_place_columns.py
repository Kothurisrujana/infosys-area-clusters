"""Add one "route" link column and one Google km column per chosen school / hospital.

    python build/add_place_columns.py <input.xlsx> <places.json> <google_routes.json> <output.xlsx>

places.json: [[type, column name, lat, lon], ...]
google_routes.json: {"pinLat,pinLon>placeLat,placeLon": "<distance>|<time>", ...} read from Google Maps' first driving route.
"""
import json, re, sys
import openpyxl

src, places_file, res_file, dst = sys.argv[1:5]
PLACES = json.load(open(places_file, encoding='utf-8')); RES = json.load(open(res_file, encoding='utf-8'))

def km_of(v):
    m = re.match(r'([\d.,]+)\s*(km|m)\b', v or '')
    if not m: return None
    x = float(m.group(1).replace(',', '')); return round(x / 1000, 2) if m.group(2) == 'm' else x

ws = openpyxl.load_workbook(src).active
H = [c.value for c in ws[1]]; li = H.index('lat-lon')
out = openpyxl.Workbook(); w = out.active; w.title = ws.title
extra = []
for t, name, la, lo in PLACES: extra += [f'{t}: {name} (route)', f'{t}: {name} google_km']
w.append(H + extra)
missing = 0
for r in ws.iter_rows(min_row=2, values_only=True):
    r = list(r); pin = str(r[li] or '').replace(' ', ''); add = []
    for t, name, la, lo in PLACES:
        if not pin: add += [None, None]; continue
        a, b = (float(x) for x in pin.split(','))
        o = f'{a},{b}'; d = f'{la},{lo}'
        link = f'=HYPERLINK("https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}&travelmode=driving","Google route")'
        k = km_of(RES.get(f'{o}>{d}'))
        if k is None: missing += 1
        add += [link, k]
    w.append(r + add)
out.save(dst)
print('wrote', dst, '| new columns:', len(extra), '| routes without a Google distance:', missing)
