"""Read-only standard-library checks of captured layout; does not drive a browser."""
from pathlib import Path
import json,hashlib
p=Path(__file__).resolve().parent
manifest=json.loads((p/'SHA256SUMS.json').read_text())
for f,h in manifest.items():assert hashlib.sha256((p/f).read_bytes()).hexdigest()==h,f
before=json.loads((p/'browser/top-layout.json').read_text());after=json.loads((p/'browser/bottom-layout.json').read_text())
assert before['viewport']==after['viewport']=={'width':575,'height':823}
assert before['scrollTop']==0 and after['scrollTop']>0
assert abs(after['scrollTop']-(after['scrollHeight']-after['clientHeight']))<=1
assert before['pageY']==after['pageY']
assert before['chart']==after['chart']
assert after['documentWidth']==575
c=after['chart'];v=after['viewport'];heads=after['headings']
assert len(heads)==5 and c['top']>=0 and c['bottom']<=v['height']
assert [h['text'] for h in heads[1:]]==['2026-10-0808:45:00','2026-10-0808:50:00','2026-10-0808:55:00','2026-10-0809:00:00']
for h in heads:
 assert c['top']<=h['top']<h['bottom']<=c['bottom'] and h['left']>=c['left'] and h['right']<=c['right']
for g in after['groups']:
 assert max(h['bottom'] for h in heads)<=g['top']<g['bottom']<=c['bottom']
assert {g['name'] for g in after['groups']}=={'Fluid records','Perfusion observations'}
assert len(after['sources'])==9
for s in after['sources']:
 assert max(h['bottom'] for h in heads)<=s['top']<s['bottom']<=c['bottom']
 assert c['left']<=s['left']<s['right']<=c['right']
dom=(p/'browser/bottom-dom.txt').read_text()
assert 'New execution disabled in this demo' in dom
for text in ['285 mL','110 mL','-50 mL','40 mL','45 mL','2.1 mmol/L','2.0 mmol/L','2.0 s','Interval 08:45:00 → 09:00:00 UTC']:assert text in dom,text
print(json.dumps({'result':'PASS','manifest_entries':len(manifest),'viewport':v,'internal_scroll_before':before['scrollTop'],'internal_scroll_after':after['scrollTop'],'outer_page_stationary':True,'time_headings_visible':4,'fluid_and_perfusion_groups_fully_visible':True,'all_nine_source_controls_fully_visible':True,'execution_disabled_banner':True,'scope':'Implementation-captured browser layout and screenshots; not independent Director live execution or general accessibility certification'},indent=2))
