"""Validate maximum bounded RF2 note/pin/review carriers without storage changes."""
import json
from app.api.schemas.renal_fluid_entry import RF2Draft
from app.models.clinical.hemodynamics import CirculatoryEvent, EvidenceBinding
from app.models.clinical.recorded_v2 import SourceCode
from app.models.clinical.common import Reference
from app.demo.circulatory import fields, concept, PROV, TARGET
repository='ffffffff-ffff-4fff-bfff-ffffffffffff'
pins=[{'reference':{'kind':'circulatory_event','id':chr(97+n)*256,'version':'v'*256},'digest':'a'*64,'ingestion':100,'cutoff':200,'repository':repository} for n in range(12)]
reviews=[{'selected':p['reference'],'terminal':{**p['reference'],'version':'w'*256},'terminal_digest':'b'*64,'terminal_ingestion':200,'record_status':'withdrawn','retain_historical':True} for p in pins]
body=RF2Draft.model_validate({'repository':repository,'id':'ffffffff-ffff-4fff-bfff-ffffffffffff','revision':'eeeeeeee-eeee-4eee-beee-eeeeeeeeeeee','actor':'x'*128,'recorded_at':'2026-10-08T10:00:00Z','chart':None,'note':{**{k:'x'*512 for k in ('question','findings','possibilities','gaps','plan')},'pins':pins},'source_review':reviews,'predecessor':None,'reason':None})
entries=[SourceCode(namespace='clinrx.local.rf2.pin/v1',version='1',code=json.dumps(p,separators=(',',':')),raw_display='Exact selected evidence pin') for p in pins]
entries.extend(SourceCode(namespace='clinrx.local.rf2.review/v1',version='1',code=json.dumps(v,separators=(',',':')),raw_display='Explicit selected-source review decision') for v in reviews)
meta={'version':1,'chart':None,'note':{**body.note.model_dump(mode='json'),'pins':[]}}
entries.append(SourceCode(namespace='clinrx.local.rf2/v1',version='1',code=json.dumps(meta,separators=(',',':')),raw_display='Structured local source assertions'))
note=CirculatoryEvent(**fields('rf2-carrier-proof'),event_type='other',description=concept('x'*4096),external_evidence=tuple(entries),associations=tuple(EvidenceBinding(role='context',scope=TARGET,status='resolved',exact=Reference.model_validate(p['reference']),provenance=PROV) for p in pins))
size=len(note.model_dump_json().encode());request=len(body.model_dump_json().encode());largest=max(len(e.code.encode()) for e in entries)
assert len(entries)==25<=32 and len(note.associations)==12<=32 and largest<=4096 and request<=65536 and size<=65536
print(json.dumps({'status':'PASS','pins':12,'review_decisions':12,'carrier_entries':25,'max_entry_bytes':largest,'fact_bytes':size,'request_bytes':request,'local_body_budget':65536,'existing_response_limit':2097152,'no_model_or_limit_changes':True},indent=2))
