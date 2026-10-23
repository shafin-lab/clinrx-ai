"""RF1 serialization contracts, no database access or clinical policy."""
import json
from pathlib import Path
from pydantic import TypeAdapter
from app.api.schemas.common import DecimalString
from app.api.schemas.renal_fluid import RenalFluidResponse, RenalHistoryResponse

def schema_bundle():
    roots, definitions = {}, {}
    for model in (RenalFluidResponse, RenalHistoryResponse):
        schema = model.model_json_schema(mode='serialization')
        for name, value in schema.pop('$defs', {}).items():
            if name in definitions and definitions[name] != value:
                raise ValueError('conflicting schema')
            definitions[name] = value
        roots[model.__name__] = schema
    for name in ('Quantity', 'ExactQuantity', 'PositiveQuantity', 'NonnegativeQuantity'):
        if name in definitions:
            definitions[name]['properties']['value'] = {'type': 'string', 'pattern': TypeAdapter(DecimalString).json_schema()['pattern']}
    return {'roots': roots, 'definitions': definitions}

if __name__ == '__main__':
    (Path(__file__).resolve().parents[1] / 'frontend/src/api/renalFluidSchemas.json').write_text(json.dumps(schema_bundle(), indent=2) + '\n')
