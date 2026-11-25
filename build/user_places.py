"""Places within 5 km of each listing, taken from the user's own FMV files
(Gachibowli_Property_FMV.csv, Kokapet_Property_FMV.csv, Kondapur_Property_FMV.csv).

Those files give, per project, the distance in km to named places (schools, hospitals, offices, ...).
Each website listing is matched to a row of those files by project name, or else by a map pin within 150 m,
and gets that row's places up to 5 km. Output: build/data/user_near.json, read by inject.py.

    python build/user_places.py
"""
import csv, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FMV = ['Gachibowli', 'Kokapet', 'Kondapur']
SITE = ['Gachibowli', 'Kokapet', 'Kondapur', 'Narsingi']
MAX_KM = 5.0
NOT_PLACES = {'s.0', 'name of the project', 'type', 'bhk', 'area_sqft', 'no.of bathrooms', 'floors', 'floor no', 'facing',
              'furnishing status', 'status', 'asking price', 'price_numeric', 'price per sqft', 'lat-lon', 'age_years', 'orr',
              'orr connectivity', 'airport distance', 'total amenities', 'nearby metro', 'price note', 'dist_financial_district_km',
              'begumpet airport'}
# kind of each place (checked in this order); names the keywords miss are listed by hand
KIND_HAND = {'phoenix': 'school', 'global edge': 'school', 'sloka global': 'school', 'ingenium world': 'school', 'rockwell school': 'school',
             'oakridge': 'school', 'gatik junior': 'school', 'gokul degree': 'school', 'padala ram reddi': 'school', 'cbit': 'school',
             'ssj engineering': 'school', 'nift college': 'school', 'gar': 'office', 'kokapet one': 'office', 'mn capital': 'office',
             'wipro circle': 'office', 'dlf cybercity': 'office', 'pranava business park': 'office', 'trendset jayabheri connect': 'office',
             'jayabheri silicon towers': 'office', 'tcs synergy park': 'office', 'microsoft campus': 'office', 'infosys gachibowli': 'office',
             'medihub': 'hospital', 'iswarya ivf&fertility': 'hospital', 'new era diagnostics': 'hospital', 'smart vision eye': 'hospital',
             'apollo dental': 'hospital', 'dr krishna sai ortho': 'hospital', 'bommineni cosmetic gynecology': 'hospital',
             'medicover neurology': 'hospital', 'iron kingdom': 'fitness', 'valuelabs cricket ground': 'fitness', 'gmc balayogi stadium': 'fitness',
             'ocean park': 'park', 'serenity park': 'park', 'neopolis view point': 'park', 'kokapet terminal': 'transport',
             'gachibowli flyover bus stop': 'transport', 'kondapur bus depot': 'transport', 'jesus prayers': 'worship',
             'house of transformation': 'worship', 'hare krishna': 'worship', 'gandipet gandimaissamma': 'worship',
             'shiva keshva mahasanidhnam': 'worship', 'shiva temple masjid banda': 'worship', 'masjid munawara': 'worship',
             'ratnadeep': 'shop', 'star bazaar': 'shop', 'vijetha supermarket': 'shop', 'spar kondapur': 'shop', 'ikea hyderabad': 'shop'}
KIND_RE = [('hospital', r'hospital|clinic|health|speciality'), ('school', r'school|college|university|vidyalaya|institute|iiit|business'),
           ('transport', r'metro|bus'), ('shop', r'mall|mart|market|ratnadeep|bazaar'), ('fitness', r'gym|fitness'),
           ('worship', r'temple|mosque|masjid|church'), ('park', r'park|garden|lake')]
SHOW = {'iiit hyderabad': 'IIIT Hyderabad', 'cbit': 'CBIT', 'nift college': 'NIFT College', 'klh university': 'KLH University',
        'dlf cybercity': 'DLF Cybercity', 'tcs synergy park': 'TCS Synergy Park', 'gar': 'GAR Infobharati', 'mn capital': 'MN Capital',
        'gmc balayogi stadium': 'GMC Balayogi Stadium', 'ikea hyderabad': 'IKEA Hyderabad', 'ssj engineering': 'SSJ Engineering College',
        'kims hospital kondapur': 'KIMS Hospital Kondapur', 'iswarya ivf&fertility': 'Iswarya IVF & Fertility', 'rai durg metro': 'Raidurg Metro',
        'dr krishna sai ortho': 'Dr Krishna Sai Ortho', 'phoenix': 'Phoenix Green School', 'oakridge': 'Oakridge International School',
        'e-fitness gym': 'E-Fitness Gym', 'ratnadeep': 'Ratnadeep', 'medihub': 'MediHub', 'padala ram reddi': 'Padala Rama Reddi Law College'}

def kind(n):
    if n in KIND_HAND: return KIND_HAND[n]
    for k, rx in KIND_RE:
        if re.search(rx, n): return k
    return 'other'
show = lambda n: SHOW.get(n) or ' '.join(w if w.isupper() else w[:1].upper() + w[1:] for w in n.split())
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
def pin(s):
    try: a, b = (float(x) for x in str(s).replace('"', '').split(',')); return a, b
    except Exception: return None
def km(p, q): return math.hypot((p[0] - q[0]) * 110.6, (p[1] - q[1]) * 106.2)
jskey = lambda p: f'{p[0]!r},{p[1]!r}'   # same text as JavaScript's  lat + ',' + lon

places, pidx, rows = [], {}, []
for area in FMV:
    for r in csv.DictReader(open(os.path.join(ROOT, f'{area}_Property_FMV.csv'), encoding='utf-8-sig')):
        p = pin(r.get('lat-lon'))
        if not p: continue
        near = []
        for k, v in r.items():
            k = (k or '').strip().lower()
            if not k or k in NOT_PLACES: continue
            try: d = float(v)
            except (TypeError, ValueError): continue
            if 0 <= d <= MAX_KM:
                if k not in pidx: pidx[k] = len(places); places.append([show(k), kind(k)])
                near.append([pidx[k], d])
        rows.append(dict(area=area, proj=norm(r['name of the project']), pin=p, near=sorted(near, key=lambda x: x[1])))

out, stat = {}, {'project': 0, 'pin': 0, 'none': 0}
for area in SITE:
    for r in csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', f'{area}_site.csv'), encoding='utf-8-sig')):
        p = pin(r.get('lat-lon'))
        if not p: continue
        n = norm(r['name of the project'])
        how = 'project'
        c = [x for x in rows if n and len(n) >= 5 and not n.startswith('unnamed') and x['proj'][:8] == n[:8]]
        if not c: how = 'pin'; c = [x for x in rows if km(p, x['pin']) < 0.15]
        c = [x for x in c if km(p, x['pin']) < 2]          # same name far away is a different place
        if not c: stat['none'] += 1; continue
        best = min(c, key=lambda x: (x['area'] != area, km(p, x['pin'])))
        stat[how] += 1
        out[jskey(p) + '|' + n] = best['near']
        out.setdefault(jskey(p), best['near'])
json.dump({'places': places, 'near': out}, open(os.path.join(HERE, 'data', 'user_near.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print(len(places), 'places;', stat)
