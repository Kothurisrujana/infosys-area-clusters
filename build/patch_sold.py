"""Keep sold listings (instead of dropping them), show them on the map as SOLD markers, and compare each sold price
with what sellers ask today in the same project and BHK."""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'site_template.html'); shutil.copy(f, f + '.bak_sold')
t = open(f, encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a[:80], t.count(a)); t = t.replace(a, b)

# ---------- parsing: keep sold rows aside ----------
rep("""  raw.forEach(r=>{
    if(cStatus!=null&&isSold(r[cStatus])){sold++;return}""", """  const soldRows=[];
  raw.forEach(r=>{
    const isS=cStatus!=null&&isSold(r[cStatus]);""")
rep("""    if(!(price>0)){skipped++;return}
    const sqft=""", """    if(!(price>0)){if(isS)sold++;else skipped++;return}
    const sqft=""")
rep("""    rows.push({name:String(cName!=null""", """    (isS?(sold++,soldRows):rows).push({name:String(cName!=null""")
rep("  return{rows,skipped,columns,nameCol,sold,old};", "  return{rows,soldRows,skipped,columns,nameCol,sold,old};")
rep("const x=q[i],d={file:x.file,rows:x.rows,skipped:x.skipped,", "const x=q[i],d={file:x.file,rows:x.rows,soldRows:x.soldRows||[],skipped:x.skipped,")
rep("      d.rows=[...old.rows,...x.rows.filter(r=>!seen.has(key(r)))];", "      d.rows=[...old.rows,...x.rows.filter(r=>!seen.has(key(r)))];d.soldRows=[...(old.soldRows||[]),...(x.soldRows||[])];")

# ---------- comparison helpers + map markers ----------
rep("const projectDots=L.layerGroup().addTo(map),DOTS_FROM_ZOOM=14;", r"""const projectDots=L.layerGroup().addTo(map),DOTS_FROM_ZOOM=14;
/* ---------- sold listings: what they sold for against what sellers ask now ---------- */
const soldLayer=L.layerGroup().addTo(map);
const projKey=n=>String(n||'').toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,8);
function soldType(r){const s=String(r.status||'').toLowerCase();return /secondary/.test(s)?'resale':/primary|landlord/.test(s)?'first sale (builder / landowner)':'sold'}
/* today's asking prices in the same project: same BHK first, else any BHK */
function askingFor(sr,area){const d=state.data[area]||state.loaded[area];if(!d)return null;const k=projKey(sr.name);
  const same=d.rows.filter(r=>projKey(r.name)===k),sb=same.filter(r=>r.bhk===sr.bhk),use=sb.length?sb:same;if(!use.length)return null;
  const med=v=>{v=v.filter(x=>x>0).sort((a,b)=>a-b);return v.length?(v.length%2?v[v.length>>1]:(v[v.length/2-1]+v[v.length/2])/2):null};
  const pr=use.map(r=>r.price).filter(x=>x>0);
  return{n:use.length,sameBhk:!!sb.length,medPrice:med(pr),lo:Math.min(...pr),hi:Math.max(...pr),medPpsf:med(use.map(r=>r.ppsf))}}
const pctTxt=(a,b)=>a&&b?`${b>=a?'+':''}${Math.round((b-a)/a*100)}%`:'–';
function soldTip(sr,area){const A=askingFor(sr,area);
  return `<b>${esc(sr.name)}</b> · <span style="color:#b91c1c;font-weight:700">SOLD</span> (${esc(soldType(sr))})<br>Sold at <b>${money(sr.price)}</b>${sr.ppsf?` · ₹${inr(sr.ppsf)}/sqft`:''}<br>${sr.bhk??'?'} BHK · ${sr.sqft?inr(sr.sqft)+' sqft':'size not given'} (${esc(basisTxt(sr))})`+
    (A?`<br>Asking now in this project${A.sameBhk?` (${sr.bhk} BHK)`:''}: <b>${money(A.medPrice)}</b> typical${A.n>1?`, ${money(A.lo)}–${money(A.hi)}`:''} from ${A.n} listing${A.n>1?'s':''}${A.medPpsf&&sr.ppsf?`<br>Asking ₹/sqft is <b>${pctTxt(sr.ppsf,A.medPpsf)}</b> vs this sale`:''}`:'<br>No listing for sale now in this project')}
function drawSold(){soldLayer.clearLayers();if(state.view!=='grid')return;const z=map.getZoom(),s=z>=15?16:z>=13?13:11;
  Object.entries(state.data).forEach(([a,d])=>(d.soldRows||[]).forEach((sr,i)=>{if(sr.lat==null)return;
    const n=(d.soldRows.slice(0,i).filter(x=>x.lat===sr.lat&&x.lon===sr.lon).length),ang=n*2.39996,rad=n?9*Math.sqrt(n):0;
    const la=sr.lat+rad*Math.cos(ang)/111320,lo=sr.lon+rad*Math.sin(ang)/(111320*Math.cos(sr.lat*Math.PI/180));
    L.marker([la,lo],{pane:'dots',zIndexOffset:900,keyboard:false,icon:L.divIcon({className:'psymw',iconSize:[s,s],html:`<svg width="${s}" height="${s}" viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" transform="rotate(45 8 8)" fill="#111827" stroke="#fff" stroke-width="1.6"/><path d="M5.6 8.2 7.3 9.9 10.6 6.3" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>`})})
      .bindTooltip(soldTip(sr,a),{direction:'top',offset:[0,-6]}).bindPopup(()=>soldTip(sr,a)+`<br>${srcLinks(sr).map(l=>`<a href="${esc(l.u)}" target="_blank" rel="noopener">${esc(l.site)} ↗</a>`).join(' ')}`,{maxWidth:320}).addTo(soldLayer)}));
  const box=$('mapKeys');let k=document.getElementById('soldKey');const any=Object.values(state.data).some(d=>(d.soldRows||[]).length);
  if(!k&&box){k=document.createElement('div');k.id='soldKey';k.className='blegend';box.appendChild(k)}
  if(k){k.hidden=!any;k.innerHTML=`<div class="bl-t">Sold listings</div><div><svg width="13" height="13" viewBox="0 0 16 16" style="vertical-align:-2px"><rect x="2.5" y="2.5" width="11" height="11" transform="rotate(45 8 8)" fill="#111827" stroke="#fff" stroke-width="1.6"/><path d="M5.6 8.2 7.3 9.9 10.6 6.3" stroke="#fff" stroke-width="1.6" fill="none"/></svg> Sold (price it sold for). Hover for today's asking price in the same project.</div>`}}
map.on('zoomend',()=>drawSold());
/* section: every sold listing next to today's asking prices */
function soldVsAskHTML(){
  const L_=[];Object.entries(state.data).forEach(([a,d])=>(d.soldRows||[]).forEach(sr=>L_.push([a,sr])));if(!L_.length)return'';
  L_.sort((x,y)=>x[1].name.localeCompare(y[1].name)||x[1].price-y[1].price);
  const rows=L_.map(([a,sr])=>{const A=askingFor(sr,a);const d=A&&A.medPpsf&&sr.ppsf?Math.round((A.medPpsf-sr.ppsf)/sr.ppsf*100):null;
    return `<tr><td>${esc(sr.name)}<br><small>${esc(a)}</small></td><td class="n">${sr.bhk??'–'}</td><td class="n">${sr.sqft?inr(sr.sqft):'–'}<br><small>${esc(basisTxt(sr))}</small></td><td>${esc(soldType(sr))}</td>
      <td class="n"><b>${money(sr.price)}</b>${sr.ppsf?`<br><small>₹${inr(sr.ppsf)}/sqft</small>`:''}</td>
      <td class="n">${A?`<b>${money(A.medPrice)}</b><br><small>${A.n>1?`${money(A.lo)}–${money(A.hi)} · `:''}${A.n} listing${A.n>1?'s':''}${A.sameBhk?'':', any BHK'}</small>`:'<small>none for sale now</small>'}</td>
      <td class="n">${A&&A.medPpsf?`₹${inr(Math.round(A.medPpsf))}`:'–'}</td>
      <td class="n">${d==null?'–':`<b style="color:${d>=0?'#15803d':'#b91c1c'}">${d>=0?'+':''}${d}%</b>`}</td></tr>`}).join('');
  return `<section class="card"><h2>Sold listings: sold price against today's asking price</h2>
  <p class="hint">${L_.length} listing${L_.length>1?'s are':' is'} marked sold in your files. Asking price = the typical price of listings for sale now in the same project (same BHK where there is one). The last column compares price per sqft; sizes may be on different bases (super built-up, built-up, carpet), so treat small gaps with care.</p>
  <div class="tw"><table><thead><tr><th>Project</th><th class="n">BHK</th><th class="n">Size (sqft)</th><th>Sale</th><th class="n">Sold for</th><th class="n">Asking now (typical)</th><th class="n">Asking ₹/sqft</th><th class="n">Asking vs sold (₹/sqft)</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}""")
# draw markers whenever the map is redrawn, and put the section near the top of the analysis
rep("  let h=oneAreaHTML()+vcHTML()+", "  let h=oneAreaHTML()+soldVsAskHTML()+vcHTML()+")
i = t.index("function renderAll(){"); j = t.index("drawProjectDots();", i)
t = t[:j] + "drawProjectDots();drawSold();" + t[j + len("drawProjectDots();"):]
open(f, 'w', encoding='utf-8').write(t); print('patched')
