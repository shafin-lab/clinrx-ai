"""Lossless, explicit mappings with conservative canonical-content equality."""
from dataclasses import dataclass


from pydantic import ValidationError

from app.models.clinical.facts import (
    ClinicalInference, ClinicalObservation, EncounterContext, MedicationAdministration,
    MedicationOrder, PatientContext,
)
from .entities import EncounterRow, FactRow, PAYLOAD_VERSION, PatientRow
from .errors import PersistenceInputError, StorageIntegrityError, UnsupportedOperation
from .metadata import IngestionMetadata
from .canonical import canonical_payload
from app.models.clinical.microbiology import (Specimen, DirectExamination, CultureFinding,
    IsolateIdentification, SusceptibilityResult, ResistanceFinding, MolecularResult,
    BloodCultureSet, BloodCultureBottle)
from app.models.clinical.antimicrobials import (AntimicrobialOrder,
    CompletedAntimicrobialAdministration, AntimicrobialNonDelivery)
from app.models.clinical.laboratory import LaboratoryReport
from app.models.clinical.respiratory import RespiratoryRecord
from app.models.clinical.transfusion import M10_FACTS, M10Record

from app.models.clinical.hemodynamics import M7_FACTS, CirculatoryRecord

SUPPORTED_FACTS = {
    'observation': ClinicalObservation,
    'medication_order': MedicationOrder,
    'medication_administration': MedicationAdministration,
    'inference': ClinicalInference,
    'microbiology_specimen': Specimen,
    'microbiology_direct_examination': DirectExamination,
    'microbiology_culture': CultureFinding,
    'microbiology_isolate': IsolateIdentification,
    'microbiology_susceptibility': SusceptibilityResult,
    'microbiology_resistance': ResistanceFinding,
    'microbiology_molecular': MolecularResult,
    'blood_culture_set': BloodCultureSet,
    'blood_culture_bottle': BloodCultureBottle,
    'antimicrobial_order': AntimicrobialOrder,
    'antimicrobial_administration': CompletedAntimicrobialAdministration,
    'antimicrobial_non_delivery': AntimicrobialNonDelivery,
    'laboratory_report': LaboratoryReport,
    'respiratory_record': RespiratoryRecord,
}
SupportedFact = (ClinicalObservation | MedicationOrder | MedicationAdministration | ClinicalInference
    | Specimen | DirectExamination | CultureFinding | IsolateIdentification | SusceptibilityResult | ResistanceFinding | MolecularResult | BloodCultureSet | BloodCultureBottle | AntimicrobialOrder | CompletedAntimicrobialAdministration | AntimicrobialNonDelivery | LaboratoryReport | RespiratoryRecord)


SUPPORTED_FACTS = {**SUPPORTED_FACTS, **M7_FACTS, **M10_FACTS}
SupportedFact = SupportedFact | CirculatoryRecord | M10Record

@dataclass(frozen=True)
class StoredFact:
    fact: SupportedFact
    ingestion: IngestionMetadata


def validate_fact(fact) -> SupportedFact:
    model = SUPPORTED_FACTS.get(getattr(fact, 'kind', None))
    if model is None or type(fact) is not model:
        raise UnsupportedOperation('unsupported clinical fact category')
    return model.model_validate(fact)



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
