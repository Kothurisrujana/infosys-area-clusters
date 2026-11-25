"""For every listing map pin: the road it sits on (approach road), the shortest route along roads to the
nearest main road (trunk/primary/secondary), its length and the roads it uses. Source: OpenStreetMap."""
import json, math, heapq, csv, collections, sys, re
d = json.load(open('roads.json', encoding='utf-8'))['elements']
N = {e['id']: (e['lat'], e['lon']) for e in d if e['type'] == 'node'}
W = [e for e in d if e['type'] == 'way']
def km(a, b):
    x = (b[1]-a[1])*math.cos((a[0]+b[0])/2*math.pi/180); y = b[0]-a[0]; return math.hypot(x, y)*111.32
ROADWORD = re.compile(r'(?i)(road|rd|street|st|lane|marg|highway|avenue|cross|colony road|main road)')
MAIN = {'trunk', 'primary', 'secondary'}
NM = json.load(open('names.json', encoding='utf-8'))['elements']
def epos(e): c = e.get('center', e); return (c['lat'], c['lon'])
ADDR = [(epos(e), e['tags']['addr:street'].strip()) for e in NM if 'addr:street' in e.get('tags', {}) and not re.search(r'(?i)^(unnamed|gachibowli|bhel|jntu campus|kondapur|madhapur|hyderabad)$', e['tags']['addr:street'].strip())]
COLONY = [(epos(e), e['tags']['name'].strip(), 'res') for e in NM if e['tags'].get('landuse') == 'residential' or 'residential' in e['tags']] +          [(epos(e), e['tags']['name'].strip(), 'place') for e in NM if 'place' in e['tags'] and e['tags']['place'] in ('neighbourhood', 'quarter', 'hamlet')]
def grid(pts, c=.002):
    g = collections.defaultdict(list)
    for x in pts: g[(int(x[0][0]/c), int(x[0][1]/c))].append(x)
    return g
AG = grid(ADDR)
def near(g, p, r, c=.002):
    gx, gy = int(p[0]/c), int(p[1]/c); k = int(r/(c*111))+1
    return [x for i in range(gx-k, gx+k+1) for j in range(gy-k, gy+k+1) for x in g.get((i, j), ()) if km(p, x[0]) <= r]
NOROUTE = {'motorway', 'motorway_link'}            # ORR: only reachable at exits, not a street you walk out onto
G = collections.defaultdict(list); segs = []; mainnode = {}
for i, w in enumerate(W):
    t = w['tags']; h = t['highway']
    if h in NOROUTE: continue
    ns = [n for n in w['nodes'] if n in N]
    for a, b in zip(ns, ns[1:]):
        L = km(N[a], N[b]); G[a].append((b, L, i)); G[b].append((a, L, i)); segs.append((a, b, i))
    if h in MAIN and t.get('bridge') != 'yes' and t.get('tunnel') != 'yes' and 'flyover' not in (t.get('name') or '').lower():
        for n in ns: mainnode[n] = i
# Unnamed streets: the street name most buildings along them give in their address (OpenStreetMap addr:street),
# leaving out names that belong to a named road right next to them.
NAMED_PTS = grid([(N[n], (W[i]['tags'].get('name') or '').lower()) for i, w in enumerate(W) if w['tags'].get('name') for n in w['nodes'][::2] if n in N])
ADDRNAME = {}
for i, w in enumerate(W):
    if w['tags'].get('name') or w['tags'].get('ref') or w['tags']['highway'] in NOROUTE: continue
    ns = [N[n] for n in w['nodes'] if n in N]; votes = collections.Counter()
    for p in ns[::2]:
        close = {x[1] for x in near(NAMED_PTS, p, .1)}
        for q, st in near(AG, p, .06):
            if st.lower() not in close: votes[st] += 1
    if votes:
        st, v = votes.most_common(1)[0]
        if (v >= 2 or len(ns) <= 6) and ROADWORD.search(st): ADDRNAME[i] = st
print('unnamed ways named from addresses:', len(ADDRNAME))
# name unnamed main-road ways after the nearest named main road of the same class
named = [(N[n], W[i]) for n, i in mainnode.items() if W[i]['tags'].get('name') or W[i]['tags'].get('ref')]
def wname(w):
    if isinstance(w, int): w = W[w]
    t = w['tags']; return (t.get('name:en') or t.get('name') or t.get('ref') or '').strip()
# ORR service roads: secondary roads running beside the motorway
orrpts = [N[n] for w in W if w['tags']['highway'] == 'motorway' for n in w['nodes'] if n in N]
oidx = collections.defaultdict(list)
for q in orrpts: oidx[(int(q[0]/.002), int(q[1]/.002))].append(q)
def near_orr(p):
    gx, gy = int(p[0]/.002), int(p[1]/.002)
    return any(km(p, q) < .4 for x in range(gx-2, gx+3) for y in range(gy-2, gy+3) for q in oidx.get((x, y), ()))
# unnamed main roads take the name of the nearest named main road they connect to
mw = collections.defaultdict(set)
for n, i in mainnode.items(): mw[n].add(i)
wn = collections.defaultdict(set)
for n, s_ in mw.items():
    for i in s_: wn[i] |= s_
def bfs_name(i):
    seen = {i}; fr = [i]
    for _ in range(12):
        nx = []
        for j in fr:
            for k in wn[j]:
                if k in seen: continue
                seen.add(k)
                if wname(W[k]): return wname(W[k])
                nx.append(k)
        fr = nx
    return ''
V = json.load(open('../data/villages_final.json', encoding='utf-8'))
def inring(p, R):
    c = False; j = len(R)-1
    for k in range(len(R)):
        a, b = R[k], R[j]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]: c = not c
        j = k
    return c
def village(p):
    for v in V:
        if any(inring(p, R) for R in v['rings']): return v['name']
    return ''
cache = {}
def main_name(i):
    if i in cache: return cache[i]
    w = W[i]; n = wname(w)
    if not n:
        p = N[[x for x in w['nodes'] if x in N][0]]
        best = min(named, key=lambda q: km(p, q[0]) + (0 if q[1]['tags']['highway'] == w['tags']['highway'] else 0.3))
        n = bfs_name(i) or (wname(best[1]) if km(p, best[0]) < 0.8 else '')
    p = N[[x for x in w['nodes'] if x in N][len([x for x in w['nodes'] if x in N])//2]]
    if (not n or n.lower() == 'service road') and near_orr(p): n = 'ORR service road'
    if not n or n.lower() == 'service road':
        vg = village(p); kind = 'Service road' if n else 'Main road'
        n = f"{vg} {kind.lower()}" if vg else kind
    cache[i] = n; return cache[i]
# multi-source Dijkstra from every main-road node
dist = {n: 0.0 for n in mainnode}; pred = {}; pq = [(0.0, n) for n in mainnode]; heapq.heapify(pq)
while pq:
    dd, u = heapq.heappop(pq)
    if dd > dist[u]: continue
    for v, L, i in G[u]:
        nd = dd + L
        if nd < dist.get(v, 1e9): dist[v] = nd; pred[v] = (u, i); heapq.heappush(pq, (nd, v))
# grid index of segments for snapping
cell = 0.004; idx = collections.defaultdict(list)
for s in segs:
    a, b = N[s[0]], N[s[1]]
    for gx in range(int(min(a[0], b[0])/cell), int(max(a[0], b[0])/cell)+1):
        for gy in range(int(min(a[1], b[1])/cell), int(max(a[1], b[1])/cell)+1): idx[(gx, gy)].append(s)
def proj(p, a, b):
    c = math.cos(p[0]*math.pi/180); ax, ay = (a[1]-p[1])*c, a[0]-p[0]; bx, by = (b[1]-p[1])*c, b[0]-p[0]
    dx, dy = bx-ax, by-ay; L2 = dx*dx+dy*dy; t = 0 if L2 == 0 else max(0, min(1, -(ax*dx+ay*dy)/L2))
    q = (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t); return km(p, q), q, t
def snap(p):
    best = None
    for r in range(0, 4):
        gx, gy = int(p[0]/cell), int(p[1]/cell)
        for x in range(gx-r, gx+r+1):
            for y in range(gy-r, gy+r+1):
                for s in idx.get((x, y), ()):
                    D, q, t = proj(p, N[s[0]], N[s[1]])
                    if best is None or D < best[0]: best = (D, q, t, s)
        if best and best[0] < cell*111*r: break
    return best
KIND = {'residential': 'colony road', 'service': 'internal / service road', 'living_street': 'narrow lane', 'unclassified': 'local road',
        'tertiary': 'link road', 'tertiary_link': 'link road', 'road': 'local road', 'secondary': 'main road', 'primary': 'main road', 'trunk': 'highway',
        'secondary_link': 'main road slip road', 'primary_link': 'main road slip road', 'trunk_link': 'highway slip road'}
def wdesc(i):
    w = W[i]; h = w['tags']['highway']; n = wname(w); src = 'osm' if n else ''
    if not n and i in ADDRNAME: n = ADDRNAME[i]; src = 'addr'
    return {'name': n, 'src': src, 'kind': KIND.get(h, h), 'hw': h, 'lanes': w['tags'].get('lanes'), 'oneway': w['tags'].get('oneway') == 'yes'}
# ---------- traffic ----------
# Junctions reported as peak-hour bottlenecks (news reports quoting Cyberabad traffic police / civic bodies, 2025-26).
HOT = [('Biodiversity Junction', 17.42914, 78.37447, 'heavy'), ('Mindspace Junction (Raidurg)', 17.43898, 78.37783, 'heavy'),
       ('IKEA Junction', 17.4391, 78.37532, 'heavy'), ('Cyber Towers Junction', 17.45158, 78.38108, 'heavy'),
       ('Gachibowli flyover works (IIIT Junction)', 17.43757, 78.36492, 'heavy'), ('Khajaguda Junction', 17.42265, 78.38173, 'heavy'),
       ('Financial District ORR interchange', 17.41298, 78.33863, 'heavy'), ('Kokapet ORR interchange', 17.4049, 78.33456, 'heavy'),
       ('My Home Avatar Junction, Kokapet', 17.39839, 78.35534, 'heavy'), ('Narsingi Circle', 17.38566, 78.35412, 'busy'),
       ('Kokapet Circle', 17.38657, 78.34742, 'busy')]
def hot_near(p, r):
    b = min(HOT, key=lambda h: km(p, (h[1], h[2]))); D = km(p, (b[1], b[2])); return (b, D) if D <= r else (None, D)
def peak_level(p):
    h, D = hot_near(p, 1.2)
    if h: return ('Heavy' if h[3] == 'heavy' else 'Busy'), h[0], round(D, 2)
    h, D = hot_near(p, 2.5)
    if h: return 'Busy', h[0], round(D, 2)
    return 'Moderate', '', None
# speeds (km/h) by road type; peak values sit around TomTom's 2025 Hyderabad rush-hour average of 16 km/h,
# and drop to 12 km/h within 1 km of a reported bottleneck (IT-corridor peak speeds reported at 12-15 km/h)
SP_N = {'motorway': 60, 'motorway_link': 35, 'trunk': 35, 'trunk_link': 25, 'primary': 30, 'primary_link': 22, 'secondary': 28, 'secondary_link': 20, 'tertiary': 22, 'tertiary_link': 18}
SP_P = {'motorway': 40, 'motorway_link': 20, 'trunk': 18, 'trunk_link': 14, 'primary': 16, 'primary_link': 13, 'secondary': 16, 'secondary_link': 13, 'tertiary': 14, 'tertiary_link': 12}
G2 = collections.defaultdict(list)
for i, w in enumerate(W):
    h = w['tags']['highway']; ns = [n for n in w['nodes'] if n in N]
    for a, b in zip(ns, ns[1:]):
        L = km(N[a], N[b]); mid = ((N[a][0]+N[b][0])/2, (N[a][1]+N[b][1])/2)
        tn = L/SP_N.get(h, 16)*60; sp = SP_P.get(h, 12)
        if h not in ('motorway',) and hot_near(mid, 1.0)[0]: sp = min(sp, 12)
        tp = L/sp*60; G2[a].append((b, L, tn, tp)); G2[b].append((a, L, tn, tp))
def dijk(src, k):
    D = {src: 0.0}; pq = [(0.0, src)]
    while pq:
        dd, u = heapq.heappop(pq)
        if dd > D[u]: continue
        for e in G2[u]:
            nd = dd + e[k]
            if nd < D.get(e[0], 1e9): D[e[0]] = nd; heapq.heappush(pq, (nd, e[0]))
    return D
HQ = (17.4350636, 78.3505964)
hq = snap(HQ)[3][0]
IK, IN, IP = dijk(hq, 1), dijk(hq, 2), dijk(hq, 3)
out = {}
pins = set(); PADDR = collections.defaultdict(list)
ROADWORD = re.compile(r'(?i)\b(road|rd|street|st|lane|marg|highway|avenue|cross|colony road|main road)\b')
def addr_road(a):
    """The road named in a listing's address, e.g. 'Near X School, Keystone School Rd, Financial District' -> 'Keystone School Road'."""
    for seg in re.split(r'[,;]', a):
        seg = seg.strip(' .-')
        m = re.search(r"(?i)([A-Za-z0-9&' .-]{2,45}?\b(road|rd|street|lane|marg|highway))\.?\s*$", seg)
        if not m: continue
        n = re.sub(r'(?i)\brd\b', 'Road', m.group(1)).strip(' .-')
        n = re.sub(r'(?i)^(near|opp|opposite|beside|behind)\s+', '', n)
        if re.search(r'(?i)unnamed|^(main|service|the|new|old)\s+road$', n) or len(n) <= 5: continue
        return n[0].upper() + n[1:]
    return ''
CG = grid(COLONY)
root = r'C:/Users/kothu/Downloads/Clustering/area_property_lists/'
import os
FILES = [f + '_Property.csv' for f in ['Gachibowli', 'Nanakramguda', 'Khajaguda', 'Kokapet', 'Kondapur', 'Narsingi']] +         [f + '_site.csv' for f in ['Gachibowli', 'Kokapet', 'Kondapur', 'Narsingi']]          # the website's current listing files too
for f in FILES:
    if not os.path.exists(root + f): continue
    for r in csv.DictReader(open(root+f, encoding='utf-8-sig')):
        v = r['lat-lon'].strip()
        if v:
            p_ = tuple(float(x) for x in v.split(',')); pins.add(p_)
            if not re.search(r'label only', r.get('location basis') or '', re.I): PADDR[p_].append(r.get('address') or '')
for p in pins:
    D, q, t, (a, b, i) = snap(p)
    # leave the pin's road from whichever end is closer to a main road
    ca = dist.get(a, 1e9) + km(q, N[a]); cb = dist.get(b, 1e9) + km(q, N[b])
    s, tot = (a, ca) if ca <= cb else (b, cb)
    path = [q, N[s]]; roads = [i]; u = s
    while u in pred: u, wi = pred[u]; path.append(N[u]); roads.append(wi)
    hit = mainnode.get(u)
    onmain = W[i]['tags']['highway'] in MAIN
    # roads used, in order, merging repeats of the same road
    seq = []
    for wi in roads:
        de = wdesc(wi); key = (de['name'] or de['kind'])
        if not seq or seq[-1]['key'] != key: seq.append({'key': key, **de, 'km': 0})
    # length per road along the path
    k = 0; segk = [km(path[j], path[j+1]) for j in range(len(path)-1)]
    rk = [roads[0]] + roads[1:]
    lens = collections.OrderedDict()
    for j, L in enumerate(segk):
        wi = roads[min(j, len(roads)-1)]; de = wdesc(wi); key = de['name'] or de['kind']; lens[key] = lens.get(key, 0) + L
    for s_ in seq: s_['km'] = round(lens.get(s_['key'], 0), 2); s_.pop('key')
    mi = hit if hit is not None else i
    jp = path[-1] if not onmain else q
    lvl, hname, hkm = peak_level(jp)
    ah = W[i]['tags']['highway']; ak = 0 if onmain else tot
    # time to the main road: colony/internal roads ~15 km/h normally, ~10 km/h at office hours (gate and school queues)
    an, ap = ak/15*60, ak/10*60
    ends = [(a, km(q, N[a])), (b, km(q, N[b]))]
    inf = min(((IK.get(n, 1e9)+x, IN.get(n, 1e9)+x/15*60, IP.get(n, 1e9)+x/10*60) for n, x in ends), key=lambda z: z[1])
    # simplify the path (drop points closer than 25 m)
    sp = [path[0]]
    for pt in path[1:-1]:
        if km(sp[-1], pt) > 0.025: sp.append(pt)
    sp.append(path[-1])
    app = wdesc(i)
    if not app['name'] and onmain: app['name'] = main_name(i); app['src'] = 'osm'
    if not app['name']:
        ar = collections.Counter(x for x in (addr_road(a) for a in PADDR.get(p, [])) if x)
        if ar: app['name'] = ar.most_common(1)[0][0]; app['src'] = 'listing'
    if not app['name']:
        cl = sorted(near(CG, p, .25 if app['hw'] == 'service' else .6), key=lambda x: (x[2] != 'res', km(p, x[0])))
        fv = next((v for v in seq if v.get('name')), None)
        if app['hw'] == 'service' and cl and cl[0][2] == 'res': app['name'] = f"Internal road of {cl[0][1]}"; app['src'] = 'colony'
        elif cl and cl[0][2] == 'place': app['name'] = f"{cl[0][1]} colony road"; app['src'] = 'colony'
        elif fv: app['name'] = f"Lane off {fv['name']}"; app['src'] = 'lane'
        elif not onmain: app['name'] = f"Lane off {main_name(mi)}"; app['src'] = 'lane'
    if seq and not seq[0].get('name') and app['name']: seq[0]['name'] = app['name']; seq[0]['src'] = app['src']
    out[f'{p[0]},{p[1]}'] = {'pinKm': round(D, 3), 'app': app, 'onMain': onmain, 'mainKm': 0 if onmain else round(tot, 2),
        'main': {'name': main_name(mi), 'hw': W[mi]['tags']['highway'], 'lanes': W[mi]['tags'].get('lanes')},
        'via': [] if onmain else seq,
        'traffic': {'peak': lvl, 'hot': hname, 'hotKm': hkm, 'toMainMin': [round(an, 1), round(ap, 1)],
                    'infosys': {'km': round(inf[0], 1), 'min': [round(inf[1]), round(inf[2])]}}, 'path': [] if onmain else [[round(x, 5), round(y, 5)] for x, y in sp]}
json.dump(out, open('approach.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
v = list(out.values())
print(len(v), 'on main', sum(x['onMain'] for x in v), 'pin>100m', sum(x['pinKm'] > .1 for x in v))
ks = sorted(x['mainKm'] for x in v); print('mainKm quartiles', ks[len(ks)//4], ks[len(ks)//2], ks[3*len(ks)//4], ks[-1])
print(collections.Counter(x['main']['name'] for x in v).most_common(40))
print(collections.Counter(x['app']['kind'] for x in v)); print(collections.Counter(x['app']['src'] or 'none' for x in v)); import random; random.seed(3); print([x['app']['name'] for x in random.sample(v,30)])
print(collections.Counter(x['traffic']['peak'] for x in v)); print(sorted(x['traffic']['infosys']['km'] for x in v)[::80]); print(sorted(x['traffic']['infosys']['min'][1] for x in v)[::80])
print('size', len(json.dumps(out, ensure_ascii=False)))
