"""Generate the strict manual chart request schema; M6 facts reuse existing schema."""
import json
from pathlib import Path
from app.api.schemas.antibiotic_chart import AntibioticDraft,AntibioticHistoryRequest

def bundle():
    roots={};definitions={}
    for cls in (AntibioticDraft,AntibioticHistoryRequest):
        schema=cls.model_json_schema(mode='serialization');definitions.update(schema.pop('$defs',{}));roots[cls.__name__]=schema
    return dict(roots=roots,definitions=definitions)
if __name__=='__main__':(Path(__file__).resolve().parents[1]/'frontend/src/api/antibioticSchemas.json').write_text(json.dumps(bundle(),indent=2)+'\n')
