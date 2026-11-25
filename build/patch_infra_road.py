"""Show road distances (Google for Gachibowli, Mapbox for Kokapet and Narsingi) in the listing card, the hexagon
overview and the listing table. Run once on build/site_template.html, then python build/inject.py."""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'site_template.html'); shutil.copy(f, f + '.bak_infra')
t = open(f, encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a[:80], t.count(a)); t = t.replace(a, b)

# ---------- data ----------
rep("const ROADS=__ROADS__,BOTTLENECKS=__HOT__;", r"""const ROADS=__ROADS__,BOTTLENECKS=__HOT__;
/* Road (driving) distances per map pin: Google Maps best route for Gachibowli, Mapbox driving route for Kokapet and Narsingi. */
const INFRA=__INFRA__;
const infraOf=r=>r.lat==null?null:(INFRA[r.lat+','+r.lon]||null);
const SRC_TXT={google:'Google Maps best route',mapbox:'Mapbox driving route'};""")

# ---------- listing card: road distances first, straight-line places folded below ----------
rep("""  return `<div class="lcard">${head}<div class="lc-g">${tiles}</div><p class="nbsrc">Bars run from 0 to ${CARD_KM} km: a short bar means close. Straight-line distance from the map pin, except the main road (by road).</p></div>`;
}""", """  const I=infraOf(r);
  if(!I)return `<div class="lcard">${head}<div class="lc-g">${tiles}</div><p class="nbsrc">Bars run from 0 to ${CARD_KM} km: a short bar means close. Straight-line distance from the map pin, except the main road (by road). No road distances were collected for this area.</p></div>`;
  const one=(c,lab,nm,d)=>`<div class="lc-t"><div class="lc-l"><i style="background:${c}"></i>${lab}</div><div class="lc-d">${d==null?'–':kmTxt(d)}</div>${d!=null?kmBar(d,c):''}<div class="lc-n">${nm?esc(nm):''}</div></div>`;
  const many=(c,lab,L,n)=>!L||!L.length?'':`<div class="lc-t lc-list"><div class="lc-l"><i style="background:${c}"></i>${lab}</div>${L.slice(0,n).map(([nm,d],i)=>`<div class="lc-row${i?'':' first'}"><span>${esc(nm)}</span><b>${kmTxt(d)}</b></div>${i?'':kmBar(d,c)}`).join('')}</div>`;
  const road=[one('#0c5f68','Infosys office','Gachibowli campus',I.inf),
    I.metro?one(catColor('metro'),'Metro',I.metro[0],I.metro[1]):'',
    I.co?one('#111827','Big company',I.co[0],I.co[1]):'',
    I.orr?one(catColor('orr'),'ORR exit',I.orr[0],I.orr[1]):'',
    ro?one('#f97316','Main road',ro.main.name,ro.onMain?0.001:ro.mainKm):'',
    many(catColor('hospital'),'Nearest hospitals',I.H,4),many(catColor('school'),'Nearest schools',I.S,4),many(catColor('park'),'Nearest parks',I.P,3)].join('');
  const all=(lab,L)=>L&&L.length?`<div class="lc-all"><b>${lab}</b> ${L.map(([nm,d])=>`${esc(nm)} <span>${kmTxt(d)}</span>`).join(' · ')}</div>`:'';
  return `<div class="lcard">${head}<div class="lc-src">By road · ${SRC_TXT[I.s]}</div><div class="lc-g">${road}</div>
    <details class="lc-more"><summary>Every hospital, school and park measured for this property</summary>${all('Hospitals',I.H)}${all('Schools',I.S)}${all('Parks',I.P)}</details>
    <details class="lc-more"><summary>Other places nearby (straight line, OpenStreetMap)</summary><div class="lc-g">${tiles}</div></details>
    <p class="nbsrc">Distances are by road (${SRC_TXT[I.s]}); bars run from 0 to ${CARD_KM} km. ${I.s==='google'?'Google gives its fastest route at the time it was read, so a few may be longer than the shortest road.':'Mapbox routes follow real roads and one-way streets; parks were not collected for this area.'}</p></div>`;
}""")

# ---------- hexagon overview: ranges from road distances when the pins have them ----------
rep("""  const metrics=[{lab:'Infosys office',c:'#0c5f68',v:pts.map(infKm),names:'Gachibowli campus'},
    ...NEAREST_KINDS.map(K=>{""", """  const IP=pts.map(infraOf).filter(Boolean);
  const road=IP.length?(()=>{const nm=f=>{const c=new Map();IP.forEach(x=>{const v=f(x);if(v&&v[0])c.set(v[0],(c.get(v[0])||0)+1)});return[...c.entries()].sort((a,b)=>b[1]-a[1]).slice(0,2).map(e=>esc(e[0])).join(', ')};
    const near=k=>x=>x[k]&&x[k].length?x[k][0]:null;
    return [{lab:'Infosys office',c:'#0c5f68',v:IP.map(x=>x.inf),names:'Gachibowli campus'},
      {lab:'Metro',c:catColor('metro'),v:IP.map(x=>x.metro&&x.metro[1]),names:nm(x=>x.metro)},
      {lab:'Big company',c:'#111827',v:IP.map(x=>x.co&&x.co[1]),names:nm(x=>x.co)},
      {lab:'ORR exit',c:catColor('orr'),v:IP.map(x=>x.orr&&x.orr[1]),names:nm(x=>x.orr)},
      {lab:'Nearest hospital',c:catColor('hospital'),v:IP.map(x=>near('H')(x)&&near('H')(x)[1]),names:nm(near('H'))},
      {lab:'Nearest school',c:catColor('school'),v:IP.map(x=>near('S')(x)&&near('S')(x)[1]),names:nm(near('S'))},
      ...(IP.some(x=>x.P&&x.P.length)?[{lab:'Nearest park',c:catColor('park'),v:IP.map(x=>near('P')(x)&&near('P')(x)[1]),names:nm(near('P'))}]:[])]})():null;
  const srcs=[...new Set(IP.map(x=>x.s))].map(s=>SRC_TXT[s]).join(' and ');
  const metrics=road||[{lab:'Infosys office',c:'#0c5f68',v:pts.map(infKm),names:'Gachibowli campus'},
    ...NEAREST_KINDS.map(K=>{""")
rep("""      return{lab:K.label,c:kindColor(K),v,names:[...c.entries()].sort((a,b)=>b[1]-a[1]).slice(0,2).map(e=>esc(e[0])).join(', ')}})];
  const ro=pts.map(r=>[r,roadOf(r)]).filter(z=>z[1]);""", """      return{lab:K.label,c:kindColor(K),v,names:[...c.entries()].sort((a,b)=>b[1]-a[1]).slice(0,2).map(e=>esc(e[0])).join(', ')}})];
  const ro=pts.map(r=>[r,roadOf(r)]).filter(z=>z[1]);""")
rep("""  <p class="nbsrc">Each bar runs from the closest listing to the farthest one; the black mark is the typical (middle) listing. Straight-line distance, except the main road (by road).</p>""",
    """  <p class="nbsrc">Each bar runs from the closest listing to the farthest one; the black mark is the typical (middle) listing. ${road?`All distances are by road (${srcs})${IP.length<pts.length?`, for the ${new Set(pts.filter(infraOf).map(r=>r.lat+','+r.lon)).size} map pins that have them`:''}.`:'Straight-line distance, except the main road (by road).'}</p>""")
rep("""  return `<h4 class="rdh">Whole hexagon at a glance</h4>${tiles}
  <h4 class="rdh">Distances: closest to farthest listing</h4>""", """  return `<h4 class="rdh">Whole hexagon at a glance</h4>${tiles}
  <h4 class="rdh">Distances${road?' by road':''}: closest to farthest listing</h4>""")

# ---------- listing table: road columns (also in the CSV download) ----------
rep("""      ...NEAREST_KINDS.map(K=>({key:'nn_'+(K.key||K.k)""", """      {key:'rd_inf',label:'Infosys (road km)',num:1,get:x=>{const I=infraOf(x.r);return I&&I.inf!=null?I.inf:null},order:x=>{const I=infraOf(x.r);return I?I.inf:null}},
      {key:'rd_h',label:'Nearest hospital (road)',get:x=>{const I=infraOf(x.r);return I&&I.H.length?`${I.H[0][0]} (${kmTxt(I.H[0][1])})`:null},order:x=>{const I=infraOf(x.r);return I&&I.H.length?I.H[0][1]:null}},
      {key:'rd_s',label:'Nearest school (road)',get:x=>{const I=infraOf(x.r);return I&&I.S.length?`${I.S[0][0]} (${kmTxt(I.S[0][1])})`:null},order:x=>{const I=infraOf(x.r);return I&&I.S.length?I.S[0][1]:null}},
      {key:'rd_p',label:'Nearest park (road)',get:x=>{const I=infraOf(x.r);return I&&I.P.length?`${I.P[0][0]} (${kmTxt(I.P[0][1])})`:null},order:x=>{const I=infraOf(x.r);return I&&I.P.length?I.P[0][1]:null}},
      {key:'rd_src',label:'Road distances from',get:x=>{const I=infraOf(x.r);return I?SRC_TXT[I.s]:null}},
      ...NEAREST_KINDS.map(K=>({key:'nn_'+(K.key||K.k)""")

# ---------- open with Gachibowli, Kokapet and Narsingi ----------
rep("want=q==null?'Gachibowli,Nanakramguda,Khajaguda':", "want=q==null?'Gachibowli,Kokapet,Narsingi':")

# ---------- styles ----------
rep(".kbar{", """.lc-src{font-size:11.5px;font-weight:700;color:#0c5f68;margin:-2px 0 6px}
.lc-list .lc-row{display:flex;justify-content:space-between;gap:8px;font-size:12px;line-height:1.35;padding:1px 0}.lc-list .lc-row span{overflow:hidden;text-overflow:ellipsis}.lc-list .lc-row.first b{font-size:15px}
.lc-more{margin-top:8px;font-size:12px}.lc-more summary{cursor:pointer;font-weight:600;color:var(--muted)}.lc-all{margin:4px 0;line-height:1.5}.lc-all span{color:var(--muted)}
.kbar{""")
open(f, 'w', encoding='utf-8').write(t); print('patched')

# ---------- build script: fill __INFRA__ ----------
i = os.path.join(HERE, 'inject.py'); s = open(i, encoding='utf-8').read()
if '__INFRA__' not in s:
    s = s.replace(".replace('__HOT__', '[]')", ".replace('__HOT__', '[]')\n     .replace('__INFRA__', open(here('data', 'infra.json'), encoding='utf-8').read().replace('</', '<\\\\/'))")
    open(i, 'w', encoding='utf-8').write(s); print('inject.py updated')
