"""Build website/four_areas.html: the six-area website design (commit dfacd4a, kept in build/site_template_six.html)
with only Gachibowli, Kokapet, Kondapur and Narsingi, using the current listing files (*_site.csv: listings with
portal links, active ones first).

    python build/roads/roads.py   (run inside build/roads: approach roads for every map pin)
    python build/inject_four.py
"""
import re, os, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def here(*p): return os.path.join(HERE, *p)

PRELOAD_FILES = {'Gachibowli': 'Gachibowli_site.csv', 'Kokapet': 'Kokapet_site.csv',
                 'Kondapur': 'Kondapur_site.csv', 'Narsingi': 'Narsingi_site.csv'}

m = open(os.path.join(ROOT, 'Infosys_9km_Area_Map.html'), encoding='utf-8').read()
data = re.search(r'AREAS=(\[.*?\]);', m, re.S).group(1)
pre = {n: {'file': f, 'csv': open(os.path.join(ROOT, 'area_property_lists', f), encoding='utf-8-sig').read()} for n, f in PRELOAD_FILES.items()}

V = json.load(open(here('data', 'villages_final.json'), encoding='utf-8'))
B = json.load(open(here('data', 'borders_final.json'), encoding='utf-8'))
for v in V:
    if v['name'] in B: B[v['name']] = {'kind': 'village', 'label': v['name'] + ' revenue village', 'rings': v['rings']}
pois = open(here('places', 'pois.json'), encoding='utf-8').read()
roads = json.load(open(here('roads', 'approach.json'), encoding='utf-8'))
for v in roads.values(): v.pop('traffic', None)            # the site does not show traffic
roads = json.dumps(roads, ensure_ascii=False, separators=(',', ':'))

t = open(here('site_template_six.html'), encoding='utf-8').read()
old = "want=q==null?'Gachibowli,Nanakramguda,Khajaguda':"
assert t.count(old) == 1
t = t.replace(old, "want=q==null?'Gachibowli,Kokapet,Kondapur,Narsingi':").replace('open with the three Financial District areas', 'open with the four areas')

# no uploading: the four areas' listings are built in and clustered straight away
for a, b in [('<label id="drop" for="file">', '<label id="drop" for="file" hidden style="display:none">'),
             ('<input id="file" type="file"', '<input id="file" type="file" hidden disabled'),
             ('<form id="confirm" hidden>', '<form id="confirm" hidden style="display:none!important">'),
             ('<div class="group" style="margin-top:8px"><button class="btn small" id="dlTemplate"', '<div class="group" style="margin-top:8px;display:none" hidden><button class="btn small" id="dlTemplate"'),
             ("drop.addEventListener('drop',e=>onFiles(e.dataTransfer.files));", "drop.addEventListener('drop',e=>e.preventDefault());"),
             ("`${AREAS.length} areas · ${up} uploaded`", "`${AREAS.length} areas · ${up} loaded`"),
             ("<h2>All uploaded areas</h2>", "<h2>All loaded areas</h2>"), ("all uploaded areas", "all loaded areas"), ("the uploaded areas", "the loaded areas")]:
    assert a in t, a[:50]
    t = t.replace(a, b)

j = lambda o, **k: json.dumps(o, separators=(',', ':'), **k)
t = (t.replace('__DATA__', data)
      .replace('__BORDERS__', j(B, ensure_ascii=False))
      .replace('__VILLAGES__', j(V))
      .replace('__POIS__', pois)
      .replace('__ROADS__', roads.replace('</', '<\\/'))
      .replace('__HOT__', '[]')
      .replace('__PRELOAD__', json.dumps(pre, ensure_ascii=False).replace('</', '<\\/')))
out = os.path.join(ROOT, 'website', 'four_areas.html')
open(out, 'w', encoding='utf-8').write(t)
print('ok', out, len(t), {n: v['csv'].count('\n') - 1 for n, v in pre.items()})
