"""Turn the OpenStreetMap download (osm.json) into pois.json: clean, de-duplicated places by category.
Categories: metro (Hyderabad Metro stations only), it (IT offices and IT parks), school, hospital, park, food."""
import json, re, math, sys
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'osm.json', encoding='utf-8'))['elements']

def pos(e):
    if 'lat' in e: return e['lat'], e['lon']
    c = e.get('center'); return (c['lat'], c['lon']) if c else (None, None)
def km(a, b, c, d):
    x = (d - b) * math.cos((a + c) / 2 * math.pi / 180); y = c - a
    return math.hypot(x, y) * 111.32

IT_WORDS = re.compile(r"\b(it|tech|technolog\w*|software|soft|infotech|info ?park|infosys|systems?|solutions?|digital|data|cyber|cloud|labs?|computer\w*|"
    r"semiconductor\w*|analytics|consult\w*|services? pvt|global ?services|development cent\w*|innovation|engineering cent\w*|sez|mindspace|"
    r"waverock|divyasree|raheja|dlf|skyview|cyber ?towers?|knowledge ?city|financial ?district|campus|tower|park)\b", re.I)
BIG = re.compile(r"\b(tcs|wipro|infosys|accenture|deloitte|microsoft|google|amazon|facebook|meta|apple|oracle|ibm|cognizant|capgemini|hcl|tech mahindra|"
    r"cyient|value ?labs|honeywell|novartis|hsbc|wells fargo|jp ?morgan|j\.p\. morgan|bank of america|goldman|salesforce|qualcomm|intel|nvidia|adobe|"
    r"dell|hp|uber|thomson reuters|franklin templeton|state street|ubs|invesco|genpact|ey|kpmg|pwc|mphasis|ltimindtree|l&t|mindtree|virtusa|"
    r"globallogic|epam|synchrony|maq|bosch|oneplus|zf|micron|amd|ericsson|nokia|vodafone|airtel|ust|providence|optum|anthem|elevance|"
    r"mastercard|visa|fis|broadridge|cgi|ntt|dxc|sutherland|tata|infor|servicenow|workday)\b", re.I)
NOT_IT = re.compile(r"\b(food|restaurant|cafe|hotel|bank branch|atm|gas|plastics?|housing finance|insurance office|school|college|hospital|clinic|"
    r"temple|church|mosque|apartment|residen\w*|villa|mall|store|shop|mart|salon|gym|courier|travels?|real ?estate|builders?|construction)\b", re.I)

def cat(t):
    if t.get('station') == 'subway' or t.get('subway') == 'yes' and t.get('railway') != 'station' or t.get('network') == 'Hyderabad Metro' and t.get('railway') == 'station':
        return 'metro'
    if t.get('railway') == 'station' and ('Hyderabad Metro' in (t.get('network') or '') or t.get('station') in ('subway', 'Metro')): return 'metro'
    if t.get('railway') == 'station': return None            # MMTS / Indian Railways: not metro
    a = t.get('amenity')
    if a == 'school': return 'school'
    if a in ('college', 'university'): return None
    if a == 'hospital' or t.get('healthcare') == 'hospital': return 'hospital'
    if a == 'clinic': return None
    if t.get('leisure') == 'park': return 'park'
    if a in ('restaurant', 'cafe', 'fast_food', 'food_court'): return 'food'
    n = t.get('name') or ''
    if not n or NOT_IT.search(n): return None
    o = t.get('office')
    if o in ('it', 'telecommunication', 'software'): return 'it'
    if (o == 'company' or t.get('building') == 'office' or t.get('landuse') == 'commercial') and (IT_WORDS.search(n) or BIG.search(n)): return 'it'
    return None

HOSP_SMALL = re.compile(r"\b(dental|dentist|diagnostic\w*|lab|laborator\w*|pharmacy|physio\w*|scan\w*|eye care|optical)\b", re.I)
out = {k: [] for k in ('metro', 'it', 'school', 'hospital', 'park', 'food')}
for e in d:
    t = e.get('tags', {}); k = cat(t)
    if not k: continue
    la, lo = pos(e)
    if la is None: continue
    n = (t.get('name:en') or t.get('name') or '').strip()
    if k == 'metro':
        if t.get('station') == 'Metro' and 'Durgam' in n: pass
        n = re.sub(r"\s*\((Red|Blue|Green) Line\)$", '', n); n = re.sub(r"(?i)\s*metro( station)?$", '', n)
        n = {'Synchrony @ Raidurg': 'Raidurg', 'miyapur': 'Miyapur', 'Bharath Nagar': 'Bharat Nagar'}.get(n, n)
    if k == 'hospital' and HOSP_SMALL.search(n): continue
    if k in ('food', 'school', 'hospital', 'it') and not n: continue
    if k == 'park' and not n: n = 'Neighbourhood park'
    out[k].append([n, round(la, 5), round(lo, 5)])

# De-duplicate: the same name within 300 m (metro: same name anywhere within 1 km) is one place.
for k, v in out.items():
    keep = []
    for p in v:
        lim = 1.0 if k == 'metro' else 0.3
        if any(q[0].lower() == p[0].lower() and km(q[1], q[2], p[1], p[2]) < lim for q in keep): continue
        if k == 'park' and p[0] == 'Neighbourhood park' and any(km(q[1], q[2], p[1], p[2]) < 0.12 for q in keep): continue
        keep.append(p)
    out[k] = keep
json.dump(out, open('pois.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print({k: len(v) for k, v in out.items()})
print('metro:', sorted(p[0] for p in out['metro']))
print('it sample:', [p[0] for p in out['it'][:40]])

# ---------- big companies and IT parks (named brands) ----------
BRANDS = [('Microsoft','microsoft'),('Wipro','wipro'),('Google','google'),('Amazon','amazon'),('Infosys','infosys'),('TCS','tcs|tata consultancy'),
 ('Tech Mahindra','tech ?mahindra'),('Deloitte','deloitte'),('Accenture','accenture'),('Cognizant','cognizant'),('Capgemini','capgemini'),('HCLTech','hcl'),
 ('Oracle','oracle'),('Meta','\bmeta\b|facebook'),('Apple','\bapple\b'),('Qualcomm','qualcomm'),('Bank of America','bank of america'),('HSBC','hsbc'),
 ('JPMorgan','j\.?p\.? ?morgan'),('Wells Fargo','wells fargo'),('Goldman Sachs','goldman'),('Salesforce','salesforce'),('Novartis','novartis'),
 ('Honeywell','honeywell'),('ValueLabs','value ?labs'),('Cyient','cyient'),('Thomson Reuters','thomson reuters'),('Franklin Templeton','franklin templeton'),
 ('Uber','\buber\b'),('GlobalLogic','global ?logic'),('Capital One','capital one'),('ZF','\bzf\b'),('Bosch','bosch'),('Synchrony','synchrony'),
 ('Mindspace IT Park','mindspace'),('DLF Cybercity','dlf'),('Knowledge City','knowledge (city|park)'),('Wave Rock IT Park','wave ?rock'),
 ('Phoenix IT parks','ph(o|e)enix'),('Cyber Towers','cyber ?towers?'),('Raheja IT Park','raheja')]
for p in out['it']:
    for disp, rx in BRANDS:
        if re.search(rx, p[0], re.I): p.append(disp); break

# ---------- landmarks and ORR exits (from osm2.json) ----------
d2 = json.load(open('osm2.json', encoding='utf-8'))['elements']
lm, orr = [], []
MALL_OK = re.compile(r"mall|atrium|pvr icon", re.I); MALL_NO = re.compile(r"shoppinh|gsm mall|infinity mall|rr mall|shopping mall|family mall|dresses|collections|trends|silks|zudio|bazar", re.I)
LAKE_OK = re.compile(r"cheruvu|lake|sagar|talab|chervu", re.I)
LAKE_NO = re.compile(r"wipro|microsoft|cognitive|ql pond|sigma|timber|sds|sun city|reservoir|tank|pond|river|quarry|buffalo", re.I)
UNI = re.compile(r"indian school of business|international institute of information technology|university of hyderabad|urdu university|open university|klh university", re.I)
HOTEL = re.compile(r"hyatt|westin|novotel|trident|sheraton|itc|radisson|m.ridien|marriott|taj", re.I)
for e in d2:
    t = e.get('tags', {}); n = (t.get('name:en') or t.get('name') or '').strip(); la, lo = pos(e)
    if la is None: continue
    if t.get('highway') == 'motorway_junction':
        if t.get('ref'): orr.append([f"ORR Exit {t['ref']}" + (f" ({n})" if n else ''), round(la,5), round(lo,5)])
        continue
    if not n: continue
    if t.get('shop') == 'mall' and MALL_OK.search(n) and not MALL_NO.search(n): kind = 'Mall'
    elif t.get('natural') == 'water' and LAKE_OK.search(n) and not LAKE_NO.search(n): kind = 'Lake'
    elif t.get('leisure') == 'golf_course' and re.search(r"boulder|army golf", n, re.I): kind = 'Golf course'
    elif t.get('leisure') == 'stadium' and re.search(r"balayogi|pjr", n, re.I): kind = 'Stadium'
    elif t.get('amenity') == 'university' and UNI.search(n): kind = 'University'
    elif t.get('tourism') == 'hotel' and HOTEL.search(n): kind = 'Luxury hotel'
    elif t.get('leisure') == 'nature_reserve': kind = 'National park'
    else: continue
    n = n.replace('Le M\ufffdridien', 'Le Méridien')
    lm.append([n, round(la,5), round(lo,5), kind])
def dedupe(v, lim=0.4):
    k = []
    for p in v:
        if not any(q[0].lower() == p[0].lower() and km(q[1],q[2],p[1],p[2]) < lim for q in k): k.append(p)
    return k
out['landmark'] = dedupe(lm, 1.0); out['orr'] = dedupe([[re.sub(r' \(\)$','',x[0]),x[1],x[2]] for x in orr], 1.5)
json.dump(out, open('pois.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('brands tagged:', sum(1 for p in out['it'] if len(p) > 3), sorted({p[3] for p in out['it'] if len(p) > 3}))
print('landmarks:', len(out['landmark']), sorted({(p[3]) for p in out['landmark']}))
print([f"{p[0]} ({p[3]})" for p in out['landmark']])
print('orr:', out['orr'])
