"""Choose the listings the website shows for Gachibowli and Kokapet.

    python build/merge_listings.py      (first: builds the de-duplicated *_merged.csv files)
    python build/select_listings.py

Kokapet  (target 400, never more than 450):
  1. every listing that came from the user's own Kokapet files (checked + construction)
  2. every independent house and villa in Kokapet
  3. other named projects, a few listings each (map pin and price first), until the target is reached
Gachibowli (up to 200):
  the merged Gachibowli listings (the user's file + the website's) plus independent houses from
  Independent_Houses_List.xlsx that are in Gachibowli and not already listed.
Writes area_property_lists/Kokapet_site.csv and Gachibowli_site.csv.
"""
import csv, os, re, collections, importlib.util
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__)); LIST = os.path.join(os.path.dirname(HERE), 'area_property_lists')
spec = importlib.util.spec_from_file_location('ml', os.path.join(HERE, 'merge_listings.py'))
src = open(os.path.join(HERE, 'merge_listings.py'), encoding='utf-8').read()
ml = {'__file__': os.path.join(HERE, 'merge_listings.py')}; exec(src[:src.index("merge('Kokapet'")], ml)          # reuse same() / num() without re-running the merge
same, num = ml['same'], ml['num']
KOK_TARGET, KOK_MAX, GACH_MAX, PER_OTHER = 400, 450, 200, 6
read = lambda f: list(csv.DictReader(open(os.path.join(LIST, f), encoding='utf-8-sig')))
isHouse = lambda r: re.search(r'independent|villa|house', str(r.get('type', '')), re.I) is not None
fromUser = lambda r: str(r.get('checked on', '')).startswith('from ')

# ---------- only listings with a working portal link (results of build/check_active.py) ----------
import json
LS_PATH = os.path.join(HERE, 'data', 'link_status.json')
LS = json.load(open(LS_PATH, encoding='utf-8')) if os.path.exists(LS_PATH) else {}
NOT_CHECKABLE = {'99acres.com': 'not re-checked: 99acres asks scripts for a robot check',
                 'magicbricks.com': 'not re-checked: MagicBricks blocks automated checks',
                 'housing.com': 'not re-checked: Housing.com blocks automated checks'}
def url_of(r): return str(r.get('source url') or '').strip()
def has_portal(r):
    u = url_of(r).lower()
    return u.startswith('http') and 'docs.live.net' not in u
def link_state(r):
    u = url_of(r); s = LS.get(u)
    if s and s['state'] in ('active', 'removed'): return s['state'], f"{s['why']} (checked {s.get('checked', '')})"
    d = re.sub(r'^https?://(www\.)?', '', u).split('/')[0].lower()
    return 'unchecked', NOT_CHECKABLE.get(d, 'not re-checked: the portal did not answer')
def live(rows):
    out = []
    for r in rows:
        if not has_portal(r): continue
        st, why = link_state(r)
        if st == 'removed': continue
        r['portal check'] = ('Active on portal: ' if st == 'active' else 'Listed on portal 13 Nov 2026, ') + why
        out.append(r)
    return out
confirmed = lambda r: str(r.get('portal check', '')).startswith('Active')
DROPPED = {}
# each area: 200-300 listings. Confirmed-active listings first (up to 300, in the area's priority order);
# only if fewer than 200 are confirmed, listings that could not be re-checked fill up to 200.
AREA_MIN, AREA_MAX = 200, 300
def cap(ordered):
    ordered = [r for i, r in enumerate(ordered) if all(r is not x for x in ordered[:i])]
    keep = [r for r in ordered if confirmed(r)][:AREA_MAX]
    if len(keep) < AREA_MIN: keep += [r for r in ordered if not confirmed(r)][:AREA_MIN - len(keep)]
    ids = {id(r) for r in keep}
    return [r for r in ordered if id(r) in ids]

# ---------- Kokapet ----------
K = read('Kokapet_merged.csv'); cols = list(K[0].keys()) + ['portal check']
n0 = len(K); K = live(K); DROPPED['Kokapet'] = n0 - len(K)
pick = [r for r in K if fromUser(r)]
pick += [r for r in K if not fromUser(r) and isHouse(r) and r not in pick]
others = collections.defaultdict(list)
for r in K:
    if r in pick or re.match(r'unnamed', r['name of the project'], re.I): continue
    others[r['name of the project'].strip()].append(r)
spare = []
for name, rows in sorted(others.items(), key=lambda kv: -len(kv[1])):
    rows.sort(key=lambda r: (not confirmed(r), not r.get('lat-lon'), not num(r.get('price_numeric'))))
    pick += rows[:PER_OTHER]; spare += rows[PER_OTHER:]
pick = cap(pick + spare)
with open(os.path.join(LIST, 'Kokapet_site.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader()
    for i, r in enumerate(pick, 1): r['s.0'] = i; w.writerow(r)
nP = len({r['name of the project'].strip().lower() for r in pick})
print(f"Kokapet: {len(pick)} listings from {nP} projects | confirmed active {sum(map(confirmed, pick))} | dropped (no link or removed) {DROPPED['Kokapet']} | from your files {sum(map(fromUser, pick))} | "
      f"independent houses / villas {sum(map(isHouse, pick))} | other projects {len(pick) - sum(1 for r in pick if fromUser(r) or isHouse(r))}")

# ---------- Gachibowli ----------
G = read('Gachibowli_merged.csv'); gcols = list(G[0].keys())
wb = openpyxl.load_workbook(os.path.join(LIST, 'Independent_Houses_List.xlsx'))
ws = wb['Houses']; hdr = None; added = 0
for row in ws.iter_rows():
    vals = [c.value for c in row]
    if vals and vals[0] == 'ID': hdr = vals; continue
    if not hdr or not vals[0] or str(vals[1]).strip() != 'Gachibowli': continue
    d = dict(zip(hdr, vals))
    links = {c.column: c.hyperlink.target for c in row if c.hyperlink}
    li = hdr.index('Listing link') + 1; mi = hdr.index('Map location') + 1
    m = re.search(r'([\d.]+),\s*([\d.]+)', links.get(mi, '') or '')
    r = {'name of the project': d['Name / project'], 'type': d['Type'], 'bhk': d['BHK'] or '', 'area_sqft': d['Built-up (sqft)'] or '',
         'area basis': 'Built-up area', 'price_numeric': d['Total price (₹)'] or '', 'asking price': d['Price'] or '', 'price per sqft': d['₹ per sqft'] or '',
         'status': d['Status'] or '', 'floors': d['Floors'] or '', 'no.of bathrooms': d['Bathrooms'] or '', 'furnishing status': d['Furnishing'] or '',
         'parking': d['Parking'] or '', 'age_years': d['Age (years)'] or '', 'sources': d['Sources'] or '', 'source url': links.get(li, ''),
         'lat-lon': f'{m.group(1)},{m.group(2)}' if m else '', 'location basis': 'map pin' if m else 'no map pin',
         'listed by website as': 'Gachibowli', 'checked on': 'from Independent_Houses_List.xlsx'}
    if any(same(r, g) for g in G): continue
    G.append(r); added += 1
n0 = len(G); G = live(G); DROPPED['Gachibowli'] = n0 - len(G)
if 'portal check' not in gcols: gcols.append('portal check')
G = cap(G)
with open(os.path.join(LIST, 'Gachibowli_site.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=gcols, extrasaction='ignore'); w.writeheader()
    for i, r in enumerate(G, 1): r['s.0'] = i; w.writerow(r)
print(f"Gachibowli: {len(G)} listings | confirmed active {sum(map(confirmed, G))} | dropped (no link or removed) {DROPPED['Gachibowli']} | independent houses / villas {sum(map(isHouse, G))} | added from the houses list {added}")

# ---------- Narsingi and Kondapur (up to 300 each) ----------
# The user's project files have no listing links, so "active now" means: the project has at least one listing on the
# portals in the area file collected on 13 Nov 2026 (area_property_lists/<Area>_Property.csv).
from difflib import SequenceMatcher
pkey = lambda s: re.sub(r'\b(the|by|apartments?|residency|towers?|kondapur|narsingi|hyderabad|phase\s*\d*)\b|[^a-z0-9]', '', str(s or '').lower())
def user_rows(path, M):
    ws = openpyxl.load_workbook(path, data_only=True).active
    R = [r for r in ws.iter_rows(values_only=True) if any(v not in (None, '') for v in r)]
    H = [str(h).strip() if h else '' for h in R[0]]; out = []
    for r in R[1:]:
        d = dict(zip(H, r)); o = {}
        for k, src in M.items():
            v = src(d) if callable(src) else d.get(src)
            if v not in (None, ''): o[k] = v
        if o.get('name of the project'): out.append(o)
    return out
def status(v):
    s = str(v or '').lower()
    return 'Under Construction' if 'under' in s else ('Ready To Move' if s else '')
def cr(v):
    try: return round(float(v) * 1e7)
    except (TypeError, ValueError): return ''
NARS = {'name of the project': 'project name', 'bhk': 'BHK', 'area_sqft': 'area_sqft', 'price per sqft': 'price_per_sqft',
        'price_numeric': lambda d: cr(d.get('total_price')), 'asking price': lambda d: f"{d.get('total_price')} Cr" if d.get('total_price') else '',
        'lat-lon': lambda d: f"{d['latitude']},{d['longitude']}" if d.get('latitude') and d.get('longitude') else '',
        'status': lambda d: status(d.get('construction status')), 'furnishing status': 'furnishing status', 'sources': 'source',
        'age_years': 'age_years', 'total amenities': 'amenities count', 'orr connectivity': 'orr_connectivity',
        'listing year': 'year', 'type': lambda d: 'Villa' if 'villa' in str(d.get('project name', '')).lower() else 'Apartment'}
KOND = {'name of the project': 'Project Name', 'bhk': 'BHK', 'area_sqft': 'Area sqft', 'price per sqft': 'Builder Asking Price / Sqft',
        'price_numeric': lambda d: cr(d.get('Builder Asking Price - Total (Cr)')),
        'asking price': lambda d: f"{d.get('Builder Asking Price - Total (Cr)')} Cr" if d.get('Builder Asking Price - Total (Cr)') else '',
        'status': lambda d: status(d.get('Construction Status')), 'furnishing status': 'Furnishing Status', 'sources': 'source',
        'total amenities': 'Amenities Count', 'orr connectivity': 'ORR Dist (km)', 'airport distance': 'RGI Airport Dist (km)',
        'builder': 'Builder', 'listing year': 'year', 'type': lambda d: 'Villa' if 'villa' in str(d.get('Project Name', '')).lower() else 'Apartment'}
def build_area(area, path, M, limit=300):
    P = read(f'{area}_Property.csv'); cols = list(P[0].keys())
    n0 = len(P); P = live(P); DROPPED[area] = n0 - len(P)
    for c in ('listing year', 'orr connectivity', 'airport distance', 'builder', 'total amenities', 'portal check'):
        if c not in cols: cols.append(c)
    cur = collections.defaultdict(list)
    for r in P: cur[pkey(r['name of the project'])].append(r)
    def match(name):
        k = pkey(name)
        if k in cur: return k
        b = max(cur, key=lambda c: SequenceMatcher(None, k, c).ratio())
        return b if SequenceMatcher(None, k, b).ratio() >= .85 else None
    U = user_rows(path, M); act = []; inactive = set()
    for u in U:
        k = match(u['name of the project'])
        if not k: inactive.add(u['name of the project']); continue
        if not u.get('lat-lon'):                          # Kondapur file has no map pins: use the project's pin from the portals
            pin = next((p['lat-lon'] for p in cur[k] if p.get('lat-lon')), '')
            u['lat-lon'] = pin; u['location basis'] = "same project's map pin (portal)" if pin else 'no map pin'
        else: u['location basis'] = 'map pin (your file)'
        u['area basis'] = u.get('area basis', 'not stated'); u['listed by website as'] = area
        u['checked on'] = f"from {os.path.basename(path)} (year {u.get('listing year', '?')}); project active on portals 2026-11-13"
        u['_proj'] = k
        if any(same(u, a) for a in act): continue
        act.append(u)
    pick = []          # the user's own rows have no listing link, so they are left out (portal listings of the same projects are used)
    mine = {u['_proj'] for u in act}
    # fill with current portal listings: the user's projects first, then the rest
    rest = sorted(P, key=lambda r: (pkey(r['name of the project']) not in mine, not confirmed(r), not r.get('lat-lon'), re.match(r'unnamed', r['name of the project'], re.I) is not None))
    for r in rest:
        if any(same(r, a) for a in pick): continue
        pick.append(r)
    pick = cap(pick)
    with open(os.path.join(LIST, f'{area}_site.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader()
        for i, r in enumerate(pick, 1): r['s.0'] = i; w.writerow(r)
    print(f"{area}: {len(pick)} listings, all with portal links | of your projects {sum(pkey(r['name of the project']) in mine for r in pick)} | "
          f"confirmed active {sum(map(confirmed, pick))} | removed/no-link rows left out of the pool {DROPPED[area]}")
build_area('Narsingi', os.path.join(HERE, 'data', 'Narsingi_projects_Data.xlsx'), NARS)
build_area('Kondapur', os.path.join(HERE, 'data', 'Kondapur_projects.xlsx'), KOND)

# ---------- size check: the size the portal shows (written in the listing's own web address) ----------
# e.g. magicbricks.com/propertyDetails/3-BHK-2185-Sq-ft-... or 99acres ...-720-sqft-spid-...
# * every listing whose link carries a size gets that figure in "portal area_sqft (from listing link)"
# * a file size under 45% of the portal size is a typing error: it is replaced by the portal size, and the
#   file's figure is kept in "size in your file"; price per sqft is recalculated
# * a portal figure that cannot be right (a villa of "350 sq ft") is reported, the file's size is kept
MIN_SQFT = {1: 300, 2: 550, 3: 800, 4: 1100, 5: 1400}
for f in ('Gachibowli_site.csv', 'Kokapet_site.csv', 'Kondapur_site.csv', 'Narsingi_site.csv'):
    R = read(f); cols = list(R[0].keys())
    for c in ('size note', 'portal area_sqft (from listing link)', 'size in your file'):
        if c not in cols: cols.append(c)
    fixed = noted = 0
    for r in R:
        s_ = num(r.get('area_sqft')); b = num(r.get('bhk')); note = ''
        if r.get('size in your file'): s_ = num(r['size in your file'])          # re-runs start from the file's own figure
        m = re.search(r'-(\d{3,5})-sq-?ft', str(r.get('source url', '')), re.I)
        link = float(m.group(1)) if m else None
        r['portal area_sqft (from listing link)'] = int(link) if link else ''
        basis = str(r.get('area basis') or 'basis not stated').strip()
        carpet = 'carpet' in basis.lower(); unknown = not re.search(r'carpet|built|super|saleable|plot', basis, re.I)
        if s_ and link:
            q = s_ / link
            if q < 0.45:
                r['size in your file'] = int(s_); r['area_sqft'] = int(link)
                r['area basis'] = 'as shown on the portal (basis not stated)'
                pr = num(r.get('price_numeric'))
                if pr: r['price per sqft'] = round(pr / link)
                note = f"Corrected: your file had {int(s_):,} sqft ({basis}); the portal listing shows {int(link):,} sq ft"; fixed += 1
            elif q > 1.6:
                note = f"Portal link says {int(link):,} sq ft, which cannot be right for this home (probably {int(link):,} sq yd = {int(link * 9):,} sq ft); your file's {int(s_):,} sqft is kept"
            elif 0.55 <= q <= 0.9 and (carpet or unknown):
                note = (f"Carpet area {int(s_):,} sqft; the portal shows {int(link):,} sq ft, likely the super built-up size" if carpet else
                        f"Probably carpet area: {int(s_):,} sqft is {round(q * 100)}% of the {int(link):,} sq ft the portal shows (likely super built-up)")
            elif abs(q - 1) <= 0.02 and b and int(b) in MIN_SQFT and s_ < MIN_SQFT[int(b)]:
                note = f"Small for {int(b)} BHK, but the portal also shows {int(link):,} sq ft (may be the plot or a single floor)"
        if not note and s_ and b and int(b) in MIN_SQFT and s_ < MIN_SQFT[int(b)]:
            note = f"Doubtful size: {int(s_):,} sqft is very small for {int(b)} BHK ({basis}); not confirmed"
        r['size note'] = note; noted += bool(note)
    with open(os.path.join(LIST, f), 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(R)
    print(f'{f}: portal size known for {sum(1 for r in R if r["portal area_sqft (from listing link)"])} | corrected {fixed} | other notes {noted - fixed}')
