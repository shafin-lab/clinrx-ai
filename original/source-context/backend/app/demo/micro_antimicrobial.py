"""Explicit synthetic S/I/U/D bootstrap; never invoked by API startup."""
import argparse
import json
from datetime import timedelta
from pathlib import Path
from app.demo.patient_state import AT, SIMULATION_AT, TARGET, SOURCE, bootstrap as base_bootstrap
from app.models.clinical.common import Binding, ClinicalTime, IdentityVerification, Provenance, Reference, Unit
from app.models.clinical import recorded_v2 as c, microbiology as m, antimicrobials as a
from app.persistence.database import create_database
from app.persistence.repository import transaction

PROV=Provenance(source=SOURCE,actor='synthetic-demo',recorded_at=AT,lineage='unknown',limitations=('Synthetic source assertion only.',))
BIND=Binding(target=TARGET,verification=IdentityVerification(status='verified',method='synthetic-demo',verifier='synthetic-system',assessed_at=AT,source=SOURCE))

def time(at): return c.RecordedTime(status='known',precision='instant',value=at)
def concept(label): return c.RecordedConcept(raw_display=label)
def code(value): return c.SourceCode(namespace='clinrx.synthetic.micro',code=value,version='1',raw_display=value)
def base(id): return dict(id='demo-'+id,revision='1',binding=BIND,origin='reported',provenance=PROV,time=ClinicalTime(precision='unknown'),temporal_status='unknown')
def binding(role,id,kind):
    return c.DomainBinding(role=role,scope=TARGET,status='resolved',stable_target=c.StableIdentity(kind=kind,id='demo-'+id),exact=Reference(kind=kind,id='demo-'+id,version='1'),provenance=PROV)
def drug():
    return a.AntimicrobialIdentity(source_code=code('agent-1'),raw_display='Synthetic antimicrobial',canonical_id='synthetic-agent-1',ingredient_ids=('synthetic-agent-1',),mapping_status='mapped',mapping_provenance=PROV)
def report(): return c.ReportState(status='final',reported=time(AT+timedelta(hours=2)),available=time(AT+timedelta(hours=2)))
def dose(basis): return a.RecordedDose(amount=dict(value='500.00',unit=Unit(raw='mg',status='unresolved',limitation='Source unit.')),basis=basis)

def facts():
    sb=binding('specimen','S','microbiology_specimen'); ib=binding('isolate','I','microbiology_isolate')
    return (
        m.Specimen(**base('S'),accession=code('sample-1'),specimen_type=concept('Synthetic blood specimen'),collected=time(AT),received=time(AT+timedelta(minutes=10))),
        m.IsolateIdentification(**base('I'),domain_bindings=(sb,),report=report(),isolate_identifier=code('isolate-1'),organism=concept('Synthetic recorded organism'),identification_state='final'),
        m.SusceptibilityResult(**base('U'),domain_bindings=(ib,),report=report(),test_identifier=code('test-1'),antimicrobial=drug(),result_status='reported',mic=m.MinimumInhibitoryConcentration(comparator='<=',quantity=dict(value='1.000',unit=Unit(raw='mg/L',status='unresolved',limitation='Source unit.'))),interpretation=m.SusceptibilityInterpretation(raw='I',category='intermediate',coding=code('I'))),
        a.CompletedAntimicrobialAdministration(**base('D'),antimicrobial=drug(),administered_dose=dose('total_administered'),administered=time(AT+timedelta(hours=1)),route=concept('Synthetic route')),
        a.AntimicrobialOrder(**base('O'),antimicrobial=drug(),order_status='active',prescribed_dose=dose('per_dose'),created=time(AT)),
        a.AntimicrobialNonDelivery(**base('N'),antimicrobial=drug(),status='held',occurred=time(AT+timedelta(hours=1)),domain_bindings=(binding('order','O','antimicrobial_order'),)),
        m.DirectExamination(**base('E'),domain_bindings=(sb,),report=report(),examination_type='gram_stain',findings=(m.ExaminationFinding(category='gram_reaction',finding=concept('Synthetic recorded finding'),presence='present'),)),
        m.CultureFinding(**base('C'),domain_bindings=(sb,),report=report(),growth='growth'),
        m.ResistanceFinding(**base('R'),domain_bindings=(ib,),report=report(),category='esbl',target=concept('Synthetic recorded marker'),result='negative'),
        m.MolecularResult(**base('P'),domain_bindings=(sb,),report=report(),test_identifier=code('PCR'),panel_identifier=code('panel-1'),target=concept('Synthetic target'),result='negative'))

def manifest():
    return dict(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,review_start=AT.isoformat(),review_end=(AT+timedelta(hours=2)).isoformat(),simulation_at=SIMULATION_AT.isoformat())

def bootstrap(engine):
    base_bootstrap(engine)
    with transaction(engine) as repo:
        for fact in facts(): repo.append_fact(fact,target=TARGET)
    return manifest()

def correct(engine):
    u=facts()[2]
    corrected=type(u).model_validate({**u.model_dump(),'revision':'2','supersedes':u.reference,'correction_reason':'Explicit synthetic source correction.', 'report':{**u.report.model_dump(),'change':'corrected'}})
    with transaction(engine) as repo: repo.append_revision(corrected,target=TARGET)
    return dict(consumed=u.reference.model_dump(),corrected=corrected.reference.model_dump())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('bootstrap','correct'))
    parser.add_argument('--database',type=Path,required=True)
    args=parser.parse_args()
    if not args.database.is_absolute(): parser.error('absolute disposable database path required')
    engine=create_database(args.database)
    try: print(json.dumps((bootstrap if args.action=='bootstrap' else correct)(engine),sort_keys=True))
    finally: engine.dispose()
if __name__=='__main__': main()
