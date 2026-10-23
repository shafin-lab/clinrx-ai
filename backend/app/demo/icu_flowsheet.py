"""Opt-in fictional ICU sequence. Uses existing contracts; never seeds on startup."""
from datetime import timedelta
from app.demo.comprehensive import bootstrap as baseline_bootstrap, demo_facts, replace
from app.demo.circulatory import fields, stamp, quantity, acquisition, device, code, concept, TARGET, PROV
from app.demo.patient_state import AT
from app.models.clinical import hemodynamics as h
from app.persistence.repository import transaction
from app.models.clinical.common import Reference
from app.demo.icu_chart_entries import context_facts,entry


def flowsheet_facts():
    originals={f.id:f for f in demo_facts()}
    records=list(context_facts())
    for n,(minute,map_value,co,ci,cvp,hr,ph,paco2,pao2,lactate) in enumerate([
        (15,'61','4.00','2.30','9.0','104','7.30','50.0','80.0','2.4'),
        (30,'68','4.40','2.50','10.0','108','7.32','47.0','84.0','2.2'),
        (45,'72','4.70','2.70','9.0','102','7.34','45.0','86.0','2.1'),
        (60,'70','4.60','2.60','9.0','96','7.35','44.0','88.0','2.0'),
    ]):
        at=AT+timedelta(minutes=minute)
        for suffix,template_id,v in [('MAP','m7-P',map_value),('CO','m7-CO',co),('CI','m7-CI',ci),('CVP','m7-PAC',cvp),('PH','m7-ABG-PH',ph),('PACO2','m7-ABG-PACO2',paco2),('PAO2','m7-ABG-PAO2',pao2),('LACTATE','m7-L',lactate)]:
            template=originals[template_id];extra={}
            result=replace(template.result,quantity=replace(template.result.quantity,value=v))
            acq=template.acquisition
            if suffix=='MAP':acq=acquisition('invasive_arterial',site=concept('Synthetic radial arterial line'))
            if suffix in ('CO','CI'):
                acq=replace(acq,respiratory_phase=concept('Source-charted end expiration'),position=concept('Source-charted semi-recumbent position'),averaging=quantity('3','{injections}'),indexing_denominator=quantity('1.73','m2') if suffix=='CI' else None,indexing_basis=PROV if suffix=='CI' else None)
            if suffix=='CI':extra.update(production='source_calculated',calculation_method=code('source-chart-reported-cardiac-index'))
            if suffix=='CO' and minute==60:acq=replace(acq,quality=h.EvidenceQuality(status='suspect',provenance=PROV,limitations=('Synthetic acquisition quality concern; not corroborating proof.',)))
            if suffix in ('PH','PACO2','PAO2'):
                extra.update(specimen=code('fs-arterial-sample-'+str(minute)),blood_gas_context=replace(template.blood_gas_context,collected=stamp(at)))
            if suffix=='LACTATE':extra.update(collected=stamp(at),blood_source='arterial',specimen=code('fs-lactate-'+str(minute)))
            records.append(replace(template,id='fs-'+suffix+'-'+str(minute),occurred=stamp(at),available=stamp(at+timedelta(minutes=3)),result=result,acquisition=acq,**extra))
        for concept_id,value in [('systemic_systolic',{15:'92',30:'101',45:'110',60:'106'}[minute]),('systemic_diastolic',{15:'47',30:'52',45:'55',60:'53'}[minute])]:
            template=originals['m7-P']
            records.append(replace(template,id='fs-'+concept_id+'-'+str(minute),concept=concept_id,occurred=stamp(at),available=stamp(at),result=h.NumericResult(quantity=quantity(value,'mmHg')),acquisition=acquisition('invasive_arterial',site=concept('Synthetic radial arterial line'))))
        records.append(h.ECGObservation(**{**fields('fs-HR-'+str(minute)),'id':'fs-HR-'+str(minute),'occurred':stamp(at),'available':stamp(at)},concept='heart_rate',result=h.NumericResult(quantity=quantity(hr,'/min')),acquisition=acquisition('ecg_monitor'),production='direct_measurement',interpretation_source='monitor'))
    # Separate observations, not corrections or inferred continuous infusion intervals.
    events=[
        ('N-ORDER',5,'norepinephrine','order','5','mcg/min'),
        ('N-START',10,'norepinephrine','initiation','5','mcg/min'),
        ('N-CHANGE',15,'norepinephrine','rate_change','7','mcg/min'),
        ('V-START',15,'vasopressin','initiation','1.8','units/h'),
        ('D-ORDER',20,'dobutamine','order','2.5','mcg/kg/min'),
        ('D-START',30,'dobutamine','initiation','2.5','mcg/kg/min'),
        ('D-CHANGE',45,'dobutamine','rate_change','3.0','mcg/kg/min'),
        ('N-REDUCE',45,'norepinephrine','rate_change','6','mcg/min'),
        ('D-PAUSE',50,'dobutamine','pause',None,None),
        ('D-RESTART',55,'dobutamine','restart','2.5','mcg/kg/min'),
        ('V-STOP',60,'vasopressin','permanent_stop',None,None),
    ]
    for suffix,minute,drug,event,rate,unit in events:
        at=AT+timedelta(minutes=minute)
        series=replace(code('fs-infusion-'+drug),namespace='clinrx.synthetic.infusion-series/v1')
        delivery=h.DeliveryDetails(rate=quantity(rate,unit),concentration=quantity({'norepinephrine':'0.08','vasopressin':'1','dobutamine':'5'}[drug], 'units/mL' if drug=='vasopressin' else 'mg/mL'),route=concept('Synthetic central venous infusion'),pump=code('fs-pump-'+drug),channel=code('fs-channel-'+drug),infusion=series,dosing_weight_basis='actual',dosing_weight=Reference(kind='circulatory_event',id='fs-WEIGHT',version='1'),attestation=PROV) if rate else None
        if event=='order':action=h.OrderEvent(prescribed=delivery,status=concept('Synthetic prescribed order; not proof of delivery'))
        elif delivery:action=h.InfusionEvent(event_type=event,delivery=delivery)
        else:action=h.InterruptionEvent(event_type=event,reason=concept('Fictional documented interruption; no causal conclusion'),attestation=PROV)
        pump_id='fs-PUMP-RATE-'+suffix
        links=()
        if rate and event!='order':
            pump_rate={'N-START':'3.75','N-CHANGE':'5.25','V-START':'1.8','D-START':'2.1','D-CHANGE':'2.52','N-REDUCE':'4.5','D-RESTART':'2.1'}[suffix]
            records.append(entry(pump_id,'pump_rate',minute,'Source-charted pump volumetric rate, not calculated from the drug dose by ClinRx.',pump_rate,'mL/h',source_identifiers=(series,)))
            links=(h.EvidenceBinding(role='delivery',scope=TARGET,status='resolved',exact=Reference(kind='circulatory_event',id=pump_id,version='1'),provenance=PROV),)
        records.append(h.VasoactiveEvent(**{**fields('fs-'+suffix),'id':'fs-'+suffix,'occurred':stamp(at),'available':stamp(at)},drug=h.VasoactiveIdentity(source=code(drug),canonical_id=drug,mapping='mapped',mapping_provenance=PROV),action=action,source_status=concept('Fictional charted event'),source_identifiers=(series,),associations=links,disclosures=('Fictional example, not a treatment protocol or dosing advice. Dosing weight and pump-rate context retain exact source references when supplied; no conversion or continuous exposure is inferred.',)))
    return tuple(records)


def bootstrap(engine):
    manifest=baseline_bootstrap(engine)
    with transaction(engine) as repo:
        for fact in flowsheet_facts():repo.append_fact(fact,target=TARGET)
    return {**manifest,'dataset':'synthetic-icu-flowsheet/2','flowsheet_enabled':True,'flowsheet_additional_records':len(flowsheet_facts()),'execution_enabled':False}
