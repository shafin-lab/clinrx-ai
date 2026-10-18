"""Read-only checks for captured local browser exercise. Does not replay the browser."""
import hashlib,json,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parent
before=json.loads((root/'before-rows.json').read_text());after=json.loads((root/'after-rows.json').read_text())
assert set(before)==set(after)
assert after['fact_revision'][:len(before['fact_revision'])]==before['fact_revision']
for table in before:
    if table not in ('fact_revision','sqlite_sequence'):
        assert after[table]==before[table],table
assert len(after['fact_revision'])-len(before['fact_revision'])==7
state=json.loads((root/'after-state.json').read_text());assert state['execution_enabled'] is False
with sqlite3.connect(root/'after.sqlite3') as db:
    db.row_factory=sqlite3.Row
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    rows=db.execute('SELECT * FROM fact_revision').fetchall()
    pins={(r['kind'],r['fact_id'],r['revision']):r for r in rows}
    for item in state['assembly']['snapshot']['items']:
        f=item['fact'];row=pins[f['kind'],f['id'],f['revision']]
        assert json.loads(row['payload'])==f
        assert hashlib.sha256(row['payload'].encode()).hexdigest()==item['expected_digest']
        assert row['patient_id']==f['binding']['target']['patient_id']=='synthetic-p1'
        assert row['encounter_id']==f['binding']['target']['encounter_id']=='synthetic-e1'
        assert row['ingestion_sequence']==item['ingestion']['ingestion_sequence']
    new=[json.loads(r['payload']) for r in rows if r['ingestion_sequence']>162]
    assert [f['kind'] for f in new]==['circulatory_pressure','circulatory_oxygen','circulatory_cardiac','circulatory_echo','circulatory_vasoactive','circulatory_perfusion','circulatory_event']
    for f in new:
        assert f['occurred']['clock']=='unknown'
        assert f['binding']['verification']['status']=='unresolved'
        assert f['available']['recorded']['status']=='not_recorded'
    assert new[0]['result']['quantity']['value']=='71.00'
    assert new[1]['blood_gas_context']['fio2']['value']=='40'
    assert new[1]['blood_gas_context']['peep']['value']=='5'
    assert new[2]['result']['quantity']['value']=='4.700'
    assert new[2]['acquisition']['quality']['status']=='suspect'
    assert new[3]['production']=='source_calculated'
    assert new[3]['occurred']['source_timestamp']=='2026-10-08T08:00:00Z'
    assert new[4]['action']['event_type']=='rate_change'
    assert new[4]['action']['delivery']['rate']['value']=='2.50'
    note=new[-1]
    exacts={json.dumps(a['exact'],sort_keys=True) for a in note['associations']}
    assert len(exacts)==3
    for stage in ('baseline','intervention','followup'):
        code=next(c for c in note['external_evidence'] if c['namespace']=='clinrx.local.reassessment.'+stage+'/v1')
        ref=json.loads(code['code']);assert json.dumps(ref,sort_keys=True) in exacts
        assert (ref['kind'],ref['id'],ref['version']) in pins
    assert 'Patient-level relationship is not established' in note['description']['raw_display']
    receipts=db.execute('SELECT * FROM circulatory_execution').fetchall()
    for receipt in receipts:assert hashlib.sha256(receipt['payload'].encode()).hexdigest()==receipt['payload_digest']
report={'status':'PASS','original_rows_retained':162,'new_browser_appends':7,'after_fact_revisions':169,'api_items_checked':163,'retained_receipts_unchanged':2,'reassessment_exact_references':3,'execution_enabled':False,'limitations':'Captured browser DOM/screenshots, server metadata and subsequent API/database correspondence; no complete browser request/response trace or independent review claimed.'}
(root/'browser-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
