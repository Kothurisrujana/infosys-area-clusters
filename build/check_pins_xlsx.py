"""Add location checks to a listings workbook the user has edited, keeping their columns as they are.

    python build/check_pins_xlsx.py <input.xlsx> <output.xlsx> [Area]

Adds, right after the lat-lon column:
  pin_quality                - how the map pin was found and whether it disagrees with the listing website
  pin_on_google_maps         - opens the exact pin in Google Maps
  search_property_on_google  - searches Google Maps for the project name and address (to confirm the pin)
"""
import csv, os, re, sys
from urllib.parse import quote_plus
import openpyxl

src, dst = sys.argv[1], sys.argv[2]
area = sys.argv[3] if len(sys.argv) > 3 else 'Gachibowli'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# address and the website's own area label come from the original listing file (the edited sheet dropped them)
orig = {str(r['s.0']).strip(): r for r in csv.DictReader(open(os.path.join(ROOT, 'area_property_lists', f'{area}_Property.csv'), encoding='utf-8-sig'))}

NEAR = {'gachibowli', 'smondo gachibowli', 'nanakramguda', 'khajaguda', 'kokapet', 'kondapur', 'narsingi', 'financial district', 'telecom nagar',
        'indira nagar', 'whitefields', 'madhapur', 'kothaguda', 'gopanpally', 'hitech city', 'hitec city', 'raidurg', 'manikonda', 'puppalaguda',
        'jv colony', 'p janardhan reddy nagar', 'vinayak nagar', 'diamond hills', 'aphb colony', ''}
FAR = {'miyapur', 'old bowenpally', 'pocharam', 'kukatpally', 'bachupally', 'nizampet', 'secunderabad', 'uppal', 'lb nagar', 'ameerpet', 'kompally',
       'chandanagar', 'hafeezpet', 'bowenpally', 'alwal', 'medchal', 'shamshabad', 'begumpet', 'banjara hills', 'jubilee hills'}

def url_locality(u):
    m = re.search(r'-in-([a-z0-9-]+?)(?:-hyderabad|/|$)', (u or '').lower())
    return m.group(1).replace('-', ' ') if m else ''

def link(u, label): return f'=HYPERLINK("{u}","{label}")'

wb = openpyxl.load_workbook(src); ws = wb.active
H = [c.value for c in ws[1]]; rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
li = H.index('lat-lon')
pin_count = {}
for r in rows:
    if r[li]: pin_count[str(r[li]).strip()] = pin_count.get(str(r[li]).strip(), 0) + 1

def quality(r, o):
    pin = str(r[li] or '').strip(); web = (o.get('listed by website as') or '').strip()
    url = url_locality(r[H.index('source url')] if 'source url' in H else o.get('source url'))
    if not pin: return 'No exact location: the website gave only the area name, so no distances'
    why = []
    if web.lower() not in NEAR: why.append(f'website lists it under {web}')
    if url in FAR: why.append(f'its web link says {url.title()}')
    if why:
        return f'CHECK: map pin is in {area} but {" and ".join(why)} (address given: {(o.get("address") or "").strip() or "none"})'
    if pin_count[pin] >= 3: return f'Project map pin (shared by {pin_count[pin]} listings of this project)'
    return 'Map pin from the listing website'

out = openpyxl.Workbook(); w = out.active; w.title = ws.title
newH = H[:li + 1] + ['pin_quality', 'pin_on_google_maps', 'search_property_on_google'] + H[li + 1:]
w.append(newH)
for r in rows:
    o = orig.get(str(r[0]).strip(), {}); pin = str(r[li] or '').strip()
    name = str(r[H.index('name of the project')] or '').strip()
    q = ', '.join(x for x in [name if not name.lower().startswith('unnamed') else '', (o.get('address') or '').strip(), area, 'Hyderabad'] if x)
    add = [quality(r, o),
           link(f'https://www.google.com/maps/search/?api=1&query={pin.replace(" ", "")}', 'Pin') if pin else None,
           link('https://www.google.com/maps/search/?api=1&query=' + quote_plus(q), 'Search name')]
    w.append(r[:li + 1] + add + r[li + 1:])
out.save(dst)
print('wrote', dst, len(rows), 'rows')
