"""Put the Google Maps route distances next to each "Google route" link in a listings workbook.

    python build/add_google_km.py <input.xlsx> <google_routes.json> <output.xlsx>

google_routes.json maps "originLat,originLon>destLat,destLon" to "<distance>|<time>|<via>" as read from
Google Maps' best (first) driving route.
"""
import json, re, sys
import openpyxl

src, res_file, dst = sys.argv[1:4]
RES = json.load(open(res_file, encoding='utf-8'))

def km_of(v):
    m = re.match(r'([\d.,]+)\s*(km|m)\b', v or '')
    if not m: return None
    x = float(m.group(1).replace(',', ''))
    return round(x / 1000, 2) if m.group(2) == 'm' else x

ws = openpyxl.load_workbook(src).active
H = [c.value for c in ws[1]]; rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
link_cols = [i for i, h in enumerate(H) if h and 'route' in str(h).lower()]
names = {i: re.sub(r'_?route.*$', '', str(H[i]), flags=re.I) + '_google_km' for i in link_cols}

out = openpyxl.Workbook(); w = out.active; w.title = ws.title
newH = []
for i, h in enumerate(H):
    newH.append(h)
    if i in link_cols: newH.append(names[i])
w.append(newH)
missing = 0
for r in rows:
    new = []
    for i, v in enumerate(r):
        new.append(v)
        if i in link_cols:
            k = None
            if v:
                m = re.search(r'origin=([^&]+)&destination=([^&]+)', str(v))
                if m: k = RES.get(f'{m.group(1)}>{m.group(2)}')
                if m and k is None: missing += 1
            new.append(km_of(k) if k else None)
    w.append(new)
out.save(dst)
print('wrote', dst, '| link columns:', [H[i] for i in link_cols], '| links without a Google distance:', missing)
