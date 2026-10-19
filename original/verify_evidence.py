"""Portable data-only RF2 evidence checks. Does not run the app or tests."""
import hashlib,json,sqlite3
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent

def digest(b):return hashlib.sha256(b).hexdigest()
def db_rows(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        return {t:db.execute('SELECT * FROM "'+t+'" ORDER BY rowid').fetchall() for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
def manifests(folder):
    manifest=folder/'SHA256SUMS.json'
    if manifest.exists():
        for name,expected in json.loads(manifest.read_text()).items():assert digest((folder/name).read_bytes())==expected,(folder,name)
    return len(json.loads(manifest.read_text())) if manifest.exists() else 0

def run():
    checks={}
    source=json.loads((ROOT/'source/FILES.json').read_text())
    for name,identity in source.items():
        b=(ROOT/'source/files'/name).read_bytes()
        assert digest(b)==identity['sha256'] and len(b)==identity['bytes']
        assert hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()==identity['git_blob']
    commit=(ROOT/'source/commit.raw').read_bytes()
    assert hashlib.sha1(('commit '+str(len(commit))+'\0').encode()+commit).hexdigest()==json.loads((ROOT/'source/IDENTITY.json').read_text())['source']
    checks['source_files']=len(source)
    for folder in ('api-journey','final-revalidation','ownership-revalidation'):checks[folder+'_hashes']=manifests(ROOT/folder)
    before=db_rows(ROOT/'api-journey/before.sqlite3');after=db_rows(ROOT/'api-journey/after.sqlite3')
    for name,rows in [('before',before),('after',after)]:assert json.loads(json.dumps(rows))==json.loads((ROOT/'api-journey'/f'{name}-rows.json').read_text())
    assert len(before)==12 and len(before['fact_revision'])==175 and len(after['fact_revision'])==182
    assert after['fact_revision'][:175]==before['fact_revision']
    for table in before:
        if table not in ('fact_revision','revision_link','sqlite_sequence'):assert after[table]==before[table]
    assert len(after['revision_link'])==len(before['revision_link'])+2
    for folder in ('final-revalidation','ownership-revalidation'):
        assert db_rows(ROOT/folder/'after-revalidation.sqlite3')==after
        assert json.loads((ROOT/folder/'after-rows.json').read_text())==json.loads(json.dumps(after))
    facts={(r[1],r[2],r[3]):r for r in after['fact_revision']};verified=0
    def walk(value):
        nonlocal verified
        if isinstance(value,dict):
            if 'fact' in value and isinstance(value['fact'],dict) and 'ingestion' in value and value['ingestion'] is not None:
                f=value['fact'];key=(f['kind'],f['id'],f['revision']);row=facts[key];assert json.loads(row[7])==f
                assert f['binding']['target']['patient_id']==row[4]=='synthetic-p1' and f['binding']['target']['encounter_id']==row[5]=='synthetic-e1'
                expected=value.get('digest',value.get('expected_digest'));assert expected==digest(row[7].encode())
                if 'canonical_fact' in value:assert value['canonical_fact']==row[7]
                m=value['ingestion'];assert m['ingestion_sequence']==row[0] and m['payload_version']==row[6]
                assert datetime.fromisoformat(m['ingested_at'].replace('Z','+00:00'))==datetime.fromisoformat(row[8])
                if 'cutoff' in value:assert row[0]<=value['cutoff']<=182
                verified+=1
            if 'canonical_assembly' in value:
                assert json.loads(value['canonical_assembly'])==value['circulatory']['assembly']
                assert digest(value['canonical_assembly'].encode())==value['context']['circulatory_digest']
                assert json.loads(value['canonical_laboratory'])==value['laboratory']
                assert digest(value['canonical_laboratory'].encode())==value['context']['observations_digest']
                assert value['context']['scope']==value['laboratory']['scope']==value['circulatory']['assembly']['request']['scope']
                assert value['execution_enabled'] is False
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for x in value:walk(x)
    events=json.loads((ROOT/'api-journey/events.json').read_text());command_checks=0
    for e in events:
        response=json.loads((ROOT/'api-journey'/e['response']).read_text());walk(response)
        if 'request' in e:
            body=(ROOT/'api-journey'/e['request']).read_bytes();assert digest(body)==e['request_sha256']
            if 'request_canonical' in response:
                assert digest(response['request_canonical'].encode())==response['request_digest']
                assert json.loads(response['request_canonical'])==json.loads(body);command_checks+=1
    for folder in ('final-revalidation','ownership-revalidation'):
        for p in (ROOT/folder).glob('*.json'):
            if p.name not in ('after-rows.json','SHA256SUMS.json','RESULTS.json'):walk(json.loads(p.read_text()))
    ledger=json.loads((ROOT/'api-journey/RESULTS.json').read_text())['ledger'];assert len(ledger)==7
    assert [(x['reference']['kind'],x['reference']['id'],x['reference']['version']) for x in ledger]==[(r[1],r[2],r[3]) for r in after['fact_revision'][175:]]
    notes=[json.loads(r[7]) for r in after['fact_revision'][175:] if any(x['label'] in ('original authored reassessment','new authored reassessment') and x['sequence']==r[0] for x in ledger)]
    for f in notes:
        entries=[x for x in f['external_evidence'] if x['namespace']=='clinrx.local.rf2.pin/v1'];assert len(entries)==3
        for x in entries:
            p=json.loads(x['code']);ref=p['reference'];r=facts[(ref['kind'],ref['id'],ref['version'])]
            assert digest(r[7].encode())==p['digest'] and r[0]==p['ingestion']<=p['cutoff']
            assert any(b['exact']==ref and b['role']=='context' and b['status']=='resolved' for b in f['associations'])
    checks.update(status='PASS',tables=12,original_facts_preserved=175,added_facts_and_revisions=7,retained_receipts=2,verified_fact_correspondences=verified,verified_command_correspondences=command_checks,notes_with_exact_mixed_pins=len(notes))
    if (ROOT/'EVIDENCE-SHA256SUMS.json').exists():
        for path,expected in json.loads((ROOT/'EVIDENCE-SHA256SUMS.json').read_text()).items():assert digest((ROOT/path).read_bytes())==expected,path
        checks['combined_manifest']='PASS'
    print(json.dumps(checks,indent=2))
if __name__=='__main__':run()
