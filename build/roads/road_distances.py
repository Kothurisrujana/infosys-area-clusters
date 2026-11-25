"""Shortest driving distance along real roads (OpenStreetMap) from each listing to the nearest place of each kind.

    cd build/roads && python road_distances.py Gachibowli

Writes exports/<Area>_listings_road_distances.csv. The nearest place is chosen BY ROAD (it can differ from the
straight-line nearest one). One-way streets are respected for the drive; the last few metres at each end
(pin to road, road to the place) are added as straight lines.
"""
import csv, json, math, heapq, collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); BUILD = os.path.dirname(HERE); ROOT = os.path.dirname(BUILD)
area = sys.argv[1] if len(sys.argv) > 1 else 'Gachibowli'
HQ = (17.4350636, 78.3505964)
MAX_KM = 15                                     # stop searching beyond 15 km by road

def km(a, b):
    x = (b[1] - a[1]) * math.cos((a[0] + b[0]) / 2 * math.pi / 180); y = b[0] - a[0]; return math.hypot(x, y) * 111.32

# ---------- road graph (directed: one-way streets only one way) ----------
d = json.load(open(os.path.join(HERE, 'roads.json'), encoding='utf-8'))['elements']
N = {e['id']: (e['lat'], e['lon']) for e in d if e['type'] == 'node'}
G = collections.defaultdict(list); segs = []
for w in d:
    if w['type'] != 'way': continue
    t = w['tags']; h = t['highway']; ns = [n for n in w['nodes'] if n in N]
    ow = t.get('oneway'); fwd = back = True
    if ow in ('yes', '1', 'true') or t.get('junction') in ('roundabout', 'circular') or (h in ('motorway', 'motorway_link') and ow != 'no'): back = False
    if ow == '-1': fwd = False
    for a, b in zip(ns, ns[1:]):
        L = km(N[a], N[b])
        if fwd: G[a].append((b, L))
        if back: G[b].append((a, L))
        if h not in ('motorway', 'motorway_link'): segs.append((a, b))   # places and homes join ordinary roads, not the ORR
# keep only roads joined to the main network (small separate pieces would trap a place or a home)
U = collections.defaultdict(set)
for a_, lst in G.items():
    for b_, _ in lst: U[a_].add(b_); U[b_].add(a_)
comp = {}; big = None
for st in U:
    if st in comp: continue
    stack = [st]; comp[st] = st; size = 0
    while stack:
        u = stack.pop(); size += 1
        for v in U[u]:
            if v not in comp: comp[v] = st; stack.append(v)
    if big is None or size > big[1]: big = (st, size)
MAINC = big[0]
# a road piece you can enter but not leave (or the reverse) is also a trap: require reachability both ways
def reach(src, rev=False):
    R = collections.defaultdict(list)
    if rev:
        for x, lst in G.items():
            for y, _ in lst: R[y].append(x)
    seen = {src}; stack = [src]
    while stack:
        u = stack.pop()
        for v in (R[u] if rev else [y for y, _ in G[u]]):
            if v not in seen: seen.add(v); stack.append(v)
    return seen
_hub = max((n for n in G if comp.get(n) == MAINC), key=lambda n: len(G[n]))
OK = reach(_hub) & reach(_hub, True)
segs = [s_ for s_ in segs if s_[0] in OK and s_[1] in OK]
print('road pieces kept:', len(segs))
cell = 0.004; idx = collections.defaultdict(list)
for s in segs:
    a, b = N[s[0]], N[s[1]]
    for gx in range(int(min(a[0], b[0]) / cell), int(max(a[0], b[0]) / cell) + 1):
        for gy in range(int(min(a[1], b[1]) / cell), int(max(a[1], b[1]) / cell) + 1): idx[(gx, gy)].append(s)
def snap(p):
    """nearest ordinary road to point p: (offset km, [(node, km along the road to it), ...])"""
    best = None; gx, gy = int(p[0] / cell), int(p[1] / cell)
    for r in range(0, 6):
        for x in range(gx - r, gx + r + 1):
            for y in range(gy - r, gy + r + 1):
                if max(abs(x - gx), abs(y - gy)) != r: continue
                for s in idx.get((x, y), ()):
                    a, b = N[s[0]], N[s[1]]; c = math.cos(p[0] * math.pi / 180)
                    ax, ay, bx, by = (a[1] - p[1]) * c, a[0] - p[0], (b[1] - p[1]) * c, b[0] - p[0]
                    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy; t = 0 if L2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / L2))
                    q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t); D = km(p, q)
                    if best is None or D < best[0]: best = (D, s, q)
        if best and best[0] < cell * 111 * r: break
    if not best: return None
    D, (a, b), q = best
    return D, [(a, km(q, N[a])), (b, km(q, N[b]))]

# ---------- places (same lists and filters as the website) ----------
POIS = json.load(open(os.path.join(BUILD, 'places', 'pois.json'), encoding='utf-8'))
HOSP_NO = re.compile(r'clinic|gynecolog|dr\.? |physician|dental|skin', re.I); PARK_NO = re.compile(r'sez|tech|it park', re.I)
KINDS = [('infosys', [['Infosys (Gachibowli campus)', HQ[0], HQ[1]]], None, None),
         ('metro', POIS['metro'], None, None),
         ('office', POIS['it'], lambda p: not re.match(r'infosys', p[0], re.I), None),
         ('big_company', POIS['it'], lambda p: len(p) > 3 and p[3] != 'Infosys', lambda p: f"{p[3]} ({p[0]})" if p[3].lower() not in p[0].lower() else p[0]),
         ('school', POIS['school'], None, None),
         ('hospital', POIS['hospital'], lambda p: not HOSP_NO.search(p[0]), None),
         ('park', POIS['park'], lambda p: p[0] != 'Neighbourhood park' and not PARK_NO.search(p[0]), None),
         ('restaurant', POIS['food'], None, None),
         ('landmark', POIS['landmark'], None, lambda p: f"{p[0]} ({p[3].lower()})"),
         ('orr_exit', POIS['orr'], None, None)]
ORRN = {n for w in d if w['type'] == 'way' and w['tags']['highway'] == 'motorway' for n in w['nodes'] if n in N}
# every place joins the road network at its nearest road: node -> [(kind, name, km from node to the place)]
ARRIVE = collections.defaultdict(list); unplaced = 0
for kind, lst, ok, nm in KINDS:
    for p in lst:
        if ok and not ok(p): continue
        if kind == 'orr_exit':                      # an ORR exit is reached at its own junction on the ORR
            j = min(ORRN, key=lambda n: km(N[n], (p[1], p[2])))
            if km(N[j], (p[1], p[2])) < .1: ARRIVE[j].append((kind, p[0], 0)); continue
        sn = snap((p[1], p[2]))
        if not sn or sn[0] > 0.5: unplaced += 1; continue
        for node, along in sn[1]: ARRIVE[node].append((kind, nm(p) if nm else p[0], along + sn[0]))
print('places joined to roads; skipped (no road within 500 m or outside the road map):', unplaced)

def road_nearest(pin):
    sn = snap(pin)
    if not sn: return None, {}
    off, starts = sn
    D = {}; pq = []
    for n, along in starts: D[n] = off + along; pq.append((off + along, n))
    heapq.heapify(pq); best = {}
    while pq:
        dd, u = heapq.heappop(pq)
        if dd > D[u] or dd > MAX_KM: continue
        for kind, name, extra in ARRIVE.get(u, ()):
            tot = dd + extra
            if kind not in best or tot < best[kind][1]: best[kind] = (name, tot)
        if len(best) == len(KINDS) and all(v[1] <= dd for v in best.values()): break
        for v, L in G[u]:
            nd = dd + L
            if nd < D.get(v, 1e9): D[v] = nd; heapq.heappush(pq, (nd, v))
    return off, best

# ---------- the sheet ----------
ROADS = json.load(open(os.path.join(HERE, 'approach.json'), encoding='utf-8'))
rows = list(csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', f'{area}_Property.csv'), encoding='utf-8-sig')))
cols = []
for kind, *_ in KINDS:
    cols += [f'{kind}_road_km'] if kind == 'infosys' else [f'nearest_{kind}_by_road', f'{kind}_road_km']
cols += ['approach_road', 'main_road', 'main_road_km_by_road']
cache = {}
out_dir = os.path.join(ROOT, 'exports'); os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f'{area}_listings_road_distances.csv')
with open(out, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + cols); w.writeheader()
    for r in rows:
        o = {c: '' for c in cols}; v = (r.get('lat-lon') or '').strip()
        if v:
            lat, lon = (float(x) for x in v.split(','))
            if (lat, lon) not in cache: cache[(lat, lon)] = road_nearest((lat, lon))
            off, best = cache[(lat, lon)]
            for kind, *_ in KINDS:
                if kind in best:
                    if kind != 'infosys': o[f'nearest_{kind}_by_road'] = best[kind][0]
                    o[f'{kind}_road_km'] = round(best[kind][1], 2)
            x = ROADS.get(f'{lat},{lon}')
            if x:
                o['approach_road'] = x['app']['name'] or x['app']['kind']; o['main_road'] = x['main']['name']
                o['main_road_km_by_road'] = 0 if x['onMain'] else x['mainKm']
        w.writerow({**r, **o})
print('wrote', out, len(rows), 'rows,', len(cache), 'map pins')
