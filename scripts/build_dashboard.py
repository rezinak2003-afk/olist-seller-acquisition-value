"""Build an interactive browser dashboard driven by the seller mart JSON."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"
OUT = ROOT/"dashboard"/"index.html"


def main():
    seller = pd.read_csv(DATA/"seller_90d_value.csv")
    funnel = pd.read_csv(DATA/"acquisition_funnel.csv")
    tests = pd.read_csv(DATA/"pairwise_comparisons.csv")
    validation = pd.read_csv(DATA/"validation_summary.csv").set_index("check")
    seller_json = seller.to_json(orient="records", date_format="iso")
    funnel_json = funnel.to_json(orient="records")
    test_json = tests.to_json(orient="records")
    data_end = str(validation.loc["data_end", "value"])
    min_daily = int(validation.loc["min_daily_orders_rule", "value"])
    plotly_js = get_plotlyjs()
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Olist Seller Acquisition &amp; 90-Day Marketplace Value</title>
<style>
:root{{--ink:#1f2937;--muted:#64748b;--line:#e2e8f0;--bg:#f3f6fa;--navy:#17365d;--teal:#0f766e;--warn:#8a5b00}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--ink)}}
header{{background:linear-gradient(120deg,#17365d,#274c77);color:white;padding:30px max(22px,calc((100vw - 1440px)/2)) 26px}}header h1{{font-size:27px;margin:0 0 7px}}header p{{margin:0;color:#dce7f2;font-size:13px}}
main{{max-width:1440px;margin:0 auto;padding:20px 22px 42px}}.controls,.card,.panel{{background:white;border:1px solid var(--line);border-radius:11px;box-shadow:0 2px 8px rgba(15,23,42,.035)}}
.controls{{padding:14px 16px;margin-bottom:14px;display:grid;grid-template-columns:2fr 1.3fr 1fr;gap:14px;align-items:end}}
label{{display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:6px}}select,input{{font:inherit;border:1px solid #cbd5e1;border-radius:7px;padding:8px 10px;background:white;color:var(--ink);width:100%}}select[multiple]{{height:108px}}
.hint{{font-size:11px;color:var(--muted);margin-top:5px}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 16px}}.card{{padding:15px 17px;min-height:102px}}
.card-label{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.035em}}.card-value{{font-size:25px;font-weight:750;color:var(--navy);padding:7px 0 3px}}.card-note{{font-size:11px;color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:14px}}.panel{{padding:10px 12px;overflow:hidden}}.full{{margin-bottom:14px}}
.section-title{{margin:22px 0 9px;font-size:18px;color:var(--navy)}}.note{{background:#fff8e7;border:1px solid #f0dfb6;border-radius:9px;padding:12px 15px;line-height:1.55;font-size:12px;margin:12px 0 16px}}
.table-wrap{{overflow:auto;max-width:100%}}table{{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}}th{{background:#eaf1f8;color:#20364f;text-align:left;padding:9px 8px;position:sticky;top:0}}td{{border-bottom:1px solid #edf1f5;padding:8px}}tr:hover td{{background:#f8fafc}}
.small{{color:var(--muted);font-size:11px}}.insufficient{{color:var(--warn);font-weight:700}}footer{{font-size:11px;color:var(--muted);padding-top:15px;border-top:1px solid var(--line);line-height:1.6;margin-top:20px}}
@media(max-width:900px){{.controls{{grid-template-columns:1fr}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.grid{{grid-template-columns:1fr}}}}
@media(max-width:520px){{main{{padding:12px}}.cards{{grid-template-columns:1fr 1fr}}.card-value{{font-size:20px}}header h1{{font-size:21px}}}}
</style></head><body>
<header><h1>Seller Acquisition → 90-Day Marketplace Value</h1><p>Olist Marketing Funnel + Brazilian E-Commerce | Recalculated from the committed seller mart | maturity boundary: {data_end} (exclusive)</p></header>
<main>
<section class="controls">
 <div><label for="origins">Recorded origin (multi-select)</label><select id="origins" multiple></select><div class="hint">Use Ctrl/Cmd to select multiple origins. All origins are selected initially.</div></div>
 <div><label for="definition">Activation definition</label><select id="definition"><option value="purchase">Purchase-window delivered</option><option value="strict">Purchase and delivery within 90 days (strict)</option></select><div class="hint">Switches activation numerator, rate and delivered GMV basis.</div></div>
 <div><label for="minN">Minimum linked mature sellers (n; floor 20)</label><input id="minN" type="number" min="20" max="500" step="1" value="20"><div class="hint">Groups with n<20 are always suppressed; set a higher threshold to be more selective.</div></div>
</section>
<section id="cards" class="cards"></section>
<div class="note"><b>Coverage before value:</b> seller-ID linkage is incomplete. Marketplace outcomes for unlinked mature deals are unobserved, not zero. The purchase-window definition assigns transactions by purchase date even when delivery occurs later; the strict definition requires both timestamps within the window. No channel spend is supplied, and origin is observational.</div>
<div class="grid"><section class="panel"><div id="activationChart"></div></section><section class="panel"><div id="gmvChart"></div></section></div>
<section class="panel full"><div id="leadChart"></div></section>
<h2 class="section-title">Channel scorecard — denominators and small groups visible</h2>
<section class="panel table-wrap"><table><thead><tr><th>Origin</th><th>Mature deals</th><th>Linked n</th><th>Unlinked</th><th>Linkage %</th><th>Activated n</th><th>Activation % (95% Wilson CI)</th><th>Median GMV (BRL)</th><th>Data status</th></tr></thead><tbody id="scorecard"></tbody></table></section>
<h2 class="section-title">Primary origin comparison</h2>
<section class="panel table-wrap"><table><thead><tr><th>Definition</th><th>Paid search</th><th>Organic search</th><th>Difference (pp)</th><th>Newcombe 95% CI (pp)</th><th>Fisher p</th><th>Holm-adjusted p</th></tr></thead><tbody id="tests"></tbody></table><p class="small">Pairwise comparisons use Fisher's exact test and Holm adjustment across all eligible origin pairs within each definition. The primary contrast is paid search vs organic search.</p></section>
<footer><b>Cutoff:</b> day after the last calendar date with at least {min_daily} order purchases; windows are [won_date, won_date + 90 days). <b>GMV:</b> item price in BRL, not seller profit or platform revenue. <b>Coverage:</b> a seller is linked when its seller_id appears in any order-item row; an unlinked seller's outcome remains unknown. <b>Data licensing:</b> confirm the current publisher terms before redistributing source data.</footer>
</main>
<script>{plotly_js}</script>
<script id="sellerData" type="application/json">{seller_json}</script>
<script id="funnelData" type="application/json">{funnel_json}</script>
<script id="testData" type="application/json">{test_json}</script>
<script>
const seller = JSON.parse(document.getElementById('sellerData').textContent);
const funnel = JSON.parse(document.getElementById('funnelData').textContent);
const tests = JSON.parse(document.getElementById('testData').textContent);
const originNames = [...new Set(seller.map(r => r.origin || '(missing)'))].sort();
const originSelect = document.getElementById('origins');
originNames.forEach(o => {{ const op=document.createElement('option'); op.value=o; op.textContent=o; op.selected=true; originSelect.appendChild(op); }});
const fmtNum = n => Number(n||0).toLocaleString('en-US');
const fmtPct = n => Number.isFinite(n) ? `${{n.toFixed(2)}}%` : '—';
const fmtBRL = n => Number.isFinite(n) ? 'R$'+n.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}}) : '—';
function wilson(x,n) {{ if(!n) return [NaN,NaN]; const z=1.95996398454,p=x/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt((p*(1-p)+z*z/(4*n))/n)/d; return [Math.max(0,c-h),Math.min(1,c+h)]; }}
function selectedOrigins() {{ return [...originSelect.selectedOptions].map(o=>o.value); }}
function getState() {{ return {{origins:selectedOrigins(),definition:document.getElementById('definition').value,minN:Math.max(20,Number(document.getElementById('minN').value)||20)}}; }}
function compute() {{
 const st=getState();
 const mature=seller.filter(r=>Boolean(r.mature_90d) && st.origins.includes(r.origin));
 const groups=st.origins.map(origin=>{{
  const all=mature.filter(r=>r.origin===origin), linked=all.filter(r=>Boolean(r.seller_linked_to_order_items));
  const col=st.definition==='purchase'?'activated_90d':'activated_delivered_within_90d';
  const gm=st.definition==='purchase'?'gmv_90d_delivered_only':'gmv_90d_delivered_within_90d';
  const success=linked.filter(r=>Number(r[col])===1).length;
  const vals=linked.map(r=>Number(r[gm])).filter(Number.isFinite);
  const sorted=[...vals].sort((a,b)=>a-b); const median=sorted.length ? (sorted.length%2?sorted[(sorted.length-1)/2]:(sorted[sorted.length/2-1]+sorted[sorted.length/2])/2) : NaN;
  const mean=vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:NaN;
  const ci=wilson(success,linked.length);
  return {{origin,mature:all.length,linked:linked.length,unlinked:all.length-linked.length,success,
    activation:linked.length?success/linked.length*100:NaN,low:ci[0]*100,high:ci[1]*100,
    linkage:all.length?linked.length/all.length*100:NaN,median,mean,total:vals.reduce((a,b)=>a+b,0),eligible:linked.length>=st.minN}};
 }});
 const eligible=groups.filter(g=>g.eligible);
 const sums=eligible.reduce((a,g)=>({{mature:a.mature+g.mature,linked:a.linked+g.linked,unlinked:a.unlinked+g.unlinked,success:a.success+g.success,gmv:a.gmv+g.total}}),{{mature:0,linked:0,unlinked:0,success:0,gmv:0}});
 const activation=sums.linked?sums.success/sums.linked*100:NaN;
 renderCards(sums,activation,eligible.length,st);
 renderCharts(eligible,st);
 renderScorecard(groups,st);
 renderTests(st);
}}
function renderCards(s,a,n,st) {{
 const items=[
  ['Mature deals',fmtNum(s.mature),`${{n}} origin groups meet n ≥ ${{st.minN}}`],
  ['Linked mature deals',fmtNum(s.linked),`${{fmtNum(s.unlinked)}} unlinked / unobserved`],
  ['Observed activation',fmtNum(s.success),st.definition==='purchase'?'Delivered status, purchase in window':'Purchase and delivery in window'],
  ['Activation rate',fmtPct(a),`${{fmtNum(s.success)}} / ${{fmtNum(s.linked)}} linked sellers`],
  ['Linkage rate',fmtPct(s.mature?100*s.linked/s.mature:NaN),'Linked / all mature deals in eligible groups'],
  ['Delivered GMV',fmtBRL(s.gmv),'Filtered definition and origin selection']
 ];
 const root=document.getElementById('cards'); root.replaceChildren();
 items.forEach(([label,value,note])=>{{const d=document.createElement('div');d.className='card';const l=document.createElement('div');l.className='card-label';l.textContent=label;const v=document.createElement('div');v.className='card-value';v.textContent=value;const p=document.createElement('div');p.className='card-note';p.textContent=note;d.append(l,v,p);root.appendChild(d);}});
}}
function renderCharts(groups,st) {{
 const labels=groups.map(g=>`${{g.origin}} (n=${{g.linked}})`);
 Plotly.react('activationChart',[{{type:'bar',x:labels,y:groups.map(g=>g.activation),marker:{{color:'#0f766e'}},
   error_y:{{type:'data',symmetric:false,array:groups.map(g=>g.high-g.activation),arrayminus:groups.map(g=>g.activation-g.low)}},
   hovertemplate:'%{{x}}<br>Activation: %{{y:.1f}}%<extra></extra>'}}],{{title:'Activation by origin · 95% Wilson intervals',yaxis:{{title:'Rate (%)',range:[0,100]}},margin:{{t:55,b:95,l:55,r:15}},template:'plotly_white'}},{{responsive:true,displaylogo:false}});
 Plotly.react('gmvChart',[{{type:'bar',x:labels,y:groups.map(g=>g.median),name:'Median',marker:{{color:'#6096ba'}},hovertemplate:'%{{x}}<br>Median GMV: R$%{{y:,.2f}}<extra></extra>'}},
  {{type:'scatter',x:labels,y:groups.map(g=>g.mean),name:'Mean',mode:'markers',marker:{{color:'#e76f51',size:9}},hovertemplate:'%{{x}}<br>Mean GMV: R$%{{y:,.2f}}<extra></extra>'}}],
  {{title:'Delivered item-price GMV by origin',barmode:'group',yaxis:{{title:'BRL'}},margin:{{t:55,b:95,l:65,r:15}},template:'plotly_white',legend:{{orientation:'h',y:-.3}}}},{{responsive:true,displaylogo:false}});
 const fs=[...funnel].sort((a,b)=>Number(b.qualified_leads)-Number(a.qualified_leads));
 Plotly.react('leadChart',[{{type:'bar',x:fs.map(r=>r.qualified_leads),y:fs.map(r=>r.origin),orientation:'h',marker:{{color:'#274c77'}},
  hovertemplate:'%{{y}}<br>Qualified leads: %{{x:,}}<extra></extra>'}}],{{title:'Qualified leads by recorded origin',xaxis:{{title:'Distinct qualified leads'}},margin:{{t:50,l:125,r:20,b:45}},template:'plotly_white'}},{{responsive:true,displaylogo:false}});
}}
function renderScorecard(groups,st) {{
 const body=document.getElementById('scorecard');body.replaceChildren();
 groups.forEach(g=>{{const tr=document.createElement('tr');const status=g.eligible?'sufficient n':'insufficient data';const values=[g.origin,fmtNum(g.mature),fmtNum(g.linked),fmtNum(g.unlinked),fmtPct(g.linkage),fmtNum(g.success),g.eligible?`${{fmtPct(g.activation)}} (${{g.low.toFixed(1)}}–${{g.high.toFixed(1)}}%)`:'—',fmtBRL(g.median),status];
 values.forEach((v,i)=>{{const td=document.createElement('td');td.textContent=v;if(i===8&&!g.eligible)td.className='insufficient';tr.appendChild(td);}});body.appendChild(tr);}});
}}
function renderTests(st) {{
 const body=document.getElementById('tests');body.replaceChildren();
 const def=st.definition==='purchase'?'purchase_window':'strict_within_90d';
 const r=tests.find(x=>x.definition===def&&x.primary_comparison===true);
 if(!r) {{const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=7;td.textContent='Primary contrast not available under current test threshold.';tr.appendChild(td);body.appendChild(tr);return;}}
 const vals=[st.definition==='purchase'?'Purchase-window':'Strict',`${{Number(r.successes_a)}}/${{Number(r.n_a)}} · ${{Number(r.rate_a_pct).toFixed(1)}}%`,`${{Number(r.successes_b)}}/${{Number(r.n_b)}} · ${{Number(r.rate_b_pct).toFixed(1)}}%`,`${{Number(r.risk_difference_a_minus_b_pp).toFixed(1)}}`,`${{Number(r.risk_difference_ci_95_low_pp).toFixed(1)}} to ${{Number(r.risk_difference_ci_95_high_pp).toFixed(1)}}`,Number(r.p_value).toFixed(4),Number(r.p_value_holm_adjusted).toFixed(4)];
 const tr=document.createElement('tr');vals.forEach(v=>{{const td=document.createElement('td');td.textContent=v;tr.appendChild(td);}});body.appendChild(tr);
}}
['change','input'].forEach(evt=>{{originSelect.addEventListener(evt,compute);document.getElementById('definition').addEventListener(evt,compute);document.getElementById('minN').addEventListener(evt,compute);}});
compute();
</script></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Interactive dashboard written: {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
