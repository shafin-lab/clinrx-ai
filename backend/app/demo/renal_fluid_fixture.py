"""Explicit opt-in disposable RF1 fixture; never seeds or edits at startup."""
from app.demo.icu_flowsheet import bootstrap as icu_bootstrap
from app.demo.patient_state import facts as original_labs, TARGET
from app.models.clinical.facts import ClinicalObservation
from app.demo.icu_chart_entries import entry
from app.persistence.repository import transaction

def observations():
    a, b, _ = original_labs()
    # Reuse the existing two laboratory samples already composed by the ICU bootstrap.
    correction = ClinicalObservation.model_validate({**a.model_dump(), 'revision': '2',
        'supersedes': a.reference, 'correction_reason': 'Synthetic transcription correction, not a new sample.',
        'value': {**a.value.model_dump(), 'value': {**a.value.value.model_dump(), 'value': '1.1000'}}})
    missing = ClinicalObservation.model_validate({**a.model_dump(), 'id': 'rf1-creatinine-missing',
        'value': {'status': 'missing', 'reason': 'Source result unavailable.'},
        'time': {'precision': 'unknown', 'uncertainty': 'Source event time unavailable.'}})
    unlike = ClinicalObservation.model_validate({**b.model_dump(), 'id': 'rf1-creatinine-unlike-unit',
        'conflict': 'unresolved', 'verification': 'unverified',
        'value': {'status': 'known', 'value': {'value': '150.0', 'unit': {'raw': 'umol/L',
            'status': 'unresolved', 'limitation': 'Source unit retained without conversion.'}}},
        'uncertainty': ('Synthetic conflicting report; no corroboration or interpretation.',)})
    return a, b, correction, missing, unlike

def fluid_examples():
    # New opt-in assertions; no generated sums or rewritten existing chart facts.
    return (
        entry('rf1-urine-zero', 'output_urine', 75, 'Recorded zero over this interval only.', '0', 'mL', start=60),
        entry('rf1-urine-gap', 'output_urine', 105, 'Source interval after an undocumented gap; no continuity inferred.', '20', 'mL', start=90),
        entry('rf1-urine-overlap', 'output_urine', 110, 'Overlapping source interval; independent accounting is not established.', '15', 'mL', start=100),
        entry('rf1-urine-missing', 'output_urine', 115, 'Source amount unavailable; not zero.', start=110),
        entry('rf1-fluid-withdrawn', 'input_iv', 120, 'Withdrawn source assertion; no older value substituted.', '50', 'mL', start=115, record_status='withdrawn'),
    )

def bootstrap(engine):
    result = icu_bootstrap(engine)
    with transaction(engine) as repo:
        for fact in (*observations(), *fluid_examples()):
            if fact.supersedes:
                repo.append_revision(fact, target=TARGET)
            else:
                repo.append_fact(fact, target=TARGET)
    return {**result, 'dataset': 'synthetic-renal-fluid/1', 'execution_enabled': False}
