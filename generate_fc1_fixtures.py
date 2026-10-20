from pathlib import Path
import json,copy,sys,hashlib,uuid
root=Path.cwd();repo=root/'rf2-implementation';sys.path.insert(0,str(repo/'backend'))
from app.models.clinical.hemodynamics import CirculatoryEvent
from app.persistence.canonical import canonical_payload
base=json.loads((repo/'frontend/tests/fixtures/rf2-api.json').read_text())['urine']
def instant(raw):
 return {'timestamp_precision':'M7ExactTimestampInput/v1','recorded':{'status':'known','precision':'instant','value':raw,'lower':None,'upper':None,'uncertainty':None},'source_timestamp':raw,'clock':'unknown','clock_basis':None,'conflicting':[],'alternative_sources':[],'alignment':None}
def make(name,kind,precision='instant',uncertainty=None,alternative=None,boundary='start'):
 e=copy.deepcopy(base);e['cutoff']=json.loads((repo/'frontend/tests/fixtures/rf2-api.json').read_text())['catalog']['cutoff']['fact_watermark'];f=e['fact'];f['id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'clinrx.fc1/'+name));e['terminal_reference']['id']=f['id']
 c=e['metadata']['chart'];c.update(start='2026-10-08T08:30:00Z' if kind=='interval' else None,end='2026-10-08T08:45:00Z' if kind=='interval' else None,point='2026-10-08T08:45:00Z' if kind=='interval' else '2026-10-08T08:30:00Z')
 f['occurred']=instant(c['point'])
 if kind=='interval':f['recorded_interval'].update(start=instant(c['start']),end=instant(c['end']))
 else:f.pop('recorded_interval',None)
 t=f['recorded_interval'][boundary] if kind=='interval' else f['occurred']
 t['recorded'].update(precision=precision,uncertainty=uncertainty)
 if precision=='bounded':t['recorded'].update(lower='2026-10-08T08:00:00Z',upper='2026-10-08T09:15:00Z')
 if alternative:
  a={'timestamp_precision':'M7ExactTimestampInput/v1','source_timestamp':alternative,'recorded':{'status':'known','precision':'instant','value':alternative,'lower':None,'upper':None,'uncertainty':None},'source':{'namespace':'clinrx.synthetic.fc1','code':'alternative-clock','version':'1','raw_display':'Alternative source assertion'},'clock':'unknown','provenance':copy.deepcopy(f['provenance'])}
  t['alternative_sources']=[a]
 for entry in f['external_evidence']:
  if entry['namespace']=='clinrx.local.rf2/v1':entry['code']=json.dumps(e['metadata'],sort_keys=True,separators=(',',':'))
 validated=CirculatoryEvent.model_validate(f);f=validated.model_dump(mode='json');e['fact']=f;e['canonical_fact']=canonical_payload(validated);e['digest']=hashlib.sha256(e['canonical_fact'].encode()).hexdigest()
 return e
cases=[
 ('interval-approximate-start','interval','approximate','Collection boundary could be anywhere from 08:00 to 09:15',None,'start',False),
 ('interval-approximate-end','interval','approximate','End time may extend beyond the hour',None,'end',False),
 ('point-approximate','point','approximate','Point time uncertain across an hour',None,'start',False),
 ('interval-day','interval','day',None,None,'start',False),
 ('point-bounded','point','bounded','Bounds cross the 09:00 hour',None,'start',False),
 ('point-instant-uncertainty','point','instant','Timestamp remains uncertain despite instant precision',None,'start',False),
 ('interval-alternative-disagrees','interval','instant',None,'2026-10-08T09:30:00Z','start',False),
 ('point-alternative-disagrees','point','instant',None,'2026-10-08T09:30:00Z','start',False),
 ('exact-interval-unknown-clock','interval','instant',None,None,'start',True),
 ('exact-point-unknown-clock','point','instant',None,None,'start',True),
 ('exact-point-agreeing-alternative','point','instant',None,'2026-10-08T08:30:00Z','start',True),
]
out=[]
for name,kind,prec,unc,alt,bound,placed in cases:out.append({'name':name,'expected_placed':placed,'evidence':make(name,kind,prec,unc,alt,bound)})
p=repo/'frontend/tests/fixtures/rf2-fc1-timing.json';p.write_text(json.dumps(out,indent=2)+'\n')
(root/'rf2-fluid-chart-fc1-validation/FIXTURE-GENERATION.json').write_text(json.dumps({'script':'generate_fc1_fixtures.py','source_fixture':'frontend/tests/fixtures/rf2-api.json','validation':'Each synthetic fact validated with existing CirculatoryEvent model in memory, serialized with existing canonical_payload; no database/server, no backend test suite or changes. Existing frontend decoder validation occurs in focused tests.','examples':len(out),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'synthetic presentation fixtures, no physical identity/eligibility assertion'},indent=2)+'\n')
print(f'Generated and validated {len(out)} typed timing fixtures.')
