"""Final Gachibowli sheet: the user's V2 columns unchanged, plus one column per nearby hospital, school and park,
each cell holding the Google Maps best-route distance (km) from that property.

    python build/build_gachibowli_final.py <V2.xlsx> <scratch dir> <output.xlsx>

scratch dir holds: nearest_plan.json (known km from the sheet), google_nearest_routes.json, final_plan.json,
google_final_routes.json (all read from Google Maps driving routes).
"""
import json, sys
from copy import copy
import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Font

src, S, dst = sys.argv[1:4]
PL = json.load(open(f'{S}/nearest_plan.json', encoding='utf-8'))
R = {}
for f in ('google_nearest_routes.json', 'google_final_routes.json'): R.update(json.load(open(f'{S}/{f}', encoding='utf-8')))
FP = json.load(open(f'{S}/final_plan.json', encoding='utf-8'))
def kmv(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    n, u = v.split()[0], v.split()[1] if len(v.split()) > 1 else 'km'
    x = float(n.replace(',', '')); return round(x / 1000, 2) if u == 'm' else x
def dist(o, la, lo):
    k = f'{o}>{la},{lo}'
    return kmv(PL['known'].get(k)) if k in PL['known'] else kmv(R.get(k))

SHORT = {'Butterfly Hospitals Women and Children in Gachibowli': 'Butterfly Hospitals (Women & Children)',
         'Care Nest Multi Speciality Hospital': 'Care Nest Hospital', 'HK Hospitals': 'HK Hospitals', 'Kakatiya Hospital': 'Kakatiya Hospital',
         'LUX Hospitals | NABH Certified | Best in Hyderabad for Proctology, Gynecology, Orthopedics, Bariatric & Laparoscopic Surgery': 'LUX Hospitals',
         'MEDICARE Multispeciality Center': 'Medicare Multispeciality Center', 'Rajitha Hospital': 'Rajitha Hospital',
         'Anjaiah Nagar Primary School': 'Anjaiah Nagar Primary School', 'Howard Lake View School': 'Howard Lake View School',
         'Howard Public Schools': 'Howard Public School', 'MP primary & ZP high school': 'MP Primary & ZP High School',
         'MPP School Siddique Nagar': 'MPP School Siddique Nagar', 'Mandal parshad primary school gachibowli sher lingampally': 'Mandal Parishad Primary School',
         'My School ITALY | aVance': 'My School Italy (aVance)', 'Nasr Boys School': 'Nasr Boys School', 'Prerana Waldorf School': 'Prerana Waldorf School',
         'SHANTHINIKETAN SCHOOL': 'Shanthiniketan School', 'Slv Ma Vidyalay': 'SLV Vidyalay', 'Sparkles Montessori': 'Sparkles Montessori',
         'Sree Sarada School': 'Sree Sarada School', 'Sri Vijaya Bharathi High School': 'Sri Vijaya Bharathi High School',
         'St.Basweshwara High School': 'St. Basweshwara High School', 'Thrishitha school': 'Thrishitha School', 'VIDYA HIGH SCHOOL': 'Vidya High School',
         'iris florets Gachibowli': 'Iris Florets School'}
newh = [(SHORT.get(n, n), la, lo) for k, n, la, lo in FP['newhs'] if k == 'Hospital']
news = [(SHORT.get(n, n), la, lo) for k, n, la, lo in FP['newhs'] if k == 'School']
parks = [(f'Park: {n}', la, lo) for n, la, lo in FP['park_cols']]

ws = openpyxl.load_workbook(src).active
H = [c.value for c in ws[1]]
last = max(i for i, h in enumerate(H, 1) if h not in (None, ''))
li = H.index('lat-lon') + 1
hosp_end = H.index('Gaman Hospitals') + 1           # existing hospital columns end here; schools follow up to `last`
layout = [('old', c) for c in range(1, hosp_end + 1)] + [('new', x) for x in newh] + \
         [('old', c) for c in range(hosp_end + 1, last + 1)] + [('new', x) for x in news] + [('new', x) for x in parks]

LAKE = FP['lake']
out = openpyxl.Workbook(); o = out.active; o.title = ws.title
for j, (t, x) in enumerate(layout, 1):
    if t == 'old':
        s = ws.cell(1, x); d = o.cell(1, j, s.value)
        if s.has_style: d.font = copy(s.font); d.fill = copy(s.fill); d.alignment = copy(s.alignment); d.border = copy(s.border)
        if ws.column_dimensions[s.column_letter].width: o.column_dimensions[d.column_letter].width = ws.column_dimensions[s.column_letter].width
    else:
        o.cell(1, j, x[0]); o.column_dimensions[o.cell(1, j).column_letter].width = max(12, min(30, len(x[0]) + 2))
filled = empty = 0
for r in range(2, ws.max_row + 1):
    pin = str(ws.cell(r, li).value or '').replace(' ', '')
    name = str(ws.cell(r, H.index('name of the project') + 1).value or '')
    lake = (not pin) and name.strip() == 'Lake View Shravika Apartment'
    if lake: pin = LAKE['pin']
    origin = ','.join(str(float(v)) for v in pin.split(',')) if pin else None
    for j, (t, x) in enumerate(layout, 1):
        if t == 'old':
            s = ws.cell(r, x); d = o.cell(r, j, s.value)
            if s.has_style: d.font = copy(s.font); d.fill = copy(s.fill); d.alignment = copy(s.alignment); d.number_format = s.number_format
            if s.hyperlink: d.hyperlink = s.hyperlink.target
            # fill this row's empty Google columns when its location is now known
            if lake and d.value in (None, ''):
                h = H[x - 1]
                if h == 'lat-lon': d.value = LAKE['pin']; d.comment = Comment('Location found on Google Maps by the project name (the listing had no map pin).', 'data')
                elif h == 'infosys distance_km': d.value = dist(origin, 17.4350636, 78.3505964)
                elif h == 'infosys_google_route':
                    d.value = 'infosys_route_googlemaps'; d.font = Font(color='0563C1', underline='single')
                    d.hyperlink = f'https://www.google.com/maps/dir/?api=1&origin={origin}&destination=17.4350636,78.3505964&travelmode=driving'
                elif h == 'nearest_metro': d.value = LAKE['metro']
                elif h == 'metro distance_km': d.value = dist(origin, *LAKE['metro_ll'])
                elif h == 'nearest_large_company': d.value = LAKE['big']
                elif h == 'large_company_km': d.value = dist(origin, *LAKE['big_ll'])
                elif h == 'ORR_near': d.value = LAKE['orr']
                elif h == 'ORR_distance_km': d.value = dist(origin, *LAKE['orr_ll'])
        else:
            if origin:
                v = dist(origin, x[1], x[2])
                o.cell(r, j, v)
                if v is None: empty += 1
                else: filled += 1
# the 16 fixed hospital / school columns for the Lake View row
FIXED = {' AIG Hospitals ': (17.443272, 78.366276), 'CARE Hospitals': (17.430537, 78.372244), ' Himagiri Hospitals': (17.442311, 78.358711),
         'KIMS Arete': (17.427863, 78.375024), ' Medicover Hospitals': (17.446669, 78.380126), 'Omega Hospital Gachibowli': (17.436443, 78.367457),
         ' Apollo Spectra ': (17.459689, 78.366037), 'Gaman Hospitals': (17.436943, 78.356673), 'Delhi Public School': (17.435981, 78.364384),
         'Kendriya Vidyalaya': (17.439305, 78.355025), 'EuroSchool (CBSE)': (17.433263, 78.373661), 'Nasr School (ICSE)': (17.444518, 78.362673),
         'Oakridge International school': (17.419876, 78.364388), 'CHIREC International': (17.462607, 78.35144), ' Meridian School google': (17.453441, 78.383856),
         ' Resonance School ': (17.43933, 78.360334)}
OH = [c.value for c in o[1]]
for r in range(2, o.max_row + 1):
    if str(o.cell(r, OH.index('name of the project') + 1).value or '').strip() != 'Lake View Shravika Apartment': continue
    for h, (la, lo) in FIXED.items():
        c = o.cell(r, OH.index(h) + 1)
        if c.value in (None, ''): c.value = dist(LAKE['pin'], la, lo)
o.freeze_panes = ws.freeze_panes
out.save(dst)
print('wrote', dst, '| new columns:', len(newh) + len(news) + len(parks), '| new cells filled:', filled, '| left empty (no Google reading):', empty)
