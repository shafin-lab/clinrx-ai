"""Explicit source-chart entries for the synthetic hemodynamics view only.

Uses existing CirculatoryEvent amount/description/interval fields. These are not
new renal, nutrition or patient-management inference contracts.
"""
from datetime import timedelta
from app.demo.circulatory import fields,stamp,quantity,code,concept,acquisition,PROV,TARGET
from app.demo.patient_state import AT
from app.demo.comprehensive import replace,demo_facts
from app.models.clinical import hemodynamics as h
from app.models.clinical.common import ClinicalTime,Reference
NAMESPACE='clinrx.synthetic.hemodynamic-chart/v1'

def entry(id,tag,minute,text,amount=None,unit=None,start=None,event_type='other',**extra):
    at=AT+timedelta(minutes=minute)
    description=replace(concept(text),coding=replace(code(tag),namespace=NAMESPACE))
    interval=h.RecordedCirculatoryInterval(start=stamp(AT+timedelta(minutes=start)),end=stamp(at),provenance=PROV,limitations=('Source-recorded interval bounds; no duration, rate or completeness assessment is inferred.',)) if start is not None else None
    return h.CirculatoryEvent(**{**fields(id),'id':id,'occurred':stamp(at),'available':stamp(at)},event_type=event_type,description=description,
        recorded_interval=interval,recorded_amount=quantity(amount,unit) if amount is not None else None,
        disclosures=('Fictional source-chart entry for hemodynamic context, not a treatment recommendation or proof of a complete fluid record. Intervals and totals are source-recorded; ClinRx does not recalculate them.',),**extra)

def context_facts():
    records=[entry('fs-WEIGHT','dosing_weight',0,'Source-charted actual dosing weight; not a calculated ideal or adjusted weight.','70','kg')]
    records.append(entry('fs-BSA','body_surface_area',0,'Source-reported BSA for indexing; height and formula are not supplied. ClinRx does not derive BSA from dosing weight.','1.73','m2'))
    groups=[(0,15,'250','0','35','10','0','205'),(15,30,'100','0','25','5','50','20'),(30,45,'50','150','40','0','50','110'),(45,60,'50','0','45','5','50','-50')]
    labels={'input_iv':'Recorded IV fluid input','input_blood':'Recorded blood-product input','output_urine':'Measured urine output','output_drain':'Measured drain output','output_crrt':'Recorded net fluid removal by CRRT','net_balance_reported':'Source-reported balance of charted categories'}
    for start,end,*values in groups:
        for tag,value in zip(labels,values,strict=True):
            records.append(entry('fs-IO-'+tag+'-'+str(end),tag,end,labels[tag]+'. This is the source-recorded interval volume, not an inferred hourly rate. Net balance is a source-reported calculation over the charted categories, not a ClinRx calculation or complete-patient fluid reconciliation.',value,'mL',start=start))
    records.append(entry('fs-URINE-TOTAL','urine_total_reported',60,'Source-reported cumulative urine volume for 08:00–09:00, not a ClinRx sum.','145','mL',start=0))
    records.append(entry('fs-BALANCE-TOTAL','balance_total_reported',60,'Source-reported cumulative balance for the charted categories over 08:00–09:00. Completeness of all intake and losses is not established.','285','mL',start=0))
    originals={f.id:f for f in demo_facts()}
    for minute,crt,temperature,mottling in [(15,'3.0','35.5','Source chart: mottling recorded around knees.'),(30,'2.5','35.8','Source chart: mottling still recorded.'),(45,'2.0','36.0','Source chart: mottling not observed at this assessment.'),(60,'2.0','36.1','Source chart: mottling not observed at this assessment.')]:
        at=AT+timedelta(minutes=minute)
        base=originals['m7-CRT']
        for suffix,concept_id,value,unit in [('CRT','capillary_refill',crt,'s'),('SKIN-TEMP','skin_temperature',temperature,'Cel')]:
            records.append(replace(base,id='fs-'+suffix+'-'+str(minute),occurred=stamp(at),available=stamp(at),concept=concept_id,
                result=h.NumericResult(quantity=quantity(value,unit)),regional_site=concept('Source-charted fingertip' if suffix=='CRT' else 'Source-charted peripheral skin site')))
        records.append(replace(base,id='fs-MOTTLING-'+str(minute),occurred=stamp(at),available=stamp(at),concept='mottling',result=h.QualitativeResult(finding=concept(mottling))))
    for minute in (15,30,45,60):
        template=originals['m7-RHYTHM'];at=AT+timedelta(minutes=minute)
        records.append(replace(template,id='fs-RHYTHM-'+str(minute),occurred=stamp(at),available=stamp(at),result=h.QualitativeResult(finding=concept('Source-reported irregular rhythm; no arrhythmia classification confirmed.' if minute==30 else 'Source-reported sinus rhythm.'))))
    for suffix,concept_id,sample,value,minute in [('SCVO2','scvo2','central_venous','66.0',30),('SVO2','svo2','mixed_venous','64.0',30)]:
        at=AT+timedelta(minutes=minute);template=originals['m7-SVO2']
        context=h.BloodGasContext(collected=stamp(at),provenance=PROV,limitations=('This venous sample has its own collection assertion; oxygen/ventilation settings are not recorded or borrowed from arterial samples.',))
        records.append(replace(template,id='fs-'+suffix+'-'+str(minute),occurred=stamp(at),available=stamp(at),concept=concept_id,sample_type=sample,specimen=code('fs-'+sample+'-sample'),blood_gas_context=context,result=h.NumericResult(quantity=quantity(value,'%'))))
    records.extend([
        entry('fs-GOAL','map_goal',0,'Fictional clinician-recorded MAP goal: 65–75 mmHg for this review. Rationale: individualized source-chart plan. Review at 09:00 UTC. This is not a ClinRx-recommended target and is not used for automatic alerts or titration.'),
        entry('fs-REVIEW','review_note',30,'Fictional clinician review: compare recorded pressures, flow method, perfusion and interval urine output. Infusion events and subsequent observations do not establish cause or treatment response. No automated recommendation.'),
        entry('fs-HANDOVER','handover_note',60,'Fictional hemodynamic handover: retain original infusion identities; CO at 09:00 has suspect source quality; PiCCO quality remains unknown. Review source-chart fluid completeness and source-recorded target. No independent response classification or shock diagnosis established.'),
        entry('fs-FLUID-CHALLENGE','fluid_challenge',10,'Source-charted fluid challenge. The same administration may be included in interval input; do not add its event volume again to the fluid chart. Baseline and subsequent measurements are linked without a response or causality claim.','250','mL',event_type='fluid_challenge'),
        entry('fs-VENT-CHANGE','ventilation_change',30,'Source-charted ventilator review: PEEP documented as 5 cmH2O. Refer to sample-time source context; no setting is carried forward to other samples.',event_type='ventilation_change'),
        entry('fs-CRRT-NOTE','crrt_context',30,'Source chart: CRRT fluid-removal context recorded. Interval rows contain source-recorded NET removal, not total effluent. Replacement fluids are not independently reconciled by ClinRx.',event_type='other'),
    ])
    records.append(h.DynamicAssessment(**{**fields('fs-FLUID-ASSESSMENT'),'id':'fs-FLUID-ASSESSMENT','occurred':stamp(AT+timedelta(minutes=15))},test='fluid_challenge',protocol=code('fictional-source-fluid-challenge'),baseline=(Reference(kind='circulatory_cardiac',id='m7-CO',version='1'),),intervention=(Reference(kind='circulatory_event',id='fs-FLUID-CHALLENGE',version='1'),),subsequent=(Reference(kind='circulatory_cardiac',id='fs-CO-15',version='1'),),ventilation_mode=concept('Source-charted volume assist-control'),rhythm=concept('Source-charted rhythm context; no automatic applicability decision'),position=concept('Source-charted semi-recumbent position'),quality=h.EvidenceQuality(status='unknown',provenance=PROV)))
    return tuple(records)
