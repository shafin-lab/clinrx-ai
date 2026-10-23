"""M10 reuses the shared typed laboratory owner without unit conversion."""
import pytest
from app.models.clinical.laboratory import LaboratoryComponent

@pytest.mark.parametrize('concept,value,unit',[
 ('hemoglobin','8.00','g/dL'),('hematocrit','24.0','%'),('platelets','75','10^9/L'),
 ('pt','18.00','s'),('inr','1.60','1'),('aptt','42.0','s'),('thrombin_time','19','s'),
 ('fibrinogen','150','mg/dL'),('total_calcium','8.10','mg/dL'),
 ('ionised_calcium','0.990','mmol/L'),('d_dimer','2.10','mg/L FEU'),('anti_xa','0.4','IU/mL')])
def test_shared_coagulation_components_preserve_mapping_value_and_original_unit(concept,value,unit):
    c=LaboratoryComponent(source_component_id='original-'+concept,
        test_code={'namespace':'hospital.lab','code':concept,'version':'1','raw_display':concept},
        mapping_status='mapped',mapped_concept=concept,mapping_version='clinrx-shared-labs/2',
        result={'kind':'numeric','raw_value':value,'comparator':'=','unit':{'namespace':'source.unit','code':unit,'raw_display':unit}})
    assert c.result.raw_value==value
    assert c.result.unit.raw_display==unit
    assert c.mapped_concept==concept
