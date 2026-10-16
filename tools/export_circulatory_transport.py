"""Export authoritative M7 serialization schemas; no inference or DB access."""
import json
from pathlib import Path
from app.api.schemas import circulatory as c

def schema_bundle():
    defs={};roots={}
    for model in (c.CirculatoryStateResponse,c.CirculatoryPreparedResponse,c.CirculatoryExecutionResponse,
                  c.CirculatoryReconciliationResponse,c.CirculatoryHistoryResponse):
        schema=model.model_json_schema(mode='serialization')
        for key,value in schema.pop('$defs',{}).items():
            if key in defs and defs[key]!=value:raise ValueError('conflicting schema definition')
            defs[key]=value
        roots[model.__name__]=schema
    return dict(roots=roots,definitions=defs)
if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'frontend/src/api/circulatorySchemas.json'
    path.write_text(json.dumps(schema_bundle(),indent=2)+'\n')
