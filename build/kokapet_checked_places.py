"""Kokapet places CSV: the listings of the user's checked file first, then the website's other Kokapet listings.

    python build/kokapet_checked_places.py "<path to Kokapet_Projects-Data(checked).xlsx>"

Writes area_property_lists/Kokapet_checked_with_places.csv. Every row gets the same place columns as the website
(build/export_places_csv.py). Rows from the checked file keep their own columns; the website's listings are mapped
onto the same column names. Website listings already in the checked file (same project, BHK, size and price) are left out.
"""
import csv, os, re, runpy, sys
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import export_places_csv as E
UP = runpy.run_path(os.path.join(HERE, 'user_places.py'))      # the FMV rows and their places (also refreshes user_near.json)
FMV, PLACES, km, norm, pin = UP['rows'], UP['places'], UP['km'], UP['norm'], UP['pin']

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'Kokapet_Projects-Data(checked).xlsx')
ws = openpyxl.load_workbook(src, read_only=True, data_only=True)['Sheet1']
it = ws.iter_rows(values_only=True)
head = [str(h).strip() if h is not None else '' for h in next(it)]
mine = [dict(zip(head, r)) for r in it if any(v not in (None, '') for v in r)]
col = lambda *names: next(h for h in head if h.lower().replace(' ', '') in [n.lower().replace(' ', '') for n in names])
C = dict(name=col('Name of the Project'), bhk=col('BHK'), sqft=col('Area_sqft'), price=col('Price_Numeric'), pin=col('Lat-Lon'),
         orr=col('ORR Connectivity'), air=col('Airport Distance'))

def fmv_near(p, name):
    """places within 5 km from the matching FMV row: same project, else a map pin within 150 m"""
    n = norm(name)
    c = [x for x in FMV if n and len(n) >= 5 and not n.startswith('unnamed') and x['proj'][:8] == n[:8]] or [x for x in FMV if km(p, x['pin']) < 0.15]
    c = [x for x in c if km(p, x['pin']) < 2]
    if not c: return None, None
    b = min(c, key=lambda x: (x['area'] != 'Kokapet', km(p, x['pin'])))
    return [(PLACES[i][0], PLACES[i][1], d) for i, d in b['near']], b['gm'][2]

ident = lambda name, bhk, sqft, price: (norm(name)[:8], str(E.num(bhk) or ''), str(E.num(sqft) or ''), str(E.num(price) or ''))
out, seen = [], set()
mine = [r for r in mine if str(r.get(C['name']) or '').strip()]   # skip stray rows with no project name
for r in mine:
    o ={'Listing from': 'your checked file', **{h: r.get(h) for h in head}}
    seen.add(ident(r[C['name']], r[C['bhk']], r[C['sqft']], r[C['price']]))
    p = pin(r.get(C['pin']))
    if p:
        near, metro = fmv_near(p, r[C['name']])
        o.update(E.enrich(p[0], p[1], r[C['name']], E.num(r.get(C['orr'])), E.num(r.get(C['air'])), near, metro, allow_est=False))
    out.append(o)
n_mine = len(out)

# the website's Kokapet listings not already in the checked file, mapped onto the checked file's column names
MAP = {'S.0': 's.0', 'Name of the Project': 'name of the project', 'Type': 'type', 'BHK': 'bhk', 'Area_sqft': 'area_sqft', 'Area Basis': 'area basis',
       'No.of Bathrooms': 'no.of bathrooms', 'Floors': 'floors', 'Floor No': 'floor no', 'Facing': 'facing', 'Furnishing Status': 'furnishing status',
       'Status': 'status', 'Asking Price': 'asking price', 'Price_Numeric': 'price_numeric', 'Price per sqft': 'price per sqft', 'Source': 'sources',
       'Link': 'source url', 'Lat-Lon': 'lat-lon', 'ORR Connectivity': 'orr connectivity', 'Airport Distance': 'airport distance',
       'Nearby Places': 'nearby places', 'Total Amenities': 'total amenities'}
_, site = E.site_rows('Kokapet')
for s in site:
    if ident(s.get('name of the project'), s.get('bhk'), s.get('area_sqft'), s.get('price_numeric')) in seen: continue
    o = {'Listing from': 'collected listings (website)'}
    for h in head: o[h] = s.get(MAP.get(h.strip(), ''), '') if MAP.get(h.strip()) else ''
    for c in E.NEW_COLS: o[c] = s.get(c, '')
    out.append(o)

dst = os.path.join(ROOT, 'area_property_lists', 'Kokapet_checked_with_places.csv')
w = csv.DictWriter(open(dst, 'w', newline='', encoding='utf-8-sig'), ['Listing from'] + head + E.NEW_COLS, extrasaction='ignore')
w.writeheader(); w.writerows(out)
print(n_mine, 'from your file +', len(out) - n_mine, 'other website listings =', len(out), '->', os.path.basename(dst))
