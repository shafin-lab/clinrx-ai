"""Additive local RF2 schema; no clinical union changes."""
import json
from pathlib import Path
from app.api.schemas.renal_fluid_entry import RF2Draft, ResolveRequest
from app.models.clinical.facts import ClinicalObservation
from app.persistence.metadata import IngestionMetadata, RepositoryCutoff

def bundle():
    roots={};definitions={}
    for model in (RF2Draft,ResolveRequest,ClinicalObservation,IngestionMetadata,RepositoryCutoff):
        schema=model.model_json_schema(mode='serialization')
        for name,s in schema.pop('$defs',{}).items():
            if name in definitions and definitions[name]!=s:raise ValueError('conflicting definition')
            definitions[name]=s
        roots[model.__name__]=schema
    return {'roots':roots,'definitions':definitions}
if __name__=='__main__':(Path(__file__).resolve().parents[1]/'frontend/src/api/rf2Schemas.json').write_text(json.dumps(bundle(),indent=2)+'\n')
