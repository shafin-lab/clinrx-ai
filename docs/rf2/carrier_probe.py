import json
from app.models.clinical.hemodynamics import CirculatoryEvent, EvidenceBinding
from app.models.clinical.recorded_v2 import SourceCode
from app.models.clinical.common import Reference
from app.demo.circulatory import fields, concept, PROV, TARGET
pins=[{'reference':{'kind':'circulatory_event','id':str(n)*256,'version':'v'*256},'digest':'a'*64,'ingestion':100,'cutoff':200,'repository':'f'*36} for n in range(12)]
entries=[SourceCode(namespace='clinrx.local.rf2.pin/v1',code=json.dumps(p,separators=(',',':')),raw_display='Exact selected evidence pin') for p in pins]
meta={'version':1,'category':'weight','acquisition':'unknown','purpose':'dosing','method':None,'source_record':{'issuer_namespace':'x'*128,'issuer':'y'*128,'record_namespace':'z'*128,'record_id':'r'*128,'component':'c'*128},'missing_reason':None}
entries.append(SourceCode(namespace='clinrx.local.rf2/v1',code=json.dumps(meta,separators=(',',':')),raw_display='Structured local source assertions'))
note=CirculatoryEvent(**fields('rf2-carrier-proof'),event_type='other',description=concept('x'*4096),external_evidence=tuple(entries),associations=tuple(EvidenceBinding(role='context',scope=TARGET,status='resolved',exact=Reference.model_validate(p['reference']),provenance=PROV) for p in pins))
size=len(note.model_dump_json().encode());assert len(entries)==13<=32 and len(note.associations)==12<=32 and max(len(e.code.encode()) for e in entries)<=4096 and size<65536
print(json.dumps({'status':'PASS','pins':12,'carrier_entries':13,'max_entry_bytes':max(len(e.code.encode()) for e in entries),'fact_bytes':size,'local_body_budget':65536,'existing_response_limit':2097152,'no_model_or_limit_changes':True},indent=2))
