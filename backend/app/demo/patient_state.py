"""Explicit deterministic synthetic bootstrap and reasoned correction CLI.

Only use a disposable local database. Repeated bootstrap/correction is exact-content
idempotent and never resets, deletes, or rewinds an existing revision chain.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from alembic import command
from alembic.config import Config
from app.models.clinical.common import (Binding, ClinicalTime, ClinicalValue, ContextTarget,
    IdentityVerification, Provenance, Quantity, Source, Unit)
from app.models.clinical.facts import (ClinicalObservation, Dose, EncounterContext,
    MedicationIdentity, MedicationOrder, PatientContext)
from app.persistence.database import create_database
from app.persistence.repository import transaction

AT = datetime(2026, 10, 8, 8, tzinfo=timezone.utc)
SIMULATION_AT = datetime(2026, 10, 8, 12, 1, tzinfo=timezone.utc)
TARGET = ContextTarget(patient_id='synthetic-p1', encounter_id='synthetic-e1')
SOURCE = Source(namespace='clinrx.synthetic.demo', identifier='patient-state-v1', version='1', channel='system')


def facts():
    binding = Binding(target=TARGET, verification=IdentityVerification(status='verified',
        method='synthetic-demo', verifier='synthetic-system', assessed_at=AT, source=SOURCE))
    def fields(id, at, source):
        return dict(id=id, revision='1', binding=binding, origin='reported',
            time=ClinicalTime(event=at, recorded=at, precision='instant'),
            provenance=Provenance(source=source, actor='synthetic-demo', recorded_at=at,
                lineage='unknown', limitations=('Synthetic demonstration only; no clinical feed.',)),
            verification='verified', conflict='none_known', temporal_status='historical',
            uncertainty=('Synthetic recorded evidence only.',))
    labs = []
    for label, value, at in (('A', '1.00', AT), ('B', '2.000', AT+timedelta(hours=2))):
        source = Source(namespace='clinrx.synthetic.serum-creatinine', identifier='demo-sample-'+label, version='1', channel='measurement')
        labs.append(ClinicalObservation(**fields('demo-creatinine-'+label, at, source),
            concept_id='synthetic-serum-creatinine', value=ClinicalValue(status='known', value=Quantity(value=Decimal(value),
                unit=Unit(raw='mg/dL', code='mg/dL', system='UCUM', status='assessed')))))
    medication = MedicationOrder(**fields('demo-medication-M', AT+timedelta(hours=1), SOURCE),
        medication=MedicationIdentity(product_id='synthetic-product', ingredient_ids=('synthetic-ingredient',)),
        prescribed_dose=Dose(amount=Quantity(value=Decimal('1.0'), unit=Unit(raw='mg', code='mg', system='UCUM', status='assessed')), basis='per_dose'),
        route='synthetic route', schedule_text='synthetic single event', order_status='active')
    return labs[0], labs[1], medication


def manifest():
    a, b, m = facts()
    return dict(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id,
        review_start=AT.isoformat(), review_end=(AT+timedelta(hours=2)).isoformat(),
        earlier_laboratory=a.reference.model_dump(), later_laboratory=b.reference.model_dump(), medication=m.reference.model_dump(),
        mode='historical synthetic simulation', simulation_at=SIMULATION_AT.isoformat())


def bootstrap(engine):
    # Explicit caller action; never run during app import/startup.
    config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
    with transaction(engine) as repository:
        repository.register_patient(PatientContext(patient_id=TARGET.patient_id, source_identifiers=(SOURCE,)))
        repository.register_encounter(EncounterContext(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id,
            time=ClinicalTime(event=AT, precision='instant'), source=SOURCE))
        a, b, m = facts()
        for fact in (a, m, b):
            repository.append_fact(fact, target=TARGET)
    return manifest()


def correct(engine):
    a, _, _ = facts()
    corrected = ClinicalObservation.model_validate({**a.model_dump(), 'revision': '2',
        'supersedes': a.reference, 'correction_reason': 'Explicit synthetic correction scenario.',
        'value': ClinicalValue(status='known', value=Quantity(value=Decimal('1.50'),
            unit=Unit(raw='mg/dL', code='mg/dL', system='UCUM', status='assessed')))})
    with transaction(engine) as repository:
        repository.append_revision(corrected, target=TARGET)
    return dict(patient_id=TARGET.patient_id, encounter_id=TARGET.encounter_id,
        consumed=a.reference.model_dump(), corrected=corrected.reference.model_dump())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('bootstrap', 'correct'))
    parser.add_argument('--database', type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_absolute():
        parser.error('absolute disposable database path required')
    engine = create_database(args.database)
    try:
        print(json.dumps((bootstrap if args.action == 'bootstrap' else correct)(engine), sort_keys=True))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
