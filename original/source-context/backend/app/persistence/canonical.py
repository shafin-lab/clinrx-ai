"""Lossless canonical serialization, shared without persistence admission imports."""
import json
from datetime import datetime
from pydantic import AwareDatetime, TypeAdapter, ValidationError
from pydantic_core import PydanticSerializationError
from .errors import PersistenceInputError, UnsupportedOperation

_AWARE_TIME = TypeAdapter(AwareDatetime)


def _check_timestamps(original, encoded):
    """Reject lossy representations recursively; never normalize retained timestamps."""
    if isinstance(original, datetime):
        try:
            restored = _AWARE_TIME.validate_python(encoded)
        except (ValidationError, ValueError, TypeError):
            raise UnsupportedOperation('timestamp is not faithfully representable in payload version 1') from None
        # Compare wall time AND offset, not datetime equality alone (which can
        # equate different offsets or obscure fold distinctions).
        if original.isoformat() != restored.isoformat():
            raise UnsupportedOperation('timestamp is not faithfully representable in payload version 1')
    elif isinstance(original, dict):
        for key, value in original.items():
            _check_timestamps(value, encoded[key])
    elif isinstance(original, (tuple, list)):
        for value, serialized in zip(original, encoded, strict=True):
            _check_timestamps(value, serialized)


def canonical_payload(model) -> str:
    # JSON key order and omitted defaults do not affect equality. Array order,
    # Decimal lexical precision, offsets and source spelling DO remain material.
    try:
        original = model.model_dump(mode='python', exclude_none=False, exclude_defaults=False)
        encoded = model.model_dump(mode='json', exclude_none=False, exclude_defaults=False)
        _check_timestamps(original, encoded)
        return json.dumps(encoded, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)
    except (ValidationError, PydanticSerializationError, ValueError, TypeError):
        raise PersistenceInputError('payload serialization failed') from None

