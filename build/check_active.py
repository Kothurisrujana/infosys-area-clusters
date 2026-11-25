"""Check whether each listing link is still live on its portal.

    python build/check_active.py            (checks links not checked yet; results kept in build/data/link_status.json)

Rules, per portal:
  nobroker.in              the page states "active":true / false
  squareyards, houssed,    page loads with the listing title = active; 404 / 410 / sent elsewhere = removed
  rezy, housing
  99acres.com              blocks scripts (403); checked separately in a normal browser (same rules: loads = active)
  magicbricks.com          shows a maintenance page to scripts and cannot be opened here: "could not check"
One portal at a time per thread, with a pause between pages; a portal that starts refusing (403 / 429 / captcha)
is stopped for this run, not retried.
"""
import csv, json, os, re, time, threading, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); LIST = os.path.join(os.path.dirname(HERE), 'area_property_lists')
OUT = os.path.join(HERE, 'data', 'link_status.json')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
FILES = ['Gachibowli_merged.csv', 'Kokapet_merged.csv', 'Kondapur_Property.csv', 'Narsingi_Property.csv',
         'Gachibowli_site.csv', 'Kokapet_site.csv', 'Kondapur_site.csv', 'Narsingi_site.csv']
CHECK_HERE = ('nobroker.in', 'squareyards.com', 'houssed.com', 'rezy.in', 'housing.com')

def dom(u):
    m = re.match(r'https?://(?:www\.)?([^/]+)', u or ''); return m.group(1).lower() if m else ''

status = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
lock = threading.Lock()
def save():
    with lock:
        json.dump(status, open(OUT, 'w', encoding='utf-8'), indent=0, ensure_ascii=False)

links = set()
for f in FILES:
    p = os.path.join(LIST, f)
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            u = str(r.get('source url') or '').strip()
            if u.lower().startswith('http'): links.add(u)
by = {}
for u in sorted(links):
    by.setdefault(dom(u), []).append(u)

def check(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA, 'Accept-Language': 'en'}), timeout=25)
        code, final, body = r.status, r.geturl(), r.read().decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        code, final, body = e.code, u, ''
    except Exception as e:
        return {'state': 'error', 'why': type(e).__name__}
    if code in (404, 410): return {'state': 'removed', 'why': f'page gone ({code})'}
    if code in (403, 406, 429) or re.search(r'captcha|unusual traffic|access denied', body[:20000], re.I):
        return {'state': 'blocked', 'why': f'portal refused the check ({code})'}
    if code != 200: return {'state': 'error', 'why': f'http {code}'}
    if 'nobroker' in u:
        m = re.search(r'"active":(true|false)', body)
        if m: return {'state': 'active' if m.group(1) == 'true' else 'removed', 'why': 'portal says active' if m.group(1) == 'true' else 'portal says inactive (sold or taken down)'}
    t = re.search(r'<title>(.*?)</title>', body, re.I | re.S); title = t.group(1).strip() if t else ''
    path_kept = final.rstrip('/').split('/')[-1][:20] == u.rstrip('/').split('/')[-1][:20]
    if title and path_kept: return {'state': 'active', 'why': 'listing page loads'}
    return {'state': 'removed', 'why': 'listing page now sends you elsewhere'}

def run(d, urls):
    refused = 0
    for u in urls:
        if u in status and status[u]['state'] in ('active', 'removed'): continue
        res = check(u); res['checked'] = time.strftime('%Y-%m-%d'); status[u] = res
        refused = refused + 1 if res['state'] == 'blocked' else 0
        if len(status) % 25 == 0: save()
        if refused >= 3: print(d, 'stopped: the portal is refusing checks'); break
        time.sleep(0.8)
    save(); print(d, 'done', len(urls))

T = [threading.Thread(target=run, args=(d, by[d])) for d in CHECK_HERE if d in by]
for t in T: t.start()
for t in T: t.join()
# 99acres: list for the browser check
json.dump(sorted(u for u in by.get('99acres.com', []) if status.get(u, {}).get('state') not in ('active', 'removed')),
          open(os.path.join(HERE, 'data', 'links_99acres_todo.json'), 'w'), indent=0)
from collections import Counter
print({d: dict(Counter(status.get(u, {}).get('state', 'not checked') for u in v)) for d, v in by.items()})
