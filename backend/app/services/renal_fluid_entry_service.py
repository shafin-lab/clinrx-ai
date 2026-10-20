"""Opt-in synthetic RF2 composition. No new clinical fact or execution semantics."""
import json
from decimal import Decimal
from hashlib import sha256
from pydantic import ValidationError
from app.api.schemas.renal_fluid_entry import Chart, RenalNote, SourceReview
from app.demo.authoring import TARGET, EvidenceConflict
from app.models.clinical.hemodynamics import CirculatoryEvent, ClinicalInstant, RecordedCirculatoryInterval, EvidenceBinding
from app.models.clinical.recorded_v2 import SourceCode, ExactQuantity, RecordedConcept
from app.models.clinical.facts import ClinicalObservation
from app.models.clinical.common import Reference
from app.persistence.canonical import canonical_payload
from app.persistence.bounded_history import HistoryBudget, HistoryAccounting, AggregateHistoryBudget
from app.persistence.errors import RecordNotFound, StorageIntegrityError, UnsupportedOperation, QueryLimitExceeded
from app.persistence.history import FactIdentity
from app.services.renal_fluid_product_service import RenalFluidProductService

META='clinrx.local.rf2/v1'; PIN='clinrx.local.rf2.pin/v1'; REVIEW='clinrx.local.rf2.review/v1'
class SourceReviewChanged(EvidenceConflict):
    def __init__(self,body):self.request_digest=sha256(canonical_payload(body).encode()).hexdigest()

CATEGORIES={'input_iv','input_blood','input_oral','input_enteral','output_urine','output_drain','output_other','output_crrt','weight','dosing_weight','net_balance_reported','urine_total_reported','balance_total_reported','fluid_challenge','crrt_context'}
def exact_json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('duplicate member')
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs)
def encoded(namespace,value,label):
    code=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if len(code.encode())>4096:raise QueryLimitExceeded('RF2 metadata exceeds carrier budget')
    return SourceCode(namespace=namespace,version='1',code=code,raw_display=label)
def metadata(fact):
    entries=[x for x in getattr(fact,'external_evidence',()) if x.namespace==META]
    if not entries:return None
    if len(entries)!=1 or entries[0].version!='1':raise StorageIntegrityError('ambiguous RF2 metadata')
    try:
        d=exact_json(entries[0].code)
        if set(d)!= {'version','chart','note'} or d['version']!=1:raise ValueError()
        chart=Chart.model_validate(d['chart']) if d['chart'] is not None else None
        if d['note'] is not None:
            if d['note'].get('pins')!=[]:raise ValueError()
            pin_entries=[x for x in getattr(fact,'external_evidence',()) if x.namespace==PIN]
            if any(x.version!='1' for x in pin_entries):raise ValueError()
            d['note']={**d['note'],'pins':[exact_json(x.code) for x in pin_entries]}
        note=RenalNote.model_validate(d['note']) if d['note'] is not None else None
        if note and {(a.exact.kind,a.exact.id,a.exact.version) for a in fact.associations if a.role=='context' and a.status=='resolved'}!={(p.reference.kind,p.reference.id,p.reference.version) for p in note.pins}:raise ValueError()
        if (chart is None)==(note is None):raise ValueError()
        if chart:
            q=fact.recorded_amount
            if (q is None)!=(chart.amount is None) or (q is not None and (str(q.value)!=chart.amount or q.unit.raw!=chart.unit)):raise ValueError()
            if fact.occurred.source_timestamp!=chart.point:raise ValueError()
            interval=fact.recorded_interval
            if chart.start is not None or chart.end is not None:
                if interval is None or interval.start.source_timestamp!=chart.start or interval.end.source_timestamp!=chart.end:raise ValueError()
            elif interval is not None:raise ValueError()
        review_entries=[x for x in getattr(fact,'external_evidence',()) if x.namespace==REVIEW]
        if review_entries:
            if not note or len(review_entries)!=len(note.pins) or any(x.version!='1' for x in review_entries):raise ValueError()
            reviews=[SourceReview.model_validate(exact_json(x.code)) for x in review_entries]
            if any(v.selected!=p.reference or v.terminal_ingestion<p.ingestion or (v.selected==v.terminal and (v.terminal_digest!=p.digest or v.terminal_ingestion!=p.ingestion)) or ((v.selected!=v.terminal or v.record_status not in (None,'recorded')) and not v.retain_historical) for v,p in zip(reviews,note.pins)):raise ValueError()
            d['source_review']=[v.model_dump(mode='json') for v in reviews]
        if note:
            expected='Clinician-authored renal/fluid reassessment; not a generated clinical conclusion.\n'+'\n'.join(k+': '+getattr(note,k) for k in ('question','findings','possibilities','gaps','plan'))
            if fact.description.raw_display!=expected or len(fact.associations)!=len(note.pins):raise ValueError()
        return d
    except (ValueError,ValidationError,TypeError):raise StorageIntegrityError('invalid RF2 metadata') from None

def category(fact):
    m=metadata(fact)
    if m:return m['chart']['category'] if m['chart'] else 'note'
    if isinstance(fact,CirculatoryEvent):
        c=fact.description.coding
        if c and c.namespace=='clinrx.synthetic.hemodynamic-chart/v1' and c.code in CATEGORIES:return c.code
    return None

def material(chart):
    d=chart.model_dump(mode='json');d.pop('new_collection_reason',None)
    return d

def time(text):
    return ClinicalInstant.model_validate({'timestamp_precision':'M7ExactTimestampInput/v1','recorded':{'status':'known','precision':'instant','value':text},'source_timestamp':text,'clock':'unknown'}) if text else ClinicalInstant()

def allowed(fact):
    return (isinstance(fact,ClinicalObservation) and fact.concept_id in ('synthetic-serum-creatinine','body-weight')) or isinstance(fact,CirculatoryEvent) or fact.kind.startswith('circulatory_')

class RF2Service(RenalFluidProductService):
    def accounting(self):return HistoryAccounting(self.aggregate_budget)
    def require_repo(self,repo,repository):
        self.require_closed()
        if repo.capture_cutoff().repository_id!=repository:raise EvidenceConflict()
    def history_rows(self,repo,cutoff,accounting,reference=None):
        return repo.list_bounded_history(target=TARGET,cutoff=cutoff,budget=self.history_budget,accounting=accounting,identity=FactIdentity(kind=reference.kind,id=reference.id) if reference else None).records
    def pin_record(self,repo,pin,accounting):
        self.require_repo(repo,pin.repository)
        now=repo.capture_cutoff()
        if pin.cutoff>now.fact_watermark:raise EvidenceConflict()
        cutoff=now.model_copy(update={'fact_watermark':pin.cutoff})
        rows=self.history_rows(repo,cutoff,accounting,pin.reference)
        found=[x for x in rows if x.fact.reference==pin.reference]
        if len(found)!=1:raise RecordNotFound('exact revision unavailable')
        s=found[0]
        if not allowed(s.fact) or s.ingestion.ingestion_sequence!=pin.ingestion or sha256(canonical_payload(s.fact).encode()).hexdigest()!=pin.digest:raise EvidenceConflict()
        return s
    def evidence(self,repo,stored,cutoff,accounting):
        terminal=self.history_rows(repo,cutoff,accounting,stored.fact.reference)[-1]
        f=stored.fact
        return {'repository':str(cutoff.repository_id),'fact':f.model_dump(mode='json'),'canonical_fact':canonical_payload(f),'digest':sha256(canonical_payload(f).encode()).hexdigest(),'ingestion':stored.ingestion.model_dump(mode='json'),'cutoff':cutoff.fact_watermark,'terminal_reference':terminal.fact.reference.model_dump(),'superseded':terminal.fact.reference!=f.reference,'metadata':metadata(f)}
    def resolve(self,repo,body):
        self.require_repo(repo,body.repository);accounting=self.accounting();out=[]
        for p in body.pins:
            s=self.pin_record(repo,p,accounting)
            out.append(self.evidence(repo,s,repo.capture_cutoff(),accounting))
        return self.bounded_dict({'repository':str(body.repository),'items':out,'execution_enabled':False})
    def history(self,repo,body):
        self.require_repo(repo,body.repository)
        if any(p.repository!=body.repository for p in body.pins):raise EvidenceConflict()
        if len(body.pins)!=1:raise UnsupportedOperation('select one exact history')
        a=self.accounting();p=body.pins[0];self.pin_record(repo,p,a)
        cutoff=repo.capture_cutoff().model_copy(update={'fact_watermark':p.cutoff})
        rows=self.history_rows(repo,cutoff,a,p.reference)
        if len(rows)>128:raise QueryLimitExceeded('history family limit')
        return self.bounded_dict({'repository':str(body.repository),'selected':p.model_dump(mode='json'),'items':[self.evidence(repo,x,cutoff,a) for x in rows],'execution_enabled':False})
    def bounded_dict(self,v):
        if len(json.dumps(v,ensure_ascii=False).encode())>self.dependencies.config.max_response_bytes:raise QueryLimitExceeded('response budget exceeded')
        return v
    def catalog(self,repo,start=None,end=None):
        self.require_closed();cutoff=repo.capture_cutoff();a=self.accounting();rows=self.history_rows(repo,cutoff,a)
        terminals={}
        for s in rows:terminals[(s.fact.kind,s.fact.id)]=s
        from datetime import datetime
        from app.execution.patient_state_v3 import PatientStateScopeV3
        start=start or datetime.fromisoformat('2026-10-08T08:00:00+00:00');end=end or datetime.fromisoformat('2026-10-08T10:00:00+00:00')
        self.window(start,end)
        scope=PatientStateScopeV3(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id,review_start=start,review_end=end,repository_cutoff=cutoff)
        base=self.build(repo,scope,a)
        # Source ownership remains explicit; generic weights are read-only.
        selected=[s for s in terminals.values() if category(s.fact) or s.fact.kind in ('circulatory_pressure','circulatory_cardiac','circulatory_lactate','circulatory_oxygen','circulatory_perfusion','circulatory_vasoactive') or (isinstance(s.fact,ClinicalObservation) and s.fact.concept_id in ('body-weight','synthetic-serum-creatinine'))]
        base_keys={(i.fact.kind,i.fact.id,i.fact.revision) for i in base.circulatory.assembly.snapshot.items}|{(i.fact.kind,i.fact.id,i.fact.revision) for i in base.laboratory.observations}
        extras=[s for s in selected if (s.fact.kind,s.fact.id,s.fact.revision) not in base_keys]
        return self.bounded_dict({'repository':str(cutoff.repository_id),'cutoff':cutoff.model_dump(mode='json'),'combined':base.model_dump(mode='json'),'items':[self.evidence(repo,s,cutoff,a) for s in extras],'execution_enabled':False})
    def source_review(self,repo,body,a):
        now=repo.capture_cutoff();out=[]
        for p in body.note.pins:
            self.pin_record(repo,p,a)
            terminal=self.history_rows(repo,now,a,p.reference)[-1]
            out.append(SourceReview(selected=p.reference,terminal=terminal.fact.reference,terminal_digest=sha256(canonical_payload(terminal.fact).encode()).hexdigest(),terminal_ingestion=terminal.ingestion.ingestion_sequence,record_status=getattr(terminal.fact,'record_status',None)))
        return tuple(out)
    def require_review(self,repo,body,a):
        current=self.source_review(repo,body,a)
        if body.source_review is None:raise UnsupportedOperation('review current selected-source status before saving')
        for accepted,latest in zip(body.source_review,current,strict=True):
            if accepted.model_copy(update={'retain_historical':False})!=latest:raise SourceReviewChanged(body)
            if (latest.selected!=latest.terminal or latest.record_status not in (None,'recorded')) and not accepted.retain_historical:raise EvidenceConflict()
        return body.source_review
    def require_owner(self,repo,body,a):
        if body.predecessor and metadata(self.pin_record(repo,body.predecessor,a).fact) is None:
            raise UnsupportedOperation('use the original source owner for this correction')
    def build_fact(self,repo,body,a):
        self.require_repo(repo,body.repository)
        predecessor=self.pin_record(repo,body.predecessor,a) if body.predecessor else None
        if predecessor and predecessor.fact.record_status!='recorded':raise UnsupportedOperation('withdrawn/invalid correction requires original owner')
        if body.note:
            for pin in body.note.pins:self.pin_record(repo,pin,a)
        at=body.recorded_at
        prov={'source':{'namespace':'clinrx.local.synthetic.rf2','identifier':str(body.id),'channel':'clinician'},'actor':body.actor,'recorded_at':at,'lineage':'incomplete','limitations':['Unauthenticated local synthetic source assertion.']}
        data=predecessor.fact.model_dump(mode='json') if predecessor else {'kind':'circulatory_event','id':str(body.id),'revision':str(body.revision),'contract_version':'3','binding':{'target':TARGET.model_dump(),'verification':{'status':'unresolved','method':'Synthetic scope selection','verifier':body.actor,'assessed_at':at,'source':prov['source'],'ambiguity':'Local synthetic patient only.'}},'origin':'reported','time':{'precision':'unknown'},'verification':'unverified','conflict':'unknown','temporal_status':'unknown','record_status':'recorded','event_type':'other'}
        if predecessor:
            oldcat=category(predecessor.fact)
            if (body.note is not None)!=(oldcat=='note') or (body.chart and body.chart.category!=('weight' if oldcat=='dosing_weight' else oldcat)):raise EvidenceConflict()
        data.update(id=str(body.id),revision=str(body.revision),provenance=prov,supersedes=body.predecessor.reference.model_dump() if predecessor else None,correction_reason=body.reason)
        entries=[x for x in getattr(predecessor.fact,'external_evidence',()) if x.namespace not in (META,PIN,REVIEW)] if predecessor else []
        if body.chart:
            c=body.chart;prior=metadata(predecessor.fact) if predecessor else None
            if prior and prior['chart']['source_record']!=c.model_dump(mode='json')['source_record']:raise EvidenceConflict()
            if predecessor and not prior and c.source_record is not None:raise UnsupportedOperation('cannot assign upstream identity to historical record')
            data.update(recorded_amount=ExactQuantity(value=Decimal(c.amount),unit={'raw':c.unit,'status':'unresolved','limitation':'Raw source unit; no conversion.'}).model_dump(mode='json') if c.amount is not None else None,**({'occurred':time(c.point).model_dump(mode='json')} if not prior or prior['chart']['point']!=c.point else {}))
            # Retained legacy commands reconstruct their original bytes for lookup only.
            # New cross-owner amendments are rejected before append. RF2-owned availability is not editable.
            if not predecessor or prior is None:data['available']=time(None).model_dump(mode='json')
            if c.start is not None or c.end is not None:
                if not prior or (prior['chart']['start'],prior['chart']['end'])!=(c.start,c.end):
                    data['recorded_interval']=RecordedCirculatoryInterval(start=predecessor.fact.recorded_interval.start if prior and predecessor.fact.recorded_interval and prior['chart']['start']==c.start else time(c.start),end=predecessor.fact.recorded_interval.end if prior and predecessor.fact.recorded_interval and prior['chart']['end']==c.end else time(c.end),provenance=prov,limitations=('Source bounds only; no calculated rate or duration.',)).model_dump(mode='json')
            else:data.pop('recorded_interval',None)
            if not predecessor:data['description']=RecordedConcept(raw_display=c.source_context,coding=SourceCode(namespace=META,code=c.category,version='1',raw_display=c.category)).model_dump(mode='json')
            data['uncertainty']=[c.uncertainty]
        else:
            n=body.note
            narrative='Clinician-authored renal/fluid reassessment; not a generated clinical conclusion.\n'+'\n'.join(k+': '+getattr(n,k) for k in ('question','findings','possibilities','gaps','plan'))
            data['description']=RecordedConcept(raw_display=narrative,coding=SourceCode(namespace=META,code='note',version='1',raw_display='Authored renal review')).model_dump(mode='json')
            entries.extend(encoded(PIN,p.model_dump(mode='json'),'Exact reviewed evidence') for p in n.pins)
            if body.source_review is not None:entries.extend(encoded(REVIEW,v.model_dump(mode='json'),'Explicit selected-source review decision') for v in body.source_review)
            data['associations']=[EvidenceBinding(role='context',scope=TARGET,status='resolved',exact=p.reference,provenance=prov).model_dump(mode='json') for p in n.pins]
            data['uncertainty']=[n.gaps];data['occurred']=time(at).model_dump(mode='json')
        meta={'version':1,'chart':body.chart.model_dump(mode='json') if body.chart else None,'note':body.note.model_dump(mode='json') if body.note else None}
        if body.note:meta['note']['pins']=[]
        entries.append(encoded(META,meta,'Structured RF2 source assertions'))
        data['external_evidence']=[e.model_dump(mode='json') for e in entries]
        return CirculatoryEvent.model_validate(data)
    def replay(self,repo,body,a):
        if not body.chart or not body.chart.source_record or body.predecessor:return None
        target=body.chart.source_record.model_dump(mode='json');rows=self.history_rows(repo,repo.capture_cutoff(),a)
        matches=[];owners=set()
        for s in rows:
            m=metadata(s.fact)
            if m and m['chart'] and m['chart']['source_record']==target:
                owners.add((s.fact.kind,s.fact.id))
                if material(Chart.model_validate(m['chart']))==material(body.chart):matches.append(s)
        if len(owners)>1:raise EvidenceConflict()
        if not owners:return None
        if len(matches)!=1:raise EvidenceConflict()
        return matches[0]
    def save(self,repo,body):
        a=self.accounting();fact=self.build_fact(repo,body,a)
        # Exact original-command idempotency is checked independently of source replay.
        retained=self.history_rows(repo,repo.capture_cutoff(),a,fact.reference)
        old=next((s for s in retained if s.fact.reference==fact.reference),None)
        if old:
            if canonical_payload(old.fact)!=canonical_payload(fact):raise EvidenceConflict()
            return self.result(repo,body,old,a,'saved')
        self.require_owner(repo,body,a)
        if body.note:self.require_review(repo,body,a)
        replay=self.replay(repo,body,a)
        if replay:return self.result(repo,body,replay,a,'source_replay')
        stored=repo.append_revision(fact,target=TARGET) if fact.supersedes else repo.append_fact(fact,target=TARGET)
        return self.result(repo,body,stored,a,'saved')
    def result(self,repo,body,stored,a,status):
        return self.bounded_dict({'status':status,'request_digest':sha256(canonical_payload(body).encode()).hexdigest(),'request_canonical':canonical_payload(body),'evidence':self.evidence(repo,stored,repo.capture_cutoff(),a),'execution_enabled':False})
    def validate(self,repo,body):
        a=self.accounting();fact=self.build_fact(repo,body,a);self.require_owner(repo,body,a);replay=self.replay(repo,body,a)
        review=self.require_review(repo,body,a) if body.note and body.source_review is not None else self.source_review(repo,body,a) if body.note else None
        return self.bounded_dict({**({'source_review':[v.model_dump(mode='json') for v in review]} if review is not None else {}),'status':'validated','request_digest':sha256(canonical_payload(body).encode()).hexdigest(),'request_canonical':canonical_payload(body),'fact':fact.model_dump(mode='json'),'replay_reference':replay.fact.reference.model_dump() if replay else None,'execution_enabled':False})
    def lookup(self,repo,body):
        a=self.accounting();fact=self.build_fact(repo,body,a)
        retained=self.history_rows(repo,repo.capture_cutoff(),a,fact.reference)
        stored=next((s for s in retained if s.fact.reference==fact.reference),None)
        if stored is None:
            replay=self.replay(repo,body,a)
            return self.result(repo,body,replay,a,'source_replay') if replay else {'status':'absent','request_digest':sha256(canonical_payload(body).encode()).hexdigest(),'request_canonical':canonical_payload(body),'execution_enabled':False}
        if canonical_payload(stored.fact)!=canonical_payload(fact):raise EvidenceConflict()
        return self.result(repo,body,stored,a,'saved')
