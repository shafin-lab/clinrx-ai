"""Composes M6/RF2 at one cutoff; appends manual records, never dose inference."""
from hashlib import sha256
from decimal import Decimal
from app.api.schemas.antibiotic_chart import AntibioticDraft
from app.api.schemas.micro_antimicrobial import MicroStateContext,MicroStateResponse
from app.api.micro_commands import MicroStateCodec
from app.demo.authoring import TARGET,EvidenceConflict
from app.models.clinical import antimicrobials as a
from app.models.clinical.common import Binding,IdentityVerification,Source,ClinicalTime,Provenance,Reference,Unit
from app.models.clinical.recorded_v2 import SourceCode,RecordedConcept,RecordedTime,DomainBinding,StableIdentity
from app.execution.patient_state_v2 import PatientStateScopeV2
from app.execution.patient_state_v2_assembly import AssemblyRequestV2,_assemble
from app.persistence.canonical import canonical_payload
from app.persistence.metadata import RepositoryCutoff
from app.persistence.errors import RecordNotFound,RecordConflict,StorageIntegrityError
from app.persistence.bounded_history import HistoryBudget,HistoryAccounting,AggregateHistoryBudget
from app.persistence.history import FactIdentity
from app.services.renal_fluid_entry_service import RF2Service,exact_json

OWNER='clinrx.local.antibiotic-chart/v1'
KINDS={'antimicrobial_order','antimicrobial_administration','antimicrobial_non_delivery'}
def kind(mode):return 'antimicrobial_order' if mode=='prescription' else 'antimicrobial_administration' if mode=='given' else 'antimicrobial_non_delivery'
def recorded(text):return RecordedTime(status='known',precision='instant',value=text)
def metadata(fact):
    codes=[c for c in getattr(fact,'source_identifiers',()) if c.namespace==OWNER]
    if not codes:return None
    if len(codes)!=1 or codes[0].version!='1':raise StorageIntegrityError('ambiguous antibiotic chart metadata')
    body=AntibioticDraft.model_validate(exact_json(codes[0].code))
    if canonical_payload(build_fact(body))!=canonical_payload(fact):raise StorageIntegrityError('antibiotic chart metadata differs')
    return body

def build_fact(body):
    source=Source(namespace=OWNER,identifier=body.source_record,version='1',channel='clinician')
    prov=Provenance(source=source,actor=body.actor,recorded_at=body.recorded_at,lineage='unknown',limitations=('Manual source record; not a generated regimen or prescribing instruction.',))
    antimicrobial=a.AntimicrobialIdentity(source_code=SourceCode(namespace='clinrx.manual-antibiotic',code=body.medicine,version='1',raw_display=body.medicine),raw_display=body.medicine,formulation=body.product,mapping_status='unknown',mapping_provenance=prov,limitation='Clinician-entered identity and product; terminology equivalence not validated.')
    encoded=canonical_payload(body)
    if len(encoded.encode())>4096:raise ValueError('source metadata exceeds bound')
    fields=dict(id=str(body.id),revision=str(body.revision),binding=Binding(target=TARGET,verification=IdentityVerification(status='verified',method='synthetic encounter binding',verifier=body.actor,assessed_at=body.recorded_at,source=source)),origin='reported',provenance=prov,time=ClinicalTime(recorded=body.recorded_at,precision='unknown'),temporal_status='unknown',source_identifiers=(SourceCode(namespace=OWNER,code=encoded,version='1',raw_display='Manual antibiotic chart request'),),disclosures=('Recorded prescription and completed administration are separate assertions; no exposure or clinical suitability inferred.',),supersedes=body.predecessor.model_dump() if body.predecessor else None,correction_reason=body.correction_reason,antimicrobial=antimicrobial,route=RecordedConcept(raw_display=body.route))
    if body.order:
        ref=Reference.model_validate(body.order.model_dump());fields['domain_bindings']=(DomainBinding(role='order',scope=TARGET,status='resolved',stable_target=StableIdentity(kind=ref.kind,id=ref.id),exact=ref,provenance=prov),)
    if body.mode in ('prescription','given'):
        dose=a.RecordedDose(amount={'value':Decimal(body.amount),'unit':Unit(raw=body.unit,status='unresolved',limitation='Recorded source unit; no conversion performed.')},basis='per_dose' if body.mode=='prescription' else 'total_administered',basis_detail=body.dose_detail)
        if body.mode=='prescription':return a.AntimicrobialOrder(**fields,prescribed_dose=dose,schedule=body.schedule,recorded_indication=body.indication,order_status='active',created=recorded(body.point))
        return a.CompletedAntimicrobialAdministration(**fields,administered_dose=dose,administered=recorded(body.point))
    return a.AntimicrobialNonDelivery(**{k:v for k,v in fields.items() if k!='route'},status=body.mode,occurred=recorded(body.point),recorded_reason=body.indication)

class AntibioticChartService(RF2Service):
    def micro(self,repo,scope):
        request=AssemblyRequestV2(scope=scope,profile_id='SyntheticMicrobiologyAntimicrobialState',profile_version='2')
        assembly=_assemble(repo,request,history_budget=self.history_budget,accounting=self.accounting())
        context=MicroStateContext(assembly_request=request,assembly_digest=assembly.canonical_digest)
        return MicroStateResponse(assembly=assembly,state_context=MicroStateCodec(self.dependencies.config.envelope_signing_key).issue(context))
    def catalog(self,repo,start,end):
        renal=super().catalog(repo,start,end)
        scope=PatientStateScopeV2(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,review_start=start,review_end=end,repository_cutoff=RepositoryCutoff.model_validate(renal['cutoff']))
        micro=self.micro(repo,scope)
        return self.bounded_dict({'version':'SyntheticAntibiotics/v1','renal':renal,'micro':micro.model_dump(mode='json'),'execution_enabled':False})
    def check(self,repo,body):
        self.require_repo(repo,body.repository);fact=build_fact(body)
        if body.predecessor and body.predecessor.kind!=fact.kind:raise EvidenceConflict()
        if body.order:
            order=repo.load_fact(Reference.model_validate(body.order.model_dump()),target=TARGET).fact
            if order.kind!='antimicrobial_order' or order.antimicrobial.raw_display!=body.medicine or order.antimicrobial.formulation!=body.product or not order.route or order.route.raw_display!=body.route:raise EvidenceConflict()
        return fact
    def reply(self,body,status,fact=None,stored=None):
        out={'status':status,'request_canonical':canonical_payload(body),'request_digest':sha256(canonical_payload(body).encode()).hexdigest(),'execution_enabled':False}
        if fact:out.update(fact=fact.model_dump(mode='json'),canonical_fact=canonical_payload(fact),digest=sha256(canonical_payload(fact).encode()).hexdigest(),ingestion=stored.ingestion.model_dump(mode='json') if stored else None)
        return self.bounded_dict(out)
    def action(self,repo,body,action):
        self.require_repo(repo,body.repository);fact=build_fact(body)
        rows=self.history_rows(repo,repo.capture_cutoff(),self.accounting(),fact.reference)
        existing=next((row for row in rows if row.fact.reference==fact.reference),None)
        if existing:
            if canonical_payload(existing.fact)!=canonical_payload(fact):raise EvidenceConflict()
            return self.reply(body,'saved',existing.fact,existing)
        if action=='lookup':return self.reply(body,'absent')
        fact=self.check(repo,body)
        for previous in self.history_rows(repo,repo.capture_cutoff(),self.accounting()):
            if previous.fact.kind not in KINDS or previous.fact.id==fact.id:continue
            previous_body=metadata(previous.fact)
            if previous_body and previous_body.source_record==body.source_record and previous.fact.kind==fact.kind:raise EvidenceConflict()
        rows=repo.list_bounded_history(target=TARGET,cutoff=repo.capture_cutoff(),identity=FactIdentity(kind=fact.kind,id=fact.id),budget=self.history_budget,accounting=self.accounting()).records
        if body.predecessor:
            prior=repo.load_fact(Reference.model_validate(body.predecessor.model_dump()),target=TARGET)
            if not metadata(prior.fact) or sha256(canonical_payload(prior.fact).encode()).hexdigest()!=body.predecessor_digest or not rows or rows[-1].fact.reference!=prior.fact.reference:raise EvidenceConflict()
        elif rows:raise EvidenceConflict()
        if action=='validate':return self.reply(body,'validated',fact)
        try:stored=repo.append_revision(fact,target=TARGET) if body.predecessor else repo.append_fact(fact,target=TARGET)
        except RecordConflict:raise EvidenceConflict() from None
        return self.reply(body,'saved',stored.fact,stored)
    def history(self,repo,body):
        context=MicroStateCodec(self.dependencies.config.envelope_signing_key).verify(body.state_context)
        if context.assembly_request.scope.target!=TARGET:raise EvidenceConflict()
        state=self.micro(repo,context.assembly_request.scope)
        if state.assembly.canonical_digest!=context.assembly_digest:raise StorageIntegrityError('micro snapshot mismatch')
        ref=Reference.model_validate(body.reference.model_dump())
        if not any(i.fact.reference==ref for i in state.assembly.snapshot.items):raise RecordNotFound('source not retained in selected view')
        rows=repo.list_bounded_history(target=TARGET,cutoff=context.assembly_request.scope.repository_cutoff,identity=FactIdentity(kind=ref.kind,id=ref.id),budget=HistoryBudget(max_rows=128),accounting=self.accounting()).records
        return self.bounded_dict({'reference':ref.model_dump(mode='json'),'items':[{'fact':s.fact.model_dump(mode='json'),'canonical_fact':canonical_payload(s.fact),'digest':sha256(canonical_payload(s.fact).encode()).hexdigest(),'ingestion':s.ingestion.model_dump(mode='json')} for s in rows],'execution_enabled':False})
