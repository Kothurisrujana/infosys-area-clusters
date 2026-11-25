"""Short note on upcoming (future) infrastructure in Kokapet / Neopolis, with approximate map markers.
Only shown while Kokapet is on the map. Facts checked against the news sources listed in FUTURE (Nov 2026)."""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'site_template.html'); shutil.copy(f, f + '.bak_future')
t = open(f, encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a[:80], t.count(a)); t = t.replace(a, b)

rep("const soldLayer=L.layerGroup().addTo(map)", r"""/* ---------- upcoming infrastructure (future projects) near Kokapet ---------- */
const FUTURE=[
 {k:'water',icon:'💧',title:'Kokapet–Neopolis water supply scheme',where:'Neopolis layout, Kokapet',lat:17.4105,lon:78.3172,approx:'layout centre (exact site not published)',
  what:'₹298 crore trunk main and pumping station to cut dependence on private water tankers; reviewed with the Godavari Phase II & III project (₹7,360 crore)',
  when:'Targeted to be completed by 2027',by:'Telangana govt / HMWSSB',
  src:[['Siasat (₹7,360 cr Godavari approval)','https://www.siasat.com/govt-sanctions-rs-7360-crore-for-hyderabad-drinking-water-supply-project-3477753/'],['Civic Mail (Neopolis water review)','https://hyderabadmail.com/ashok-reddy-reviews-godavari-neopolis-water-projects/']]},
 {k:'water',icon:'🛢',title:'Master Balancing Reservoir, Khanapur',where:'Khanapur, next to Kokapet Neopolis layout',lat:17.39426,lon:78.30199,approx:'Khanapur village centre (exact plot not published)',
  what:'3.95 acres allotted for a 22.5 ML master balancing reservoir, 2 elevated service reservoirs, chlorination room and maintenance unit; gravity supply to Neopolis and Kokapet',
  when:'Land allotted 28 Feb 2026; no completion year announced',by:'Telangana govt (land) / HMWSSB',
  src:[['Telangana Today, 28 Feb 2026','https://telanganatoday.com/telangana-govt-allots-3-95-acres-to-hmwssb-for-kokapet-neopolis-water-infrastructure'],['NewsMeter','https://newsmeter.in/hyderabad/hyderabad-govt-allots-395-acres-in-neopolis-for-godavari-water-project-gravity-supply-to-old-city-mehdipatnam-763792']]},
 {k:'water',icon:'♻',title:'“Green Water” filling station',where:'Kokapet',lat:17.39581,lon:78.32403,approx:'Kokapet village centre (site not chosen yet)',
  what:'Treated wastewater for construction and landscaping, to save drinking water; tanker filling with online quality checks',
  when:'Planning stage (feasibility study ordered Oct 2026); no year announced',by:'HMWSSB',
  src:[['Telangana Today, 22 Oct 2026','https://telanganatoday.com/hmwssb-plans-green-water-filling-station-in-kokapet']]},
 {k:'power',icon:'⚡',title:'400/220/132/33 kV GIS substation',where:'Kokapet (Neopolis) layout, beside the HMWSSB pump house',lat:17.4085,lon:78.3205,approx:'inside the layout (exact plot not published)',
  what:'Gas-insulated substation on 5.20 acres handed over by HMDA, with underground cabling in the layout, for the coming high-rise load',
  when:'Approved by CEA on 16 Feb 2026; no completion year announced',by:'TGTRANSCO (land from HMDA)',
  src:[['TGTRANSCO order (PDF)','https://tgtransco.com/toos_upload/too/ms/TOO_-_I.pdf'],['Telangana Today (Neopolis layout plans)','https://telanganatoday.com/hyderabad-neopolis-layout-in-kokapet-all-set-to-become-role-model-for-other-projects']]}];
const futureLayer=L.layerGroup().addTo(map);
const futureOn=()=>!!(state.data&&state.data.Kokapet);
function drawFuture(){futureLayer.clearLayers();if(!futureOn())return;
  FUTURE.forEach(p=>L.marker([p.lat,p.lon],{pane:'places',zIndexOffset:700,keyboard:false,icon:L.divIcon({className:'psymw',iconSize:[22,22],html:`<div class="fut ${p.k}">${p.icon}</div>`})})
    .bindTooltip(`<b>${esc(p.title)}</b> <small>(future project)</small><br>${esc(p.where)}<br>${esc(p.when)}`,{direction:'top',offset:[0,-8]})
    .bindPopup(`<div class="srcpop"><b>${esc(p.title)}</b> <small>· future project</small><div>${esc(p.what)}</div><div><b>Where:</b> ${esc(p.where)} <small>(marker: ${esc(p.approx)})</small></div><div><b>When:</b> ${esc(p.when)}</div><div><b>By:</b> ${esc(p.by)}</div><div>${p.src.map(([n,u])=>`<a href="${u}" target="_blank" rel="noopener">${esc(n)} ↗</a>`).join(' · ')}</div></div>`,{maxWidth:330})
    .addTo(futureLayer));
  const box=$('mapKeys');let k=document.getElementById('futureKey');
  if(!k&&box){k=document.createElement('div');k.id='futureKey';k.className='blegend';box.appendChild(k)}
  if(k)k.innerHTML=`<div class="bl-t">Upcoming infrastructure (future)</div><div><span class="fut water sm">💧</span> water &nbsp; <span class="fut power sm">⚡</span> power · click a marker for year and source</div>`}
function futureHTML(){if(!futureOn())return'';
  return `<section class="card fut-card"><h2>Kokapet–Neopolis: upcoming infrastructure <small>(future projects)</small></h2>
  <ul class="fut-list">${FUTURE.map(p=>`<li><span class="fut ${p.k} sm">${p.icon}</span> <b>${esc(p.title)}</b>: ${esc(p.where)}. ${esc(p.when)}. <small>By ${esc(p.by)} · ${p.src.map(([n,u])=>`<a href="${u}" target="_blank" rel="noopener">${esc(n)}</a>`).join(', ')}</small></li>`).join('')}</ul>
  <p class="hint">These are announced or approved works, not finished. Map markers show the named area; the exact plots are not published. Checked against the news reports linked above (Nov 2026).</p></section>`}
const soldLayer=L.layerGroup().addTo(map)""")
rep("  let h=oneAreaHTML()+vcHTML()+", "  let h=oneAreaHTML()+futureHTML()+vcHTML()+")
i = t.index("function renderAll(){"); j = t.index("drawProjectDots();drawSold();", i)
t = t[:j] + "drawProjectDots();drawSold();drawFuture();" + t[j + len("drawProjectDots();drawSold();"):]
rep(".routeln{", """.fut{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:12px;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}.fut.water{background:#bae6fd}.fut.power{background:#fde68a}
.fut.sm{display:inline-grid;width:18px;height:18px;font-size:10px;vertical-align:-4px;box-shadow:none;border-width:1px}.fut-list{margin:6px 0;padding-left:4px;list-style:none;font-size:13px;line-height:1.6}
.routeln{""")
open(f, 'w', encoding='utf-8').write(t); print('patched')
