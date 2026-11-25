"""Fill empty "<place> google_km" columns in the user's workbook, keeping everything else as it is,
and turn plain "Google route" text back into working links.

    python build/fill_place_km.py <input.xlsx> <places.json> <google_routes.json> <output.xlsx>
"""
import json, re, sys
import openpyxl

src, places_file, res_file, dst = sys.argv[1:5]
PLACES = json.load(open(places_file, encoding='utf-8')); RES = json.load(open(res_file, encoding='utf-8'))

def km_of(v):
    m = re.match(r'([\d.,]+)\s*(km|m)\b', v or '')
    if not m: return None
    x = float(m.group(1).replace(',', '')); return round(x / 1000, 2) if m.group(2) == 'm' else x

wb = openpyxl.load_workbook(src); ws = wb.active
H = {str(c.value).strip(): c.column for c in ws[1] if c.value}
pin_col = H['lat-lon']
filled = missing = links = 0
for t, name, la, lo in PLACES:
    kc = H.get(f'{t}: {name} google_km'); rc = H.get(f'{t}: {name} (route)')
    if not kc: continue
    for r in range(2, ws.max_row + 1):
        pin = str(ws.cell(r, pin_col).value or '').replace(' ', '')
        if not pin: continue
        a, b = (float(x) for x in pin.split(',')); o = f'{a},{b}'; d = f'{la},{lo}'
        url = f'https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}&travelmode=driving'
        if rc:
            c = ws.cell(r, rc)
            if not c.hyperlink: c.value = 'Google route'; c.hyperlink = url; links += 1
        c = ws.cell(r, kc)
        if c.value in (None, ''):
            k = km_of(RES.get(f'{o}>{d}'))
            if k is None: missing += 1
            else: c.value = k; filled += 1
wb.save(dst)
print('wrote', dst, '| km cells filled:', filled, '| still empty:', missing, '| links restored:', links)
