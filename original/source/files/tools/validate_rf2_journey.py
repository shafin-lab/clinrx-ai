"""One explicit synthetic RF2 real-API journey; no browser/clinical-execution claim."""
import argparse,hashlib,json,sqlite3,urllib.request,urllib.error,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit

PREFIX='/api/v1/patients/synthetic-p1/encounters/synthetic-e1'
def rows(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        return {t:db.execute('SELECT * FROM "'+t+'" ORDER BY rowid').fetchall() for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
def redact(value):
    if isinstance(value,dict):return {k:'[REDACTED]' if k in ('state_context','command') else redact(v) for k,v in value.items()}
    if isinstance(value,list):return list(map(redact,value))
    return value
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def run(origin,database,output):
    parsed=urlsplit(origin)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username:raise ValueError('explicit loopback origin only')
    output.mkdir(parents=True,exist_ok=False);events=[];ledger=[];opener=urllib.request.build_opener(NoRedirect)
    def checkpoint(name):
        with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as a,sqlite3.connect(output/(name+'.sqlite3')) as b:a.backup(b)
        data=rows(database);(output/(name+'-rows.json')).write_text(json.dumps(data,indent=2)+'\n');return data
    def call(path,body=None):
        number=len(events)+1;raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode() if body is not None else None
        req=urllib.request.Request(origin+path,data=raw,headers={'Origin':origin,'Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=30) as r:status=r.status;reply=r.read()
        except urllib.error.HTTPError as r:status=r.code;reply=r.read()
        value=json.loads(reply);event={'number':number,'at':datetime.now(timezone.utc).isoformat(),'method':'POST' if raw is not None else 'GET','path':path,'status':status}
        if raw is not None:
            name=f'{number:03}-request.json';(output/name).write_bytes(raw);event.update(request=name,request_sha256=hashlib.sha256(raw).hexdigest())
        name=f'{number:03}-response-redacted.json';(output/name).write_text(json.dumps(redact(value),indent=2)+'\n');event['response']=name;events.append(event)
        return status,value
    def api(path,body=None):
        status,v=call(PREFIX+'/synthetic-rf2'+path,body);assert status==200,(status,v);return v
    def pin(item,catalog=None):
        f=item['fact'];return {'repository':item.get('repository') or catalog['repository'],'reference':{'kind':f['kind'],'id':f['id'],'version':f['revision']},'digest':item.get('digest') or item['expected_digest'],'ingestion':item['ingestion']['ingestion_sequence'],'cutoff':item.get('cutoff') or catalog['cutoff']['fact_watermark']}
    def chart(category,amount,record):
        return {'category':category,'amount':amount,'unit':'kg' if category=='weight' else 'mL','missing_reason':None,'point':'2026-10-08T09:45:00Z','start':None if category=='weight' else '2026-10-08T09:30:00Z','end':None if category=='weight' else '2026-10-08T09:45:00Z','acquisition':'measured' if category=='weight' else 'unknown','method':'Synthetic bed scale' if category=='weight' else None,'purpose':'body-weight review' if category=='weight' else None,'source_context':'Fictional distinct source collection; not a copy of earlier dosing or interval totals.','uncertainty':'Unauthenticated synthetic source; completeness and clinical relationship not established.','source_record':{'issuer_namespace':'clinrx.synthetic.rf2-journey','issuer':'synthetic-chart-A','record_namespace':'collection-record','record_id':record,'component':'weight' if category=='weight' else 'volume'},'source_version':None,'new_collection_reason':None}
    def draft(c=None,n=None):
        return {'repository':catalog['repository'],'id':str(uuid.uuid4()),'revision':str(uuid.uuid4()),'actor':'Synthetic journey operator','recorded_at':'2026-10-08T09:50:00Z','chart':c,'note':n,'predecessor':None,'reason':None}
    def save(body,label,discard_delivery=False):
        before=rows(database);api('/validate',body);assert rows(database)==before
        result=api('/save',body);assert result['status']=='saved';e=result['evidence'];after=rows(database)
        assert len(after['fact_revision'])==len(before['fact_revision'])+1
        ledger.append({'label':label,'reference':pin(e)['reference'],'sequence':e['ingestion']['ingestion_sequence'],'delivery_fault':'successful response discarded by validation client after actual API returned' if discard_delivery else None})
        if discard_delivery:
            delivered=events[-1];looked=api('/lookup',body);assert looked['evidence']['fact']==e['fact'];assert delivered['request_sha256']==events[-1]['request_sha256'];assert rows(database)==after
        return e
    baseline=checkpoint('before');status,health=call('/health');assert status==200 and health['execution_enabled'] is False
    catalog=api('');assert catalog['execution_enabled'] is False and catalog['combined']['execution_enabled'] is False
    items=catalog['combined']['circulatory']['assembly']['snapshot']['items'];weight=next(x for x in items if x['fact']['id']=='fs-WEIGHT');lab=next(x for x in catalog['combined']['laboratory']['observations'] if x['fact']['id']=='demo-creatinine-A')
    existing=api('/resolve',{'repository':catalog['repository'],'pins':[pin(weight,catalog),pin(lab,catalog)]});assert rows(database)==baseline
    assert existing['items'][0]['fact']==weight['fact'];assert existing['items'][0]['metadata'] is None
    ubody=draft(chart('output_urine','35.0000','urine-0945'));urine=save(ubody,'new urine collection')
    wbody=draft(chart('weight','70.0000','weight-0945'));absent_before=rows(database);absent=api('/lookup',wbody);absent_event=events[-1];assert absent['status']=='absent' and rows(database)==absent_before
    measured_weight=save(wbody,'explicit save after pre-dispatch absence');assert absent_event['request_sha256']==events[-1]['request_sha256']
    fluid=save(draft(chart('input_iv','50.0000','iv-0945')),'new documented fluid volume',discard_delivery=True)
    note={'question':'Review existing kidney and newly recorded interval evidence','findings':'Recorded sources only; measured weight is referenced for dosing review without another quantity row.','possibilities':'Patient-level relationship not established.','gaps':'Unknown source quality and incomplete fluid accounting remain.','plan':'Unscheduled clinician review; no action scheduled.','pins':[pin(urine),pin(measured_weight),pin(lab,catalog)]}
    original_note=save(draft(n=note),'original authored reassessment')
    uc=json.loads(json.dumps(ubody));uc.update(revision=str(uuid.uuid4()),predecessor=pin(urine),reason='Synthetic transcription correction, not a new collection or physiological improvement');uc['chart']['amount']='36.0000';corrected_urine=save(uc,'urine correction')
    wc=json.loads(json.dumps(wbody));wc.update(revision=str(uuid.uuid4()),predecessor=pin(measured_weight),reason='Synthetic weight transcription correction, not a new measurement');wc['chart']['amount']='71.0000';corrected_weight=save(wc,'weight correction')
    later_note=json.loads(json.dumps(note));later_note['question']='Review corrected source references';later_note['pins']=[pin(corrected_urine),pin(corrected_weight),pin(lab,catalog)];later_note['findings']='Corrected recorded sources; original note retains original revisions. Corrections do not establish treatment response or improvement.'
    new_note=save(draft(n=later_note),'new authored reassessment')
    assert original_note['metadata']['note']['pins'][0]['reference']==pin(urine)['reference'];assert new_note['metadata']['note']['pins'][0]['reference']==pin(corrected_urine)['reference']
    reads_before=rows(database)
    old_history=api('/history',{'repository':catalog['repository'],'pins':[pin(corrected_urine)]});assert [e['fact']['revision'] for e in old_history['items']]==[urine['fact']['revision'],corrected_urine['fact']['revision']]
    pins=[pin(corrected_urine),pin(corrected_weight),pin(new_note),pin(original_note),pin(urine),pin(measured_weight)]
    resolved=api('/resolve',{'repository':catalog['repository'],'pins':pins});assert [e['fact']['revision'] for e in resolved['items']]==[p['reference']['version'] for p in pins]
    assert resolved['items'][-1]['superseded'] is True
    replay=json.loads(json.dumps(ubody));replay.update(id=str(uuid.uuid4()),revision=str(uuid.uuid4()),actor='Another synthetic recorder');replayed=api('/save',replay)
    assert replayed['status']=='source_replay' and replayed['evidence']['fact']==urine['fact'] and replayed['evidence']['superseded'] is True
    assert replayed['evidence']['terminal_reference']==pin(corrected_urine)['reference'];assert rows(database)==reads_before
    final_catalog=api('');assert final_catalog['cutoff']['fact_watermark']==len(baseline['fact_revision'])+7
    for path in ('/circulatory-review-preparations','/circulatory-reviews'):
        status,_=call(PREFIX+path,{});assert status==404
    final=checkpoint('after');assert final['fact_revision'][:len(baseline['fact_revision'])]==baseline['fact_revision'];assert len(final['fact_revision'])==len(baseline['fact_revision'])+7
    for t in baseline:
        if t not in ('fact_revision','revision_link','sqlite_sequence'):assert final[t]==baseline[t]
    assert len(final['revision_link'])==len(baseline['revision_link'])+2
    with sqlite3.connect(database) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    summary={'status':'PASS','kind':'implementation-operated real HTTP API journey; no browser or localStorage execution claim','origin':origin,'repository':catalog['repository'],'baseline_facts':len(baseline['fact_revision']),'final_facts':len(final['fact_revision']),'new_facts_and_revisions':7,'original_rows_preserved':True,'retained_receipts_unchanged':len(final['circulatory_execution']),'execution_enabled':False,'source_reuse_zero_writes':True,'source_replay_after_correction_zero_writes':True,'ledger':ledger,'events':len(events),'limitations':['Client-side successful-response discard, not socket loss','Pre-dispatch absence, not rollback proof','Saved handover and browser reload are covered separately by component tests, not this API journey']}
    (output/'events.json').write_text(json.dumps(events,indent=2)+'\n');(output/'RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()};(output/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--origin',required=True);p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.origin,a.database.resolve(),a.output.resolve())
