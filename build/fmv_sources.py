"""Add source columns to Kokapet_Property_FMV.csv by matching each row to the collected listings
in area_property_lists/Kokapet_Property.csv. Writes Kokapet_Property_FMV_with_sources.csv next to it.
Run: python build/fmv_sources.py"""
import csv, os, re, collections, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
nm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
# FMV project name -> the names the same project has in the collected listings
ALIAS = {'Ambience Beaumonde': ['Koncept Ambience Beaumonde'], 'Cybercity Wesstbrook': ['Cybercity West Brook'],
 'Eka One By Raichandani': ['Eka One By Raichandanis', 'Raichandani Eka One'], 'Fortune Greenspace Celestial': ['Greenspace Celestial'],
 'Gauthami Green Blossoms': ['Green Blossoms', 'Green Blossoms Apartments'], 'Pearl Celestial': ['Bpr Pearl Celestial'],
 'Rajapushpa Atira': ['Rajapushpa Atria'], 'Rajapushpa Can0n dale': ['Cannon Dale'], 'One By Msn': ['MSN One'],
 'Sonthalia Fortune sky villas': ['Fortune Sonthalia Sky Villas', 'Sri Fortune Sonthalia Sky Villas'],
 'The Cascade Neopolis': ['GHR The Cascades Neopolis'], 'jaswitha luxur': ['Jaswitha Luxor Flat'],
 'Rajapushpa casa luxura': ['Rajapushpa Casa Luxura'], 'Sunshines Ecopolis': ['Sunshine Ecopolis', 'Sunshine S Ecopolis'],
 'Gem Nakshatra': ['Gem Naksatra', 'Gem Nakshathra', 'Gem Nakshathra, Kokapet, Hyderabad.', 'GGEMNAKSHATRA'],
 'Raghava Linq': ['Linq By Raghava', 'Linqraghava'], 'My Home Nishada': ['My homes nishidha'],
 'Godrej Epoque': ['EPOQUE - Godrej'], 'Frontline Seven': ['FRONTLINE SEVEN/KOKAPET']}
src = list(csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', 'Kokapet_Property.csv'), encoding='utf-8-sig')))
byp = collections.defaultdict(list)
for r in src: byp[nm(r['name of the project'])].append(r)
num = lambda s: float(re.sub(r'[^0-9.]', '', str(s)) or 0)
pf = os.path.join(ROOT, 'area_property_lists', 'portal_listings_pool.csv')
pool = list(csv.DictReader(open(pf, encoding='utf-8-sig'))) if os.path.exists(pf) else []
f = os.path.join(ROOT, 'Kokapet_Property_FMV.csv')
rows = list(csv.DictReader(open(f, encoding='utf-8-sig'))); cols = list(rows[0].keys())
NEW = ['source match', 'source website', 'source url', 'other source urls', 'matched listing', 'source checked on', 'search link']
out = collections.Counter()
for r in rows:
    p = r['name of the project']
    cand = [x for n in [p] + ALIAS.get(p, []) for x in byp.get(nm(n), [])]
    b = None
    if cand:
        same = lambda x, *c: all(x[k] == r[k] for k in c)
        tiers = [('Exact listing (same BHK, size and price)', [x for x in cand if same(x, 'bhk', 'area_sqft', 'price_numeric')]),
                 ('Same project, BHK and size; price differs', [x for x in cand if same(x, 'bhk', 'area_sqft')]),
                 ('Same project and BHK; size differs', [x for x in cand if same(x, 'bhk')]),
                 ('Same project only', cand)]
        for lab, c in tiers:
            if c:
                b = min(c, key=lambda x: (abs(num(x['area_sqft']) - num(r['area_sqft'])), abs(num(x['price_numeric']) - num(r['price_numeric'])), x['floor no'] != r['floor no']))
                break
    # Not exact in the cleaned list: look in every listing card saved from the portals (area_property_lists/portal_listings_pool.csv)
    if not (b and lab.startswith('Exact')):
        keys = [nm(n)[:7] for n in [p] + ALIAS.get(p, [])]
        pr, sq = num(r['price_numeric']), num(r['area_sqft'])
        hit = [x for x in pool if x['bhk'] == r['bhk'] and num(x['sqft']) == sq and any(k in nm(x['proj']) for k in keys)]
        for plab, c in [('Exact listing (same BHK, size and price)', [x for x in hit if num(x['price']) == pr]),
                        ('Probably the same listing; price changed by up to 3%', [x for x in hit if abs(num(x['price']) - pr) <= pr * .03])]:
            if c:
                x = min(c, key=lambda x: abs(num(x['price']) - pr)); lab = plab; b = None
                r.update({'source website': x['site'], 'source url': x['url'], 'other source urls': ' '.join(y['url'] for y in c if y is not x),
                          'source checked on': '2026-11', 'matched listing': f"{x['proj']}, {x['bhk']} BHK, {x['sqft']} sqft, ₹{num(x['price'])/1e7:.2f} Cr"})
                break
    q = urllib.parse.quote_plus(f"{p} Kokapet Hyderabad {r['bhk']} BHK {r['area_sqft']} sqft")
    r['search link'] = 'https://www.google.com/search?q=' + q
    if b:
        r['source match'] = lab; r['source website'] = b['sources']; r['source url'] = b['source url']
        r['other source urls'] = b['other source urls']; r['source checked on'] = b['checked on']
        r['matched listing'] = f"{b['name of the project']}, {b['bhk']} BHK, {b['area_sqft']} sqft, {b['asking price']}" + (f", floor {b['floor no']}" if b['floor no'] else '')
    elif r.get('source url'):
        r['source match'] = lab
    else:
        r['source match'] = 'Not found in collected listings'
        for c in NEW[1:-1]: r[c] = ''
    out[r['source match']] += 1
w = csv.DictWriter(open(os.path.join(ROOT, 'Kokapet_Property_FMV_with_sources.csv'), 'w', newline='', encoding='utf-8-sig'), cols[:1] + cols[1:2] + NEW + cols[2:])
w.writeheader(); w.writerows(rows)
for k, v in out.most_common(): print(v, k)
