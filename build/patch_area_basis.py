"""Show each listing's area basis (super built-up, built-up, carpet ...) next to its size everywhere on the site."""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'site_template.html'); shutil.copy(f, f + '.bak_basis')
t = open(f, encoding='utf-8').read()
def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a[:80], t.count(a)); t = t.replace(a, b)

rep("const SRC_TXT={", r"""/* the size the portal quoted: super built-up / built-up / carpet / plot, or not stated */
function basisOf(r){if(r._basis!==undefined)return r._basis;const raw=r.raw||{};let v='';for(const k in raw){if(/^area\s*basis$/i.test(k.trim())){v=String(raw[k]||'');break}}
  const s=v.toLowerCase();r._basis=/super|saleable|sbua/.test(s)?'super built-up':/carpet/.test(s)?'carpet':/built/.test(s)?'built-up':/plot|sq\.? ?yd|yard/.test(s)?'plot':'';return r._basis}
const basisTxt=r=>basisOf(r)||'basis not stated';
const SRC_TXT={""")
# card header
rep("""r.sqft?inr(r.sqft)+' sqft':''].filter(Boolean).map(s=>`<span>${esc(s)}</span>`).join('')}${r.price?`<span class="lc-p">""",
    """r.sqft?`${inr(r.sqft)} sqft (${basisTxt(r)})`:''].filter(Boolean).map(s=>`<span>${esc(s)}</span>`).join('')}${r.price?`<span class="lc-p">""")
# hexagon size tile: say which basis the sizes are on
rep("""<small>${bh.length?bh.join(', ')+' BHK':''}</small></div></div>`;""",
    """<small>${bh.length?bh.join(', ')+' BHK':''}</small><small>${(()=>{const c={};rows.forEach(r=>{const b=basisTxt(r);c[b]=(c[b]||0)+1});return Object.entries(c).sort((a,b)=>b[1]-a[1]).map(([b,n])=>`${n} ${b}`).join(' · ')})()}</small></div></div>`;""")
# dot tooltip
rep("""${money(r.price)} · ${r.bhk??'?'} BHK · ${inr(r.sqft)} sqft · ${esc(r.type||'')}""",
    """${money(r.price)} · ${r.bhk??'?'} BHK · ${inr(r.sqft)} sqft <small>(${esc(basisTxt(r))})</small> · ${esc(r.type||'')}""")
# table: a column right after the size
rep("""    {key:'sqft',label:'Area (sqft)',num:1,get:x=>x.r.sqft?inr(x.r.sqft):null,order:x=>x.r.sqft},""",
    """    {key:'sqft',label:'Area (sqft)',num:1,get:x=>x.r.sqft?inr(x.r.sqft):null,order:x=>x.r.sqft},
    {key:'basis',label:'Area basis',get:x=>basisOf(x.r)||'not stated'},""")
open(f, 'w', encoding='utf-8').write(t); print('patched')
