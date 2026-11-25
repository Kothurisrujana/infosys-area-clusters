"""Add the user's newer listing files to the website's area files, keeping one row per real listing.

    python build/merge_listings.py

Kokapet    = area_property_lists/Kokapet_Property.csv   + build/data/Kokapet_checked.xlsx (Sheet1; Sheet2 'Unavailable' is skipped)
Gachibowli = area_property_lists/Gachibowli_Property.csv + build/data/Gachibowli_google_distances.xlsx
Writes area_property_lists/<Area>_merged.csv and prints what was added and what was dropped as a duplicate.

A row is a duplicate when it has the same listing link, or the same project and BHK with size and price
within 2% of each other (and the same floor when both rows give one): the same flat listed on two websites.
"""
import csv, os, re
from difflib import SequenceMatcher   # same project even with small spelling differences (Wesstbrook / Westbrook)
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LIST = os.path.join(ROOT, 'area_property_lists')

# user's column name -> website column name
MAP = {'s.0': 's.0', 'name of the project': 'name of the project', 'type': 'type', 'bhk': 'bhk', 'area_sqft': 'area_sqft',
       'area basis': 'area basis', 'no.of bathrooms': 'no.of bathrooms', 'floors': 'floors', 'floor no': 'floor no',
       'furnishing status': 'furnishing status', 'status': 'status', 'asking price': 'asking price', 'price_numeric': 'price_numeric',
       'price per sqft': 'price per sqft', 'lat-lon': 'lat-lon', 'source': 'sources', 'sources': 'sources', 'link': 'source url',
       'source url': 'source url', 'parking': 'parking', 'age_years': 'age_years', 'facing': 'facing',
       'orr connectivity': 'orr connectivity', 'airport distance': 'airport distance', 'nearby places': 'nearby places',
       'total amenities': 'total amenities', 'approach_road': 'approach road', 'main_road': 'main road'}

def norm_name(n): return re.sub(r'[^a-z0-9]', '', str(n or '').lower())
def num(v):
    try: return float(re.sub(r'[^\d.]', '', str(v)))
    except ValueError: return None
def link(v):
    s = str(v or '').strip()
    return s if s.lower().startswith('http') else ''

def read_xlsx(path, sheet=0):
    wb = openpyxl.load_workbook(path, data_only=True); ws = wb.worksheets[sheet]
    rows = [r for r in ws.iter_rows(values_only=True) if any(v not in (None, '') for v in r)]
    H = [str(h).strip().lower() if h is not None else '' for h in rows[0]]
    out = []
    for r in rows[1:]:
        d = {}
        for h, v in zip(H, r):
            if h in MAP and v not in (None, ''): d[MAP[h]] = v
        if 'source url' in d: d['source url'] = link(d['source url'])
        if not str(d.get('name of the project', '')).strip(): continue
        out.append(d)
    return out

def key(r):
    return (norm_name(r.get('name of the project')), str(num(r.get('bhk')) or ''), round(num(r.get('area_sqft')) or 0),
            round((num(r.get('price_numeric')) or 0) / 1e5))
def same(a, b):
    la, lb = link(a.get('source url')), link(b.get('source url'))
    if la and lb and la == lb: return True
    na, nb = norm_name(a.get('name of the project')), norm_name(b.get('name of the project'))
    if not na or not nb or SequenceMatcher(None, na, nb).ratio() < 0.85 or str(num(a.get('bhk'))) != str(num(b.get('bhk'))): return False
    sa, sb = num(a.get('area_sqft')), num(b.get('area_sqft')); pa, pb = num(a.get('price_numeric')), num(b.get('price_numeric'))
    if not (sa and sb and pa and pb): return False
    # the same flat listed on two websites: size and price agree within 2%
    if abs(sa - sb) > 0.02 * max(sa, sb) or abs(pa - pb) > 0.02 * max(pa, pb): return False
    fa, fb = num(a.get('floor no')), num(b.get('floor no'))
    return fa is None or fb is None or fa == fb

def merge(area, extra_rows, extra_name):
    base = list(csv.DictReader(open(os.path.join(LIST, f'{area}_Property.csv'), encoding='utf-8-sig')))
    cols = list(base[0].keys())
    merged = list(base); added = dup = 0
    for r in extra_rows:
        if any(same(r, b) for b in merged): dup += 1; continue
        r = {k: ('' if v is None else v) for k, v in r.items()}
        r['listed by website as'] = r.get('listed by website as') or area
        r['location basis'] = 'map pin' if r.get('lat-lon') else 'no map pin'
        r['checked on'] = r.get('checked on') or f'from {extra_name}'
        merged.append(r); added += 1
    # one more pass over everything, in case the base file and the new file each had repeats
    uniq = []
    for r in merged:
        if any(same(r, u) for u in uniq): dup += 1; continue
        uniq.append(r)
    for r in uniq:
        for k in r:
            if k not in cols: cols.append(k)
    for i, r in enumerate(uniq, 1): r['s.0'] = i
    out = os.path.join(LIST, f'{area}_merged.csv')
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader()
        for r in uniq: w.writerow({k: r.get(k, '') for k in cols})
    print(f'{area}: website file {len(base)} + {extra_name} {len(extra_rows)} -> added {added}, duplicates dropped {dup}, total {len(uniq)} unique rows')

merge('Kokapet', read_xlsx(os.path.join(HERE, 'data', 'Kokapet_checked.xlsx'), 0) + read_xlsx(os.path.join(HERE, 'data', 'Kokapet_construction.xlsx'), 0),
      'Kokapet_Projects-Data(checked).xlsx + Kokapet_Projects-Data(construction).xlsx')
merge('Gachibowli', read_xlsx(os.path.join(HERE, 'data', 'Gachibowli_google_distances.xlsx'), 0), 'Gachibowli_listings_v2.xlsx')
