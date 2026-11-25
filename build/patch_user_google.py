"""Show the distances the user collected from Google Maps in their own Kokapet file
(ORR Connectivity km, Airport Distance km, Nearby Places) in the listing card, hexagon overview and table."""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'site_template.html'); shutil.copy(f, f + '.bak_user')
t = open(f, encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a[:80], t.count(a)); t = t.replace(a, b)

rep("const SRC_TXT={google:'Google Maps best route',mapbox:'Mapbox driving route'};", r"""const SRC_TXT={google:'Google Maps best route',mapbox:'Mapbox driving route'};
/* distances typed into the listing file itself (collected from Google Maps by the user) */
function userOf(r){const raw=r.raw||{};const get=re=>{for(const k in raw){if(re.test(k.trim()))return raw[k]}return null};
  const n=v=>{const x=parseFloat(String(v??'').replace(/[^\d.]/g,''));return isFinite(x)&&x>0?x:null};
  const orr=n(get(/^orr connectivity$/i)),air=n(get(/^airport distance$/i)),near=String(get(/^nearby places$/i)||'').split(',').map(s=>s.trim()).filter(Boolean);
  return orr||air||near.length?{orr,air,near}:null}""")

# card: the user's Google values first, in both the road and the no-road versions
rep("""  const I=infraOf(r);
  if(!I)return `<div class="lcard">${head}<div class="lc-g">${tiles}</div>""", """  const I=infraOf(r),U=userOf(r);
  const ut=U?[U.orr!=null?`<div class="lc-t"><div class="lc-l"><i style="background:${catColor('orr')}"></i>ORR connectivity</div><div class="lc-d">${kmTxt(U.orr)}</div>${kmBar(U.orr,catColor('orr'))}<div class="lc-n">your Google Maps data</div></div>`:'',
    U.air!=null?`<div class="lc-t"><div class="lc-l"><i style="background:#475569"></i>Airport (RGIA)</div><div class="lc-d">${kmTxt(U.air)}</div>${kmBar(U.air,'#475569')}<div class="lc-n">your Google Maps data</div></div>`:'',
    U.near.length?`<div class="lc-t lc-list"><div class="lc-l"><i style="background:#0c5f68"></i>Nearby places</div>${U.near.slice(0,6).map(x=>`<div class="lc-row"><span>${esc(x)}</span></div>`).join('')}<div class="lc-n"><small>from your listing file</small></div></div>`:''].join(''):'';
  if(!I)return `<div class="lcard">${head}${ut?`<div class="lc-src">Your Google Maps data</div><div class="lc-g">${ut}</div><details class="lc-more"><summary>Other places nearby (straight line, OpenStreetMap)</summary><div class="lc-g">${tiles}</div></details>`:`<div class="lc-g">${tiles}</div>`}""")
rep("""    I.orr?one(catColor('orr'),'ORR exit',I.orr[0],I.orr[1]):'',""", """    U&&U.orr!=null?'':(I.orr?one(catColor('orr'),'ORR exit',I.orr[0],I.orr[1]):''),""")
rep("""  return `<div class="lcard">${head}<div class="lc-src">By road · ${SRC_TXT[I.s]}</div><div class="lc-g">${road}</div>""",
    """  return `<div class="lcard">${head}${ut?`<div class="lc-src">Your Google Maps data</div><div class="lc-g">${ut}</div>`:''}<div class="lc-src">By road · ${SRC_TXT[I.s]}</div><div class="lc-g">${road}</div>""")

# hexagon overview: add the user's ORR and airport ranges
rep("""  const srcs=[...new Set(IP.map(x=>x.s))].map(s=>SRC_TXT[s]).join(' and ');""", """  const srcs=[...new Set(IP.map(x=>x.s))].map(s=>SRC_TXT[s]).join(' and ');
  const UP=pts.map(userOf).filter(Boolean),uORR=UP.map(x=>x.orr).filter(v=>v!=null),uAIR=UP.map(x=>x.air).filter(v=>v!=null);
  const userM=[...(uORR.length?[{lab:'ORR connectivity',c:catColor('orr'),v:uORR,names:'your Google Maps data'}]:[]),...(uAIR.length?[{lab:'Airport (RGIA)',c:'#475569',v:uAIR,names:'your Google Maps data'}]:[])];""")
rep("""  const metrics=road||[{lab:'Infosys office'""", """  const metrics0=road||[{lab:'Infosys office'""")
rep("""  const ro=pts.map(r=>[r,roadOf(r)]).filter(z=>z[1]);
  if(ro.length)metrics.push(""", """  const metrics=userM.length?[...userM,...metrics0.filter(m=>m.lab!=='ORR exit')]:metrics0;
  const ro=pts.map(r=>[r,roadOf(r)]).filter(z=>z[1]);
  if(ro.length)metrics.push(""")

# table + CSV
rep("""      {key:'rd_src',label:'Road distances from'""", """      {key:'u_orr',label:'ORR connectivity (your Google data)',num:1,get:x=>{const U=userOf(x.r);return U&&U.orr!=null?U.orr:null},order:x=>{const U=userOf(x.r);return U?U.orr:null}},
      {key:'u_air',label:'Airport (your Google data)',num:1,get:x=>{const U=userOf(x.r);return U&&U.air!=null?U.air:null},order:x=>{const U=userOf(x.r);return U?U.air:null}},
      {key:'rd_src',label:'Road distances from'""")
open(f, 'w', encoding='utf-8').write(t); print('patched')
