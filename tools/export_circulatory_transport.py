"""Export authoritative M7 serialization schemas; no inference or DB access."""
import json
from pathlib import Path
from pydantic import TypeAdapter
from app.api.schemas.common import DecimalString
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
    # Pydantic's serialization regex omits exponent spellings that Decimal
    # actually emits. Use the existing finite Decimal transport grammar while
    # preserving the complete source string, without a length restriction or
    # any numeric/date coercion. This affects only the isolated M7 registry.
    pattern=TypeAdapter(DecimalString).json_schema()['pattern']
    for name in ('Quantity','ExactQuantity','NonnegativeQuantity','PositiveQuantity'):
        if name in defs:
            value=defs[name]['properties']['value']
            defs[name]['properties']['value']={**value,'type':'string','pattern':pattern}
    return dict(roots=roots,definitions=defs)
if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'frontend/src/api/circulatorySchemas.json'
    path.write_text(json.dumps(schema_bundle(),indent=2)+'\n')
