"""Lossless, explicit mappings with conservative canonical-content equality."""
import json
from dataclasses import dataclass
from datetime import datetime

from pydantic import AwareDatetime, TypeAdapter
from pydantic_core import PydanticSerializationError

from pydantic import ValidationError

from app.models.clinical.facts import (
    ClinicalInference, ClinicalObservation, EncounterContext, MedicationAdministration,
    MedicationOrder, PatientContext,
)
from .entities import EncounterRow, FactRow, PAYLOAD_VERSION, PatientRow
from .errors import PersistenceInputError, StorageIntegrityError, UnsupportedOperation
from .metadata import IngestionMetadata

SUPPORTED_FACTS = {
    'observation': ClinicalObservation,
    'medication_order': MedicationOrder,
    'medication_administration': MedicationAdministration,
    'inference': ClinicalInference,
}
SupportedFact = ClinicalObservation | MedicationOrder | MedicationAdministration | ClinicalInference


@dataclass(frozen=True)
class StoredFact:
    fact: SupportedFact
    ingestion: IngestionMetadata


def validate_fact(fact) -> SupportedFact:
    model = SUPPORTED_FACTS.get(getattr(fact, 'kind', None))
    if model is None or type(fact) is not model:
        raise UnsupportedOperation('unsupported clinical fact category')
    return model.model_validate(fact)


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


def decode(row, model):
    if row.payload_version != PAYLOAD_VERSION:
        raise StorageIntegrityError('unsupported stored payload version')
    try:
        result = model.model_validate_json(row.payload)
        if canonical_payload(result) != row.payload:
            raise StorageIntegrityError('stored payload is not canonical')
        return result
    except (ValidationError, ValueError, TypeError, PersistenceInputError, UnsupportedOperation):
        raise StorageIntegrityError('stored payload failed domain validation or serialization') from None


def load_patient(row: PatientRow) -> PatientContext:
    patient = decode(row, PatientContext)
    if patient.patient_id != row.patient_id:
        raise StorageIntegrityError('patient envelope does not match payload')
    return patient


def load_encounter(row: EncounterRow) -> EncounterContext:
    encounter = decode(row, EncounterContext)
    if (encounter.encounter_id, encounter.patient_id) != (row.encounter_id, row.patient_id):
        raise StorageIntegrityError('encounter envelope does not match payload')
    return encounter


def load_fact(row: FactRow, repository_id: str) -> StoredFact:
    model = SUPPORTED_FACTS.get(row.kind)
    if model is None:
        raise StorageIntegrityError('unsupported stored fact category')
    fact = decode(row, model)
    target = fact.binding.target
    if (fact.kind, fact.id, fact.revision, target.patient_id, target.encounter_id,
            target.longitudinal_context_id) != (
            row.kind, row.fact_id, row.revision, row.patient_id, row.encounter_id, None):
        raise StorageIntegrityError('fact envelope does not match payload')
    try:
        metadata = IngestionMetadata(repository_id=repository_id,
            ingestion_sequence=row.ingestion_sequence, ingested_at=row.ingested_at,
            payload_version=row.payload_version)
    except ValidationError:
        raise StorageIntegrityError('invalid ingestion metadata') from None
    return StoredFact(fact, metadata)
