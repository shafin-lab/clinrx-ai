"""M10 transactional source authoring and explicitly bounded exposure projections."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from hashlib import sha256
import base64
import hmac
import json
from uuid import uuid5,UUID
from types import SimpleNamespace
from sqlalchemy import text
from pydantic import TypeAdapter
from app.api.schemas.common import AwareTimestamp
from app.demo.authoring import TARGET, EvidenceConflict
from app.models.clinical.common import Binding,IdentityVerification,Source,ClinicalTime,Provenance,Reference
from app.models.clinical.transfusion import M10_FACTS,M10Fact,M10Time,DeliveryData,VetData,EvidencePin
from app.persistence.canonical import canonical_payload
from app.persistence.bounded_history import HistoryBudget
from app.persistence.history import FactIdentity
from app.persistence.errors import RecordNotFound,RecordConflict,QueryLimitExceeded
from app.services.renal_fluid_entry_service import RF2Service

OWNER='clinrx.local.m10/v1'
DELIVERY={'transfusion_administration','haemostatic_medication_course'}

def stamp(s):return TypeAdapter(AwareTimestamp).validate_python(s) if s else None
def key(ref):return ref.kind,ref.id,ref.version
def digest(fact):return sha256(canonical_payload(fact).encode()).hexdigest()
def point(t):return stamp(t.value) if t.status=='known' and t.precision=='instant' else None

def available(fact,end):
    if isinstance(fact,M10Fact):return point(fact.available) is not None and point(fact.available)<=end
    from app.models.clinical.respiratory import RespiratoryRecord
    if isinstance(fact,RespiratoryRecord):
        t=fact.times.available
        return t.status=='known' and t.precision=='instant' and t.value is not None and t.value<=end
    from app.models.clinical.laboratory import LaboratoryReport
    if isinstance(fact,LaboratoryReport):
        t=fact.times.available
        return t.status=='known' and t.precision=='instant' and t.value is not None and t.value<=end
    t=fact.time.recorded or fact.provenance.recorded_at
    return t is not None and t<=end

def build_fact(body,data=None):
    src=Source(namespace=body.source_issuer,identifier=body.source_record,version=str(body.revision),channel='clinician')
    prov=Provenance(source=src,actor=body.actor,recorded_at=body.recorded_at,lineage='unknown',limitations=('Synthetic source recording; no clinical order transmission.',))
    return M10_FACTS[body.kind](id=str(body.id),revision=str(body.revision),binding=Binding(target=TARGET,verification=IdentityVerification(status='verified',method='synthetic encounter binding',verifier=body.actor,assessed_at=body.recorded_at,source=src)),origin='reported',provenance=prov,time=ClinicalTime(recorded=body.recorded_at,precision='unknown'),temporal_status='unknown',supersedes=body.predecessor.model_dump() if body.predecessor else None,correction_reason=body.correction_reason,source_issuer=body.source_issuer,source_record=body.source_record,available=M10Time(status='known',precision='instant',value=body.available_at) if body.available_at else M10Time(status='unknown'),data=data or body.data)

def amount_key(d,a):return d.product.family,d.product.preparation,a.dimension,a.unit,a.basis

def received_totals(records,start,end):
    """Known subtotals only; unresolved coverage excludes the affected component."""
    facts={key(r.fact.reference):r.fact for r in records};deliveries={k:f for k,f in facts.items() if f.kind in DELIVERY and f.data.record_status=='recorded' and f.data.status!='not_given'}
    excluded={}; covered=set(); conflicts=[]; representations=[]
    for f in facts.values():
        if f.kind!='transfusion_coverage_link' or f.data.record_status!='recorded':continue
        d=f.data;refs=[d.aggregate,*d.constituents];valid=all(key(p.reference) in deliveries and digest(deliveries[key(p.reference)])==p.digest for p in refs)
        involved=[k for k in deliveries if any(k[:2]==key(p.reference)[:2] for p in refs)]
        if not valid:
            for k in involved:excluded[k]='Reconciliation pins changed or unavailable'
            conflicts.append({'reference':f.reference.model_dump(),'reason':'Reconciliation requires review after source change'})
        elif d.relationship=='possible_overlap':
            for k in involved:excluded[k]='Possible aggregate overlap; combined amount indeterminate'
        elif d.relationship=='fully_explained_by_constituents':covered.add(key(d.aggregate.reference));representations.append({'aggregate':d.aggregate.reference.model_dump(),'representation':'constituents'})
        else:
            covered.update(key(p.reference) for p in d.constituents);representations.append({'aggregate':d.aggregate.reference.model_dump(),'representation':'aggregate','constituents':len(d.constituents)})
    # A source aggregate and individual episodes in the same review period can
    # describe the same delivery. Require an explicit coverage assertion before
    # certifying a combined amount; a timestamp match alone establishes nothing.
    reconciled=set()
    for f in facts.values():
        if f.kind=='transfusion_coverage_link' and f.data.record_status=='recorded':
            reconciled.update((key(f.data.aggregate.reference),key(p.reference)) for p in f.data.constituents)
    for ak,aggregate in deliveries.items():
        if aggregate.data.grain!='reported_aggregate':continue
        at=point(aggregate.data.occurred)
        if at is not None and not start<=at<end:continue
        for ck,component in deliveries.items():
            if ck==ak or ck in covered or ak in covered or component.data.grain=='reported_aggregate':continue
            ct=point(component.data.occurred)
            if ct is not None and not start<=ct<end:continue
            if (aggregate.data.product.family,aggregate.data.product.preparation)==(component.data.product.family,component.data.product.preparation) and (ak,ck) not in reconciled:
                excluded[ak]='Aggregate and individual records may overlap; reconcile before combining'
                excluded[ck]='Aggregate and individual records may overlap; reconcile before combining'
    groups={};unknown=[];included=[];spanning=[]
    identities=defaultdict(list)
    for k,f in deliveries.items():identities[(f.kind,f.data.delivery_id)].append(k)
    for duplicate in identities.values():
        if len(duplicate)>1:
            for k in duplicate:excluded[k]='Unreconciled duplicate delivery identity'
    for k,f in deliveries.items():
        d=f.data
        if k in covered:continue
        if k in excluded:
            unknown.append({'reference':f.reference.model_dump(),'reason':excluded[k]});continue
        if d.completed_as:
            target=facts.get(key(d.completed_as.reference))
            if target is None or digest(target)!=d.completed_as.digest:
                unknown.append({'reference':f.reference.model_dump(),'reason':'Completed medication source changed or unavailable'});continue
        event=point(d.occurred);begin=point(d.started);finish=point(d.ended)
        if begin and finish and begin<end and finish>=start and (begin<start or finish>=end):
            spanning.append({'reference':f.reference.model_dump(),'reason':'Spanning exposure; cumulative quantities cannot be allocated within interval','amounts':[a.model_dump() for a in d.amounts]});continue
        if event is None:event=finish
        if event is None:
            unknown.append({'reference':f.reference.model_dump(),'reason':'Exact clinical time unavailable'});continue
        if not start<=event<end:continue
        included.append(f.reference.model_dump())
        if d.status=='unknown':unknown.append({'reference':f.reference.model_dump(),'reason':'Administration status uncertain'});continue
        if not d.amounts:unknown.append({'reference':f.reference.model_dump(),'reason':d.missing_amount_reason or 'Delivered amount missing'})
        elif not any(a.dimension=='volume' for a in d.amounts):unknown.append({'reference':f.reference.model_dump(),'reason':'Actual administered volume not documented; other known quantities retained','dimension':'volume'})
        for a in d.amounts:
            group=amount_key(d,a)
            if group not in groups:groups[group]={'family':group[0],'preparation':group[1],'dimension':group[2],'unit':group[3],'basis':group[4],'known_subtotal':Decimal(0),'records':[],'status_subtotals':defaultdict(Decimal)}
            out=groups[group];out['known_subtotal']+=Decimal(a.value);out['status_subtotals'][d.status]+=Decimal(a.value);out['records'].append(f.reference.model_dump())
    result=[]
    for g in groups.values():
        result.append({**g,'known_subtotal':format(g['known_subtotal'],'f'),'status_subtotals':{k:format(v,'f') for k,v in g['status_subtotals'].items()}})
    return {'groups':result,'complete':not unknown and not spanning and not conflicts,'has_records':bool(deliveries),'excluded':unknown,'spanning':spanning,'conflicts':conflicts,'representations':representations,'input_references':included,'period':{'start':start.isoformat(),'end':end.isoformat(),'boundary':'[start,end)'},'scope':'selected interval; admission total requires admission interval'}

class TransfusionService(RF2Service):
    def rows(self,repo,cutoff=None,reference=None):
        return repo.list_bounded_history(target=TARGET,cutoff=cutoff or repo.capture_cutoff(),budget=HistoryBudget(max_rows=4096,max_payload_bytes=16777216),identity=FactIdentity(kind=reference.kind,id=reference.id) if reference else None).records
    def evidence_item(self,s):return {'fact':s.fact.model_dump(mode='json'),'canonical_fact':canonical_payload(s.fact),'digest':digest(s.fact),'ingestion':s.ingestion.model_dump(mode='json')}
    def snapshot(self,repo,end,cutoff=None):
        selected={}
        for s in self.rows(repo,cutoff):
            if available(s.fact,end):selected[(s.fact.kind,s.fact.id)]=s
        return list(selected.values())
    def catalog(self,repo,start,end,cutoff=None):
        self.require_closed();start=stamp(start);end=stamp(end)
        if start>=end:raise ValueError('ordered nonempty review interval required')
        captured=repo.capture_cutoff()
        if cutoff is not None:
            if cutoff>captured.fact_watermark:raise EvidenceConflict()
            captured=captured.model_copy(update={'fact_watermark':cutoff})
        rows=self.snapshot(repo,end,captured)
        # Unknown availability is visible but never becomes eligible at a past cutoff.
        unknown=[]
        if cutoff is None:
            terminal={}
            for s in self.rows(repo,captured):terminal[(s.fact.kind,s.fact.id)]=s
            unknown=[self.evidence_item(s) for s in terminal.values() if isinstance(s.fact,M10Fact) and point(s.fact.available) is None]
            # A terminal correction with unknown availability cannot certify the
            # older positive assertion as current. Withhold both source owners;
            # retain the correction visibly and keep historical cutoffs intact.
            uncertain={(x['fact']['kind'],x['fact']['id']) for x in unknown}
            uncertain.update(('medication_administration',str(uuid5(UUID(x['fact']['id']),'completed-medication'))) for x in unknown if x['fact']['kind']=='haemostatic_medication_course')
            rows=[s for s in rows if (s.fact.kind,s.fact.id) not in uncertain]
        m10=[s for s in rows if s.fact.kind in M10_FACTS]
        evidence=[s for s in rows if s.fact.kind in ('laboratory_report','respiratory_record','medication_administration','medication_order','circulatory_event')]
        out={'version':'SyntheticM10/v1','repository':str(captured.repository_id),'cutoff':captured.model_dump(mode='json'),'patient_id':TARGET.patient_id,'encounter_id':TARGET.encounter_id,'review_start':start.isoformat(),'review_end':end.isoformat(),'items':[self.evidence_item(s) for s in m10],'unknown_availability':unknown,'totals':received_totals(rows,start,end),'evidence':[self.evidence_item(s) for s in evidence],'medication_exposures':self.medication_exposures(rows),'retracted_medication_exposures':self.retracted_medications(rows),'fluid_reconciliation':self.fluid_projection(rows),'complete':True,'execution_enabled':False}
        encounter=repo.load_encounter(patient_id=TARGET.patient_id,encounter_id=TARGET.encounter_id)
        admission=encounter.time.effective_start or encounter.time.event
        out['summaries']={'selected_interval':out['totals'],'last_24_hours':received_totals(rows,end-timedelta(hours=24),end),'admission':received_totals(rows,admission,end) if admission and admission<end else {'complete':False,'reason':'Admission start not recorded; no inferred admission total'}}
        if unknown:
            exclusions=[{'reference':{'kind':x['fact']['kind'],'id':x['fact']['id'],'version':x['fact']['revision']},'reason':'Availability unknown'} for x in unknown]
            for summary in out['summaries'].values():
                summary['complete']=False
                summary.setdefault('excluded',[]).extend(exclusions)
            out['fluid_reconciliation']['complete']=False
            out['fluid_reconciliation']['excluded']=exclusions
        return self.bounded_dict(out)
    def retracted_medications(self,rows):
        retracted={key(s.fact.data.retracted_medication.reference) for s in rows if s.fact.kind=='haemostatic_medication_course' and s.fact.data.retracted_medication}
        return [{'owner':'medication_administration','item':self.evidence_item(s),'reason':'Completed-delivery assertion retracted by an exact M10 source correction; historical dose is not counted'} for s in rows if s.fact.kind=='medication_administration' and key(s.fact.reference) in retracted]
    def medication_exposures(self,rows):
        retracted={key(s.fact.data.retracted_medication.reference) for s in rows if s.fact.kind=='haemostatic_medication_course' and s.fact.data.retracted_medication}
        out=[]
        for s in rows:
            f=s.fact
            if f.kind=='medication_administration' and key(f.reference) not in retracted:out.append({'owner':'medication_administration','item':self.evidence_item(s)})
            elif f.kind=='haemostatic_medication_course' and f.data.record_status=='recorded' and f.data.status!='not_given' and not f.data.completed_as:out.append({'owner':'haemostatic_medication_course','item':self.evidence_item(s)})
        return out
    def fluid_projection(self,rows):
        byref={key(s.fact.reference):s.fact for s in rows};links=[]
        for s in rows:
            f=s.fact
            if f.kind!='fluid_administration_link' or f.data.record_status!='recorded':continue
            d=f.data;valid=all(key(p.reference) in byref and digest(byref[key(p.reference)])==p.digest for p in (d.administration,d.fluid))
            links.append({'reference':f.reference.model_dump(),'administration':d.administration.reference.model_dump(),'fluid':d.fluid.reference.model_dump(),'status':'linked_once' if valid and d.relationship=='same_delivery' else 'unresolved','matched_volume_ml':d.matched_volume_ml,'reason':None if valid else 'Source changed or unavailable; reconciliation requires review'})
        linked={tuple(x['administration'][k] for k in ('kind','id','version')) for x in links if x['status']=='linked_once'}
        unlinked=[s.fact.reference.model_dump() for s in rows if s.fact.kind in DELIVERY and s.fact.data.record_status=='recorded' and s.fact.data.status!='not_given' and any(a.dimension=='volume' for a in s.fact.data.amounts) and key(s.fact.reference) not in linked]
        return {'links':links,'unlinked_administrations':unlinked,'complete':not unlinked and all(x['status']=='linked_once' for x in links),'accounting_owner':'existing fluid record; M10 linked volume is not added again'}
    def check_pin(self,repo,pin,rows,require_terminal=True):
        matches=[r for r in rows if r.fact.reference==pin.reference]
        if not matches:raise RecordNotFound('exact source pin unavailable in this patient')
        found=matches[0]
        if digest(found.fact)!=pin.digest:raise EvidenceConflict()
        if require_terminal:
            terminal=[r for r in rows if (r.fact.kind,r.fact.id)==(pin.reference.kind,pin.reference.id)][-1]
            if terminal.fact.reference!=pin.reference:raise EvidenceConflict()
        if pin.component_id:
            d=getattr(found.fact,'data',None)
            if isinstance(d,VetData) and pin.component_id not in {x.id for x in d.observations}:raise EvidenceConflict()
        return found.fact
    def pins(self,data):
        result=list(data.linked_sources)
        for name in ('completed_as','retracted_medication','reassesses','aggregate','administration','fluid'):
            value=getattr(data,name,None)
            if value:result.append(value)
        result.extend(getattr(data,'implicated',()))
        if hasattr(data,'relationship') and hasattr(data,'aggregate'):result.extend(data.constituents)
        return result
    def check_data(self,repo,fact,rows):
        d=fact.data
        for p in self.pins(d):
            if p.reference==fact.reference:raise EvidenceConflict()
            self.check_pin(repo,p,rows)
        if isinstance(d,DeliveryData):
            if d.status in ('completed','stopped'):
                for t in (d.occurred,d.ended):
                    if point(t) and point(t)>fact.provenance.recorded_at:raise EvidenceConflict()
            if d.completed_as:
                target=self.check_pin(repo,d.completed_as,rows)
                expected_id=str(uuid5(UUID(fact.id),'completed-medication'))
                if target.kind!='medication_administration' or target.id!=expected_id or not d.promote_to_medication:raise EvidenceConflict()
                doses=[a for a in d.amounts if a.dimension=='dose']
                if len(doses)!=1 or target.administered_dose.amount.value!=Decimal(doses[0].value) or target.administered_dose.amount.unit.raw!=doses[0].unit or target.administered_at!=(point(d.occurred) or point(d.ended)):raise EvidenceConflict()
            for r in rows:
                if r.fact.kind in DELIVERY and r.fact.id!=fact.id and r.fact.data.delivery_id==d.delivery_id:raise EvidenceConflict()
        if isinstance(d,DeliveryData) and d.retracted_medication:
            target=self.check_pin(repo,d.retracted_medication,rows)
            if target.kind!='medication_administration' or target.id!=str(uuid5(UUID(fact.id),'completed-medication')) or target.conflict!='unresolved':raise EvidenceConflict()
        if fact.kind=='transfusion_coverage_link':
            self.check_coverage(repo,fact,rows)
        if fact.kind=='fluid_administration_link':
            a=self.check_pin(repo,d.administration,rows);fluid=self.check_pin(repo,d.fluid,rows)
            if a.kind not in DELIVERY or fluid.kind!='circulatory_event':raise EvidenceConflict()
            from app.services.renal_fluid_entry_service import category
            if category(fluid)!='input_blood':raise EvidenceConflict()
            if d.relationship=='same_delivery':
                av=[Decimal(x.value) for x in a.data.amounts if x.dimension=='volume'];fv=fluid.recorded_amount
                if len(av)!=1 or fv is None or fv.unit.raw!='mL' or d.matched_volume_ml is None or av[0]!=fv.value or av[0]!=Decimal(d.matched_volume_ml):raise EvidenceConflict()
            terminal={}
            for r in rows:terminal[(r.fact.kind,r.fact.id)]=r.fact
            for old in terminal.values():
                if old.kind=='fluid_administration_link' and old.id!=fact.id and old.data.record_status=='recorded' and (old.data.fluid.reference==d.fluid.reference or old.data.administration.reference==d.administration.reference):raise EvidenceConflict()
        if fact.kind=='m10_assessment' and d.interpretation:self.verify_interpretation(repo,d.interpretation,rows)
        if fact.kind=='m10_medication_detail' and d.administration.reference.kind!='medication_administration':raise EvidenceConflict()
        if fact.kind=='transfusion_reaction' and any(p.reference.kind not in DELIVERY|{'medication_administration'} for p in d.implicated):raise EvidenceConflict()
        if isinstance(d,VetData):
            for h in d.attachment_digests:
                row=repo._session.execute(text('SELECT payload FROM m10_attachment WHERE digest=:d'),{'d':h}).first()
                if row is None or sha256(row[0]).hexdigest()!=h:raise EvidenceConflict()
    def check_coverage(self,repo,fact,rows):
        d=fact.data;agg=self.check_pin(repo,d.aggregate,rows);parts=[self.check_pin(repo,p,rows) for p in d.constituents]
        if agg.kind not in DELIVERY or any(p.kind not in DELIVERY for p in parts):raise EvidenceConflict()
        if agg.data.grain!='reported_aggregate' and d.relationship not in ('same_delivery','possible_overlap'):raise EvidenceConflict()
        if any(p.id==agg.id for p in parts) or len({key(p.reference) for p in d.constituents})!=len(d.constituents):raise EvidenceConflict()
        if any((p.data.product.family,p.data.product.preparation)!=(agg.data.product.family,agg.data.product.preparation) for p in parts):raise EvidenceConflict()
        if d.relationship in ('included_in_aggregate','fully_explained_by_constituents','same_delivery'):
            if agg.data.status in ('unknown','not_given') or any(p.data.status in ('unknown','not_given') for p in parts):raise EvidenceConflict()
            expected={(a.dimension,a.unit,a.basis):Decimal(a.value) for a in agg.data.amounts};actual=defaultdict(Decimal)
            for p in parts:
                for a in p.data.amounts:
                    basis=(a.dimension,a.unit,a.basis)
                    if basis not in expected:raise EvidenceConflict()
                    actual[basis]+=Decimal(a.value)
            if any(v>expected[k] for k,v in actual.items()):raise EvidenceConflict()
            if d.relationship=='same_delivery' and (len(parts)!=1 or dict(actual)!=expected):raise EvidenceConflict()
            for p in parts:
                for attr in p.data.product.modifications:
                    matching=next((a for a in agg.data.product.modifications if a.name==attr.name),None)
                    if matching and {matching.value,attr.value}=={'yes','no'}:raise EvidenceConflict()
                lower=point(agg.data.started);upper=point(agg.data.ended);event=point(p.data.occurred)
                if lower and upper and event and not lower<=event<=upper:raise EvidenceConflict()
        if d.relationship=='fully_explained_by_constituents':
            if not d.complete:raise EvidenceConflict()
            expected={(a.dimension,a.unit,a.basis):Decimal(a.value) for a in agg.data.amounts};actual=defaultdict(Decimal)
            for p in parts:
                for a in p.data.amounts:actual[(a.dimension,a.unit,a.basis)]+=Decimal(a.value)
            if not expected or expected!=dict(actual):raise EvidenceConflict()
        terminal={}
        for r in rows:terminal[(r.fact.kind,r.fact.id)]=r.fact
        links=[x for x in terminal.values() if x.kind=='transfusion_coverage_link' and x.id!=fact.id and x.data.record_status=='recorded']+[fact]
        edges=defaultdict(set);allocated={}
        for link in links:
            if link.data.relationship=='possible_overlap':continue
            parent=key(link.data.aggregate.reference)[:2]
            for p in link.data.constituents:
                child=key(p.reference)[:2]
                if child in allocated and allocated[child]!=parent:raise EvidenceConflict()
                allocated[child]=parent;edges[parent].add(child)
        byidentity={(r.fact.kind,r.fact.id):r.fact for r in rows};byidentity[(fact.kind,fact.id)]=fact
        for parent,children in edges.items():
            parent_fact=byidentity.get(parent)
            if not parent_fact:raise EvidenceConflict()
            expected={(a.dimension,a.unit,a.basis):Decimal(a.value) for a in parent_fact.data.amounts};actual=defaultdict(Decimal)
            for child in children:
                child_fact=byidentity.get(child)
                if not child_fact:raise EvidenceConflict()
                for a in child_fact.data.amounts:actual[(a.dimension,a.unit,a.basis)]+=Decimal(a.value)
            if any(k not in expected or v>expected[k] for k,v in actual.items()):raise EvidenceConflict()
        def visit(node,path):
            if node in path:raise EvidenceConflict()
            for child in edges[node]:visit(child,path|{node})
        for node in list(edges):visit(node,set())
    def reply(self,body,status,stored=None,fact=None):
        payload=canonical_payload(body);out={'status':status,'request_canonical':payload,'request_digest':sha256(payload.encode()).hexdigest(),'execution_enabled':False}
        if stored:out.update(self.evidence_item(stored))
        elif fact:out.update(fact=fact.model_dump(mode='json'),canonical_fact=canonical_payload(fact),digest=digest(fact),ingestion=None)
        return self.bounded_dict(out)
    def action(self,repo,body,action):
        self.require_repo(repo,body.repository)
        if (body.patient_id,body.encounter_id)!=(TARGET.patient_id,TARGET.encounter_id):raise EvidenceConflict()
        payload=canonical_payload(body);command=repo._session.execute(text('SELECT payload,response FROM m10_command WHERE command_id=:c'),{'c':str(body.command_id)}).first()
        if command:
            if command[0]!=payload:raise EvidenceConflict()
            return json.loads(command[1])
        if action=='lookup':return self.reply(body,'absent')
        rows=list(self.rows(repo));fact=build_fact(body);completion=None
        prior_courses=[r.fact for r in rows if (r.fact.kind,r.fact.id)==(fact.kind,fact.id)]
        prior=prior_courses[-1] if prior_courses else None
        owned=prior and isinstance(prior.data,DeliveryData) and (prior.data.completed_as or prior.data.retracted_medication)
        if owned and (fact.data.status!='completed' or fact.data.record_status!='recorded'):
            completion=self.retract_medication(repo,body,fact,rows,owned)
            fact=build_fact(body,{**body.data,'completed_as':None,'promote_to_medication':False,'retracted_medication':EvidencePin(reference=completion.reference,digest=digest(completion)).model_dump(mode='json')})
        elif isinstance(fact.data,DeliveryData) and (fact.data.promote_to_medication or owned):
            if owned and not fact.data.promote_to_medication:raise EvidenceConflict()
            completion=self.completed_medication(body,fact,rows)
            completion_pin=EvidencePin(reference=completion.reference,digest=digest(completion))
            fact=build_fact(body,{**body.data,'completed_as':completion_pin.model_dump(mode='json'),'retracted_medication':None})
        chain=[r for r in rows if (r.fact.kind,r.fact.id)==(fact.kind,fact.id)]
        existing=next((r for r in chain if r.fact.reference==fact.reference),None)
        # Patches preserve the immutable submitted command while building one complete successor.
        if isinstance(fact.data,VetData) and fact.data.update_mode=='patch':
            prior=next((r for r in chain if body.predecessor and key(r.fact.reference)==key(body.predecessor)),None)
            if prior is None or digest(prior.fact)!=fact.data.base_digest or fact.data.base_digest!=body.predecessor_digest:raise EvidenceConflict()
            old=prior.fact.data
            if (old.device,old.profile_id,old.profile_version,old.cartridge,old.run_id)!=(fact.data.device,fact.data.profile_id,fact.data.profile_version,fact.data.cartridge,fact.data.run_id):raise EvidenceConflict()
            obs={o.id:o for o in old.observations}
            for o in fact.data.observations:
                if o.id in obs and (obs[o.id].assay,obs[o.id].parameter)!=(o.assay,o.parameter):raise EvidenceConflict()
                obs[o.id]=o
            fact=build_fact(body,{**body.data,'observations':[o.model_dump() for o in obs.values()]})
        if existing:
            if canonical_payload(existing.fact)!=canonical_payload(fact):raise EvidenceConflict()
            response=self.reply(body,'saved',stored=existing)
        else:
            if body.predecessor:
                if not chain or chain[-1].fact.reference!=Reference.model_validate(body.predecessor.model_dump()) or digest(chain[-1].fact)!=body.predecessor_digest:raise EvidenceConflict()
                prior=chain[-1].fact
                if (prior.source_issuer,prior.source_record)!=(fact.source_issuer,fact.source_record):raise EvidenceConflict()
                if isinstance(fact.data,DeliveryData) and prior.data.delivery_id!=fact.data.delivery_id:raise EvidenceConflict()
            elif chain:raise EvidenceConflict()
            for r in rows:
                f=r.fact
                if isinstance(f,M10Fact) and f.id!=fact.id and (f.kind,f.source_issuer,f.source_record)==(fact.kind,fact.source_issuer,fact.source_record):raise EvidenceConflict()
            self.check_data(repo,fact,rows+([SimpleNamespace(fact=completion)] if completion else []))
            if action=='validate':return self.reply(body,'validated',fact=fact)
            if completion:
                if completion.supersedes:repo.append_revision(completion,target=TARGET)
                else:repo.append_fact(completion,target=TARGET)
            stored=repo.append_revision(fact,target=TARGET) if body.predecessor else repo.append_fact(fact,target=TARGET)
            response=self.reply(body,'saved',stored=stored)
        if action=='save':repo._session.execute(text('INSERT INTO m10_command(command_id,payload,response) VALUES (:c,:p,:r)'),{'c':str(body.command_id),'p':payload,'r':json.dumps(response,separators=(',',':'),sort_keys=True)})
        return response
    def evaluate(self,repo,body):
        from app.services.m10_interpretation import interpret
        self.require_repo(repo,body.repository)
        if (body.patient_id,body.encounter_id)!=(TARGET.patient_id,TARGET.encounter_id):raise EvidenceConflict()
        cutoff=repo.capture_cutoff()
        if body.cutoff>cutoff.fact_watermark:raise EvidenceConflict()
        cutoff=cutoff.model_copy(update={'fact_watermark':body.cutoff})
        rows=self.snapshot(repo,body.review_end,cutoff);observations=[];laboratory=[];pins={}
        from app.services.m10_profiles import device_profiles
        device=next((x for x in device_profiles() if x['id']==body.device_profile_id),None)
        selected_reports={}
        for supplied in body.observations:
            source=supplied.get('source_ref')
            if not isinstance(source,dict):raise EvidenceConflict()
            pin=EvidencePin(reference={k:source.get(k) for k in ('kind','id','version')},digest=source.get('digest'))
            f=self.check_pin(repo,pin,rows)
            if f.kind!='viscoelastic_report' or not device or f.data.profile_id!=device['id'] or f.data.profile_version!=device['version'] or f.data.device!=device['device'] or f.data.cartridge!=device['configuration']:raise EvidenceConflict()
            if supplied.get('id') not in {o.id for o in f.data.observations}:raise EvidenceConflict()
            selected_reports[key(f.reference)]=f;pins[key(pin.reference)]=pin
        if len(selected_reports)!=1:raise EvidenceConflict()
        # Interpret the complete report, including counterevidence. Caller value,
        # unit and selected subset cannot remove a heparin or conflicting channel.
        for f in selected_reports.values():
            for o in f.data.observations:
                state=o.state if f.data.record_status=='recorded' and f.data.report_status not in ('withdrawn','invalid','aborted') and o.result_type=='numeric' else 'invalid'
                if o.parameter.upper().startswith(('LY','LI','ML')) and o.maturation!='mature':state='pending'
                if point(o.available_at) and point(o.available_at)>body.review_end:state='pending'
                observations.append({'id':o.id,'assay':o.assay,'parameter':o.parameter,'value':o.value,'unit':o.unit,'status':state,'qualifier':o.comparator,'sample_id':f.data.specimen_id,'run_id':f.data.run_id,'source_ref':{**f.reference.model_dump(),'digest':digest(f)},'observed_at':o.observed_at.value or f.data.sampled.value,'source_current':True,'within_cutoff':True,'maturation':o.maturation,'elapsed_seconds':o.elapsed_seconds,'timing_origin':o.timing_origin})
        for supplied in body.laboratory:
            source=supplied.get('source_ref')
            if not isinstance(source,dict):raise EvidenceConflict()
            pin=EvidencePin(reference={k:source.get(k) for k in ('kind','id','version')},digest=source.get('digest'),component_id=supplied.get('component_id'))
            f=self.check_pin(repo,pin,rows)
            if f.kind!='laboratory_report' or not pin.component_id:raise EvidenceConflict()
            component=next((c for c in f.components if c.source_component_id==pin.component_id),None)
            if component is None:raise EvidenceConflict()
            result=component.result
            # Claiming a Clauss result requires its explicit method in the source.
            assay=component.assay
            recognized={'clauss','clauss fibrinogen','fibrinogen clauss','clauss method'}
            method_confirmed=assay is not None and any(str(v).strip().lower().replace('_',' ') in recognized for v in (assay.code,assay.raw_display))
            if supplied.get('parameter')!='fibrinogen_clauss' or component.mapping_status!='mapped' or component.mapped_concept!='fibrinogen' or not method_confirmed:raise EvidenceConflict()
            laboratory.append({'id':f.id+'/'+pin.component_id,'assay':'LAB','parameter':'fibrinogen_clauss','value':getattr(result,'raw_value',None),'unit':result.unit.raw_display if getattr(result,'unit',None) else None,'status':'final' if result.kind=='numeric' and f.report_status=='final' and f.record_status=='recorded' else 'invalid','qualifier':{'=':'eq','<':'lt','<=':'le','>':'gt','>=':'ge'}.get(getattr(result,'comparator',None),'unknown'),'source_ref':{**f.reference.model_dump(),'digest':pin.digest},'source_current':True,'within_cutoff':True})
            pins[key(pin.reference)]=pin
        payload={'device_profile_id':body.device_profile_id,'protocol_profile_id':body.protocol_profile_id,'mode':body.mode,'context':body.context,'observations':observations,'laboratory':laboratory,'selected_observation_ids':body.selected_observation_ids}
        output=interpret(payload)
        output['evaluation_binding']={'repository':str(body.repository),'patient_id':body.patient_id,'encounter_id':body.encounter_id,'cutoff':body.cutoff,'review_end':body.review_end.isoformat(),'pins':[p.model_dump(mode='json') for p in pins.values()]}
        output['signature']=self.sign_interpretation(output)
        return self.bounded_dict(output)
    def sign_interpretation(self,value):
        material=json.dumps({k:v for k,v in value.items() if k!='signature'},sort_keys=True,separators=(',',':'),ensure_ascii=False)
        return hmac.new(self.dependencies.config.envelope_signing_key.get_secret_value().encode(),material.encode(),'sha256').hexdigest()
    def verify_interpretation(self,repo,value,rows):
        if not isinstance(value.get('signature'),str) or not hmac.compare_digest(value['signature'],self.sign_interpretation(value)):raise EvidenceConflict()
        binding=value.get('evaluation_binding',{})
        if (binding.get('repository'),binding.get('patient_id'),binding.get('encounter_id'))!=(str(repo.capture_cutoff().repository_id),TARGET.patient_id,TARGET.encounter_id):raise EvidenceConflict()
        for p in binding.get('pins',[]):self.check_pin(repo,EvidencePin.model_validate(p),rows)
        from app.services.m10_profiles import protocol_profiles,device_profiles
        profile=value.get('protocol_profile');device=value.get('device_profile')
        if profile and not any(x['id']==profile['id'] and x['content_hash']==profile['content_hash'] for x in protocol_profiles()):raise EvidenceConflict()
        if device and not any(x==device for x in device_profiles()):raise EvidenceConflict()
    def read_attachment(self,repo,repository,digest_value,cutoff,review_end):
        self.require_repo(repo,repository);captured=repo.capture_cutoff()
        if cutoff>captured.fact_watermark:raise EvidenceConflict()
        rows=self.snapshot(repo,review_end,captured.model_copy(update={'fact_watermark':cutoff}))
        if not any(s.fact.kind=='viscoelastic_report' and digest_value in s.fact.data.attachment_digests for s in rows):raise RecordNotFound('attachment not referenced by visible patient evidence')
        row=repo._session.execute(text('SELECT media_type,payload FROM m10_attachment WHERE digest=:d'),{'d':digest_value}).first()
        if row is None or sha256(row[1]).hexdigest()!=digest_value:raise EvidenceConflict()
        return row[0],row[1]

    def completed_medication(self,body,course,rows):
        from app.models.clinical.facts import MedicationAdministration,MedicationIdentity,Dose
        from app.models.clinical.common import Quantity,Unit
        d=course.data;amounts=[a for a in d.amounts if a.dimension=='dose'];event=point(d.occurred) or point(d.ended)
        if not body.available_at:raise EvidenceConflict()
        if body.kind!='haemostatic_medication_course' or d.status!='completed' or len(amounts)!=1 or Decimal(amounts[0].value)<=0 or event is None or d.record_status!='recorded':raise EvidenceConflict()
        a=amounts[0];identifier=str(uuid5(UUID(str(body.id)),'completed-medication'))
        previous=[s.fact for s in rows if s.fact.kind=='medication_administration' and s.fact.id==identifier]
        if d.completed_as and (not previous or d.completed_as.reference!=previous[-1].reference or d.completed_as.digest!=digest(previous[-1])):raise EvidenceConflict()
        recorded=stamp(body.available_at) if body.available_at else stamp(body.recorded_at)
        if recorded<event:raise EvidenceConflict()
        return MedicationAdministration(id=identifier,revision=str(body.revision),binding=course.binding,origin='reported',provenance=course.provenance,time=ClinicalTime(event=event,recorded=recorded,precision='instant'),supersedes=previous[-1].reference if previous else None,correction_reason=body.correction_reason if previous else None,temporal_status='unknown',medication=MedicationIdentity(product_id=course.source_issuer+':'+d.product.label,formulation=d.product.preparation),administered_dose=Dose(amount=Quantity(value=Decimal(a.value),unit=Unit(raw=a.unit,status='unresolved',limitation='Original source unit; no terminology conversion')),basis='total_administered',basis_detail=a.basis),route=d.route,administered_at=event)

    def retract_medication(self,repo,body,course,rows,previous_pin):
        """Retract the completed claim without fabricating a zero-dose delivery.

        The original positive dose stays in immutable history. Its generic
        successor is explicitly conflicted; the corrected course owns any known
        partial/unknown delivery until it can again represent a completed dose.
        """
        from app.models.clinical.facts import MedicationAdministration
        previous=self.check_pin(repo,previous_pin,rows)
        if previous.kind!='medication_administration' or previous.id!=str(uuid5(UUID(course.id),'completed-medication')) or not body.predecessor:raise EvidenceConflict()
        recorded=stamp(body.available_at) if body.available_at else stamp(body.recorded_at)
        payload=previous.model_dump()
        payload.update(revision=str(body.revision),supersedes=previous.reference.model_dump(),correction_reason=body.correction_reason,conflict='unresolved',provenance=course.provenance.model_dump(),time={**previous.time.model_dump(),'recorded':max(recorded,previous.administered_at)},uncertainty=tuple(previous.uncertainty)+(f'Completed-delivery claim retracted by M10 source {course.id}/{course.revision}; do not count this historical dose as delivered.',))
        return MedicationAdministration.model_validate(payload)

    def history(self,repo,body):
        self.require_repo(repo,body.repository);cutoff=repo.capture_cutoff()
        if body.cutoff>cutoff.fact_watermark:raise EvidenceConflict()
        cutoff=cutoff.model_copy(update={'fact_watermark':body.cutoff});ref=Reference.model_validate(body.reference.model_dump());rows=[s for s in self.rows(repo,cutoff,ref) if available(s.fact,body.review_end)]
        if not any(s.fact.reference==ref for s in rows):raise RecordNotFound('source unavailable at review cutoff')
        page=rows[body.offset:body.offset+body.limit]
        return self.bounded_dict({'items':[self.evidence_item(s) for s in page],'offset':body.offset,'next_offset':body.offset+body.limit if body.offset+body.limit<len(rows) else None,'complete':body.offset+body.limit>=len(rows),'total':len(rows),'execution_enabled':False})
    def attachment(self,repo,body):
        self.require_repo(repo,body.repository)
        if body.media_type not in ('application/pdf','image/png','image/jpeg','text/plain'):raise ValueError('unsupported source attachment media')
        try:data=base64.b64decode(body.data_base64,validate=True)
        except ValueError:raise ValueError('invalid attachment encoding') from None
        if len(data)>180000 or sha256(data).hexdigest()!=body.digest:raise EvidenceConflict()
        prior=repo._session.execute(text('SELECT payload FROM m10_attachment WHERE digest=:d'),{'d':body.digest}).first()
        if prior is None:repo._session.execute(text('INSERT INTO m10_attachment(digest,media_type,payload) VALUES (:d,:m,:p)'),{'d':body.digest,'m':body.media_type,'p':data})
        elif prior[0]!=data:raise EvidenceConflict()
        return {'digest':body.digest,'status':'retained','bytes':len(data)}
