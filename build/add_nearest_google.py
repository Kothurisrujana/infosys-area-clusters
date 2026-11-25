"""Add the 4 nearest hospitals and 4 nearest schools BY ROAD (Google Maps) to the user's Gachibowli sheet.
Existing columns are left exactly as they are; new columns go at the end.

    python build/add_nearest_google.py <input.xlsx> <nearest_plan.json> <new_google_routes.json> <output.xlsx>

nearest_plan.json: {"plan": {pin: {"Hospital": [[name, lat, lon], ...5], "School": [...]}}, "known": {"pin>lat,lon": km}}
  candidates are the 5 nearest (straight line) from the Google Maps list; "known" holds km already in the sheet.
new_google_routes.json: {"pin>lat,lon": "2.4 km" | "850 m"} read from Google Maps' first driving route.
"""
import json, re, sys
import openpyxl
from openpyxl.styles import Font

src, plan_file, res_file, dst = sys.argv[1:5]
PL = json.load(open(plan_file, encoding='utf-8')); RES = json.load(open(res_file, encoding='utf-8'))
def km_of(v):
    if isinstance(v, (int, float)): return float(v)
    m = re.match(r'([\d.,]+)\s*(km|m)\b', v or '')
    if not m: return None
    x = float(m.group(1).replace(',', '')); return round(x / 1000, 2) if m.group(2) == 'm' else x
def short(n): return n.split(' | ')[0].strip(' |')

wb = openpyxl.load_workbook(src); ws = wb.active
hdr = [c.value for c in ws[1]]; li = hdr.index('lat-lon') + 1
last = max(i for i, h in enumerate(hdr, 1) if h not in (None, ''))
cols = []
for kind in ('hospital', 'school'):
    for i in range(1, 5): cols += [f'nearest_{kind}_{i}', f'nearest_{kind}_{i}_km', f'nearest_{kind}_{i}_route']
for j, h in enumerate(cols, last + 1): ws.cell(1, j).value = h
LINK = Font(color='0563C1', underline='single')
done = missing = 0
for r in range(2, ws.max_row + 1):
    v = ws.cell(r, li).value
    if not v: continue
    a, b = (float(x) for x in str(v).replace(' ', '').split(',')); o = f'{a},{b}'
    p = PL['plan'].get(o)
    if not p: continue
    j = last + 1
    for kind in ('Hospital', 'School'):
        ranked = []
        for name, la, lo in p[kind]:
            k = f'{o}>{la},{lo}'
            d = km_of(PL['known'].get(k)) if k in PL['known'] else km_of(RES.get(k))
            if d is None: missing += 1; continue
            ranked.append((d, name, la, lo))
        ranked.sort()
        for i in range(4):
            if i < len(ranked):
                d, name, la, lo = ranked[i]
                ws.cell(r, j).value = short(name); ws.cell(r, j + 1).value = d
                c = ws.cell(r, j + 2); c.value = f'{kind.lower()}_route_googlemaps'
                c.hyperlink = f'https://www.google.com/maps/dir/?api=1&origin={o}&destination={la},{lo}&travelmode=driving'; c.font = LINK
            j += 3
    done += 1
wb.save(dst)
print('wrote', dst, '| rows filled:', done, '| candidate routes without a Google distance:', missing)
