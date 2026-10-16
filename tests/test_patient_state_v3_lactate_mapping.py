"""Director regressions: independently specified correction boundaries."""
import pytest
from app.models.clinical.common import LineageEdge
from app.execution.patient_state_v3_inference import build_circulatory_timing_inference, CirculatoryInferenceError, EvidencePin
from test_persistence import database, registered
from test_patient_state_v3 import h, PROV, TARGET, change, records
from test_patient_state_v3_inference import inputs, selected


def test_f2_source_documented_lactate_admitted(registered):
    from test_patient_state_v3 import code
    p,l,v=inputs()
    l=change(l,acquisition=change(l.acquisition,parameter_support='source_documented',parameter=code('lactate'),parameter_concept='lactate',support_provenance=PROV))
    a,r=selected(registered,(p,l,v))
    assert 'concept' not in l.model_dump()
    assert h.LactateResult.model_validate_json(l.model_dump_json())==l
    assert build_circulatory_timing_inference(assembly=a,request=r).inputs[1]==l.reference



@pytest.mark.parametrize('index',[0,1,2,3,5,6,7,8,9])
def test_contradictory_measurement_mapping_rejected(index):
    from pydantic import ValidationError
    from test_patient_state_v3 import code
    f=records()[index]
    with pytest.raises(ValidationError,match='contradicts measurement concept'):
        change(f,acquisition=change(f.acquisition,parameter_support='source_documented',parameter=code('wrong'),parameter_concept='contradictory',support_provenance=PROV))


def test_singleton_lactate_does_not_add_serialized_concept():
    l=inputs()[1]
    assert 'concept' not in l.model_dump()
    assert 'concept' not in h.LactateResult.model_fields
