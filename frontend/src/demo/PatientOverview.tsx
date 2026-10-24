import type {MicroState} from '../api/microTypes';
import {m7ReviewEvidence,m9ReviewEvidence,sameReviewPins} from '../respiratory/reviewEvidenceContext';
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {RF2Client,type Catalog,type Evidence} from '../api/rf2Client';
import {key,pin} from '../api/rf2Client';
import {title,words} from './evidencePresentation';
import {chartEntry} from './chartEntries';
import {evidenceText,sourceContext} from './RenalFluidEntryWorkspace';
import type {CatalogStatus} from './RF2FluidChart';
import {PatientSourceDialog,type SourceSelection} from './PatientSourceDialog';
import {investigationPresentation} from '../clinical/sharedInvestigations';
import {WeightEntryDialog} from './WeightEntryDialog';
import {LaboratoryEntryDialog} from './LaboratoryEntryDialog';
import type {WeightScope} from './weightRecovery';
import {loadSavedReviews,type ReviewDomain,type ReviewScope,type SavedReview} from '../clinical/savedReviewStore';
import {respiratoryCategories} from '../respiratory/respiratoryCatalog';
import {RespiratorySourceDialog} from '../respiratory/RespiratorySources';
import {sourceSummary} from '../respiratory/respiratoryModel';
import './patientOverview.css';

type Requested={patient:string;encounter:string;start:string;end:string};
type LaboratoryComponent={source_component_id?:string;test_code?:{namespace?:string;code?:string;raw_display?:string};mapped_concept?:string|null;result?:Record<string,unknown>};
interface Finding {id:string;label:string;records:Evidence[];componentRecords?:Map<string,LaboratoryComponent>}
type CourseAreaId='kidney'|'infection'|'hematologic'|'circulation'|'respiratory'|'other';
interface CourseEvent {id:string;label:string;evidence:Evidence;timestamp:string|null;timeLabel:string;component?:LaboratoryComponent}
interface CourseSection {id:CourseAreaId;label:string;events:CourseEvent[]}
const COURSE_AREAS:Pick<CourseSection,'id'|'label'>[]=[
 {id:'kidney',label:'Renal system'},
 {id:'infection',label:'Antimicrobials'},
 {id:'hematologic',label:'Hematologic system'},
 {id:'circulation',label:'Cardiovascular system'},
 {id:'other',label:'Other recorded findings'},
];
const asRecord=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
function courseTimestamp(e:Evidence):{timestamp:string|null;timeLabel:string}{
 const fact=asRecord(e.fact);
 if(fact.kind==='respiratory_record'){const times=asRecord(fact.times);for(const [key,timeLabel] of [['collected','Collected'],['occurred','Observed'],['reported','Reported'],['available','Available']] as const){const point=asRecord(times[key]);if(point.status==='known'&&typeof point.value==='string')return {timestamp:point.value,timeLabel};}return {timestamp:null,timeLabel:'Time not established'};}
 if(fact.kind==='laboratory_report'){
  const times=asRecord(fact.times);
  for(const [key,timeLabel] of [['collected','Collected'],['reported','Reported'],['available','Available']] as const){const point=asRecord(times[key]);if(point.status==='known'&&typeof point.value==='string')return {timestamp:point.value,timeLabel};}
  return {timestamp:null,timeLabel:'Time not established'};
 }
 const chart=e.metadata?.chart;
 for(const point of [chart?.point,chart?.start])if(typeof point==='string')return {timestamp:point,timeLabel:'Source time'};
 const occurred=asRecord(fact.occurred),recorded=asRecord(occurred.recorded);
 for(const point of [recorded.value,occurred.source_timestamp])if(typeof point==='string')return {timestamp:point,timeLabel:'Source time'};
 const time=asRecord(fact.time);
 for(const point of [time.effective_start,time.event,time.recorded])if(typeof point==='string')return {timestamp:point,timeLabel:'Source time'};
 return {timestamp:null,timeLabel:'Time not established'};
}
function areaForFinding(finding:Finding):CourseAreaId{
 if(finding.records.some(e=>e.fact.kind==='respiratory_record'))return 'respiratory';
 const respiratoryLegacyConcepts=new Set(['ph','paco2','pao2','pvo2','bicarbonate','base_excess','sao2','svo2','scvo2','spo2','respiratory_rate']);
 if(finding.records.some(e=>e.fact.kind==='circulatory_oxygen'&&respiratoryLegacyConcepts.has(String(e.fact.concept).toLowerCase())))return 'respiratory';
 // Laboratory reports are expanded into one finding per component. Route from that
 // component's label and mapped concept; inspecting the parent report here would
 // incorrectly assign every component of a mixed panel to the same clinical area.
 const componentTerms=[finding.label,...Array.from(finding.componentRecords?.values()??[]).flatMap(component=>[component.test_code?.raw_display,component.test_code?.code,component.mapped_concept])];
 const terms=[...componentTerms,...finding.records.flatMap(e=>e.fact.kind==='laboratory_report'?[asRecord(asRecord(e.fact.specimen).specimen_type).raw_display]:[e.fact.kind,e.fact.concept_id,e.fact.concept,e.fact.test,e.fact.signal,e.metadata?.chart?.category])].filter(Boolean).join(' ').toLowerCase().replaceAll('_',' ').replaceAll('₂','2');
 if(/culture|microbiology|susceptib|antimicrobial|antibiotic|organism|specimen/.test(terms))return 'infection';
 const bloodGasSpecimen=/blood|arterial|venous|gas/.test(terms);
 if(/ha?emoglobin|ha?ematocrit|red cell|platelet|blood count|\bcbc\b|\bfbc\b|mcv|mch|reticulocyte|coagulation|\binr\b|\bpt\b|\baptt\b|fibrinogen|d.?dimer|anti.?xa|transfusion|blood bank|thrombophil/.test(terms))return 'hematologic';
 if(/blood gas|\babg\b|\bvbg\b|\bp[ah]co2\b|\bp[ah]o2\b|pvo2|oxygen saturation|\bspo2\b|\bsao2\b|\bsvo2\b|\bscvo2\b|respiratory rate|base excess|co.?oximetry/.test(terms)||bloodGasSpecimen&&(/\bph\b|bicarbonate|base excess/.test(terms)))return 'respiratory';
 if(/kidney|renal|creatinine|urea|\bbun\b|sodium|potassium|chloride|bicarbonate|urine|urinalysis|electrolyte|crrt|dialysis|fluid balance/.test(terms))return 'kidney';
 if(/circulat|pressure|\bmap\b|systolic|diastolic|heart rate|spo2|oxygen saturation|respiratory rate|vasoactive|infusion|perfusion|cardiac|lactate|flow|echo|ecg|rhythm/.test(terms))return 'circulation';
 return 'other';
}
function courseSections(findings:Finding[],withRespiratory=false):CourseSection[]{
 const areas=withRespiratory||findings.some(finding=>areaForFinding(finding)==='respiratory')?[...COURSE_AREAS.slice(0,4),{id:'respiratory' as const,label:'Respiratory system'},...COURSE_AREAS.slice(4)]:COURSE_AREAS;
 const sections=areas.map(area=>({...area,events:[] as CourseEvent[]}));
 for(const finding of findings)for(const evidence of finding.records){const time=courseTimestamp(evidence),label=finding.label?(/[a-z][A-Z]/.test(finding.label)?finding.label:finding.label[0].toUpperCase()+finding.label.slice(1)):'Recorded finding';sections.find(section=>section.id===areaForFinding(finding))!.events.push({id:JSON.stringify([finding.id,key(pin(evidence))]),label,evidence,component:finding.componentRecords?.get(key(pin(evidence))),...time});}
 for(const section of sections)section.events.sort((a,b)=>{
  const left=a.timestamp?Date.parse(a.timestamp):Number.NaN,right=b.timestamp?Date.parse(b.timestamp):Number.NaN;
  if(Number.isFinite(left)&&Number.isFinite(right)&&left!==right)return right-left;
  if(Number.isFinite(left)!==Number.isFinite(right))return Number.isFinite(left)?-1:1;
  const label=a.label.localeCompare(b.label);return label||a.id.localeCompare(b.id);
 });
 return sections;
}
function sourceState(e:Evidence):string[]{
 const fact=asRecord(e.fact),values:string[]=[];
 const reportStatus=fact.report_status;
 if(typeof reportStatus==='string'&&reportStatus!=='unknown')values.push(reportStatus[0].toUpperCase()+reportStatus.slice(1));
 const change=fact.change_state;
 if(typeof change==='string'&&change!=='original')values.push(change==='amended'?'Amended report':change==='corrected'?'Corrected report':'Superseded report');
 const recordStatus=fact.record_status;
 if(typeof recordStatus==='string'&&recordStatus!=='recorded'&&recordStatus!=='unknown')values.push(recordStatus[0].toUpperCase()+recordStatus.slice(1));
 const conflict=fact.conflict;
 if(conflict==='unresolved')values.push('Conflict unresolved');else if(conflict==='resolved')values.push('Conflict resolved');
 if(e.superseded&&!values.includes('Superseded report'))values.push('Superseded historical revision');
 return [...new Set(values)];
}
function recordedText(value:unknown):string|undefined{
 if(typeof value==='string'&&value.trim())return value.trim();
 const item=asRecord(value);
 for(const key of ['raw_display','raw','text','display','value'])if(typeof item[key]==='string'&&String(item[key]).trim())return String(item[key]).trim();
 return undefined;
}
function excerpt(value:string,limit=180){const compact=value.replace(/\s+/g,' ').trim();return compact.length>limit?compact.slice(0,limit-1).trimEnd()+'…':compact;}
function laboratoryComponentSummary(component:LaboratoryComponent):string{
 const label=component.test_code?.raw_display??component.test_code?.code??'Laboratory result',result=asRecord(component.result),kind=result.kind,status=recordedText(result.status),reason=recordedText(result.reason),unit=recordedText(asRecord(result.unit).raw_display);
 if(kind==='unavailable')return `${label}: ${status??'unavailable'}${reason?` · ${reason}`:''}`;
 const raw=recordedText(result.raw_value)??recordedText(result.value)??recordedText(result.finding)??recordedText(result.interpretation)??recordedText(result.category);
 const comparator=recordedText(result.comparator),unitSuffix=unit?.trim()==='1'?'':kind==='numeric'?(unit?` ${unit}`:' unit unavailable'):unit?` ${unit}`:'',value=raw?`${comparator&&comparator!=='='?comparator:''}${raw}${unitSuffix}`:status??'Result content unavailable';
 return `${label}: ${value}`;
}
function courseSummary(e:Evidence,component?:LaboratoryComponent):string{
 const fact=asRecord(e.fact),chart=e.metadata?.chart,note=asRecord(e.metadata?.note),lab=fact.kind==='laboratory_report';
 if(fact.kind==='respiratory_record')return sourceSummary(e);
 if(lab)return component?laboratoryComponentSummary(component):evidenceText(e);
 const quantity=asRecord(fact.recorded_amount),result=asRecord(fact.result),resultQuantity=asRecord(result.quantity),value=asRecord(fact.value),valueQuantity=asRecord(value.value);
 if(typeof quantity.value==='string'||typeof resultQuantity.value==='string'||value.status==='known'&&typeof valueQuantity.value==='string')return evidenceText(e);
 if(e.metadata?.chart?.missing_reason)return `Numerical result unavailable: ${e.metadata.chart.missing_reason}`;
 if(value.status&&value.status!=='known')return `Numerical result unavailable: ${String(value.reason??value.status).replaceAll('_',' ')}`;
 for(const field of ['question','findings','possibilities','plan','gaps']){const text=recordedText(note[field]);if(text)return `Clinician note: ${excerpt(text)}`;}
 const content=[fact.rhythm,fact.recorded_interpretation,fact.finding,result.finding,result.interpretation,result.raw_value,result.value,fact.organism,fact.description,fact.event_description,fact.context_description].map(recordedText).find(Boolean);
 if(content)return `Recorded finding: ${excerpt(content)}`;
 const category=[fact.category,result.category,fact.event_type,fact.signal,fact.availability].map(recordedText).find(Boolean);
 if(category)return `Recorded category: ${excerpt(category)}`;
 if(chart?.missing_reason)return `Source content unavailable: ${chart.missing_reason}`;
 return 'Source content missing: no numeric or narrative result was recorded.';
}
function withdrawalDetail(e:Evidence):string|undefined{
 const fact=asRecord(e.fact),reason=['withdrawal_reason','record_status_reason','status_reason','correction_reason'].map(key=>recordedText(fact[key])).find(Boolean);
 return reason?`Withdrawal details: ${reason}`:undefined;
}
const categories:Record<string,string>={weight:'Recorded weight',input_oral:'Oral intake',input_enteral:'Enteral intake',input_iv:'IV fluid input',input_blood:'Blood-product input',output_urine:'Urine output',output_drain:'Drain output',output_other:'Other measured loss',output_crrt:'CRRT net fluid removal',output_crrt_net:'Recorded CRRT net removal',output_crrt_effluent:'Recorded CRRT effluent',net_balance_reported:'Reported interval fluid balance',urine_total_reported:'Reported cumulative urine volume',balance_total_reported:'Reported cumulative chart balance'};
const names:Record<string,string>={'body-weight':'Recorded weight'};
const sameInstant=(a:string,b:string)=>Number.isFinite(Date.parse(a))&&Date.parse(a)===Date.parse(b);
const reviewActions:Record<ReviewDomain,Record<string,string>>={M9:{review:'Respiratory review'},M7:{confirm:'Confirm measurement',perfusion:'Reassess perfusion',fluid:'Review fluid benefit and harm',vasoactive:'Review vasoactive delivery',specialist:'Seek senior or specialist review',continue:'Continue observation and reassess'},M8:{collection:'Check collection and catheter patency',baseline:'Review baseline and kidney trajectory',urgent:'Seek urgent renal or ICU review',delivery:'Review kidney support delivery',citrate:'Review citrate and metabolic context',medications:'Review renal medication dosing and levels',recovery:'Review kidney recovery',followup:'Plan renal follow-up'}};
export function overviewReviewSummaries(catalog:Catalog,requested:Requested,micro?:MicroState){
 const scope=catalog.combined.context.scope,signature=JSON.stringify([scope.patient_id,scope.encounter_id,scope.review_start,scope.review_end,catalog.repository,catalog.cutoff.fact_watermark]);
 return (catalog.respiratory_records?['M7','M8','M9'] as const:['M7','M8'] as const).map(domain=>{
  const reviewScope:ReviewScope={domain,patient:requested.patient,encounter:requested.encounter,repository:catalog.repository},loaded=loadSavedReviews<Record<string,unknown>>(reviewScope);
  const expected=domain==='M7'?m7ReviewEvidence(catalog.combined.circulatory,requested,catalog):domain==='M9'?m9ReviewEvidence(catalog,requested,micro):undefined;
  return {domain,review:loaded.reviews[0] as SavedReview<Record<string,unknown>>|undefined,issue:loaded.issue??'',matchesCurrent:!!loaded.reviews[0]&&(expected?loaded.reviews[0].snapshot.signature===expected.signature&&sameReviewPins(loaded.reviews[0].snapshot.pins,expected.pins):loaded.reviews[0].snapshot.signature===signature)};
 });
}
/** Presentation of an already-decoded shared catalog. No requests, inference or source mutation. */
export function patientOverviewModel(catalog:Catalog,requested:Requested){
 const scope=catalog.combined.context.scope,circ=catalog.combined.circulatory.assembly.request.scope;
 const sameScope=(s:typeof scope)=>s.patient_id===requested.patient&&s.encounter_id===requested.encounter&&sameInstant(s.review_start,requested.start)&&sameInstant(s.review_end,requested.end)&&s.repository_cutoff.repository_id===catalog.repository&&s.repository_cutoff.fact_watermark===catalog.cutoff.fact_watermark;
 const seen=new Set<string>();
 const allEvidence=[...catalog.items,...catalog.laboratory_reports,...(catalog.respiratory_records??[])];
 const valid=catalog.execution_enabled===false&&catalog.combined.execution_enabled===false&&catalog.combined.circulatory.execution_enabled===false&&catalog.cutoff.repository_id===catalog.repository&&sameScope(scope)&&sameScope(circ)&&sameScope(catalog.combined.laboratory.scope)&&allEvidence.every(e=>{
  const k=key(pin(e));if(seen.has(k))return false;seen.add(k);
  return e.repository===catalog.repository&&(e.fact.kind==='respiratory_record'?e.cutoff<=catalog.cutoff.fact_watermark:e.cutoff===catalog.cutoff.fact_watermark)&&e.ingestion.ingestion_sequence<=e.cutoff&&e.ingestion.repository_id===catalog.repository&&e.ingestion.ingestion_sequence<=e.cutoff&&e.fact.binding.target.patient_id===requested.patient&&e.fact.binding.target.encounter_id===requested.encounter;
 });
 if(!valid)return {valid:false,findings:[] as Finding[],courseSections:[] as CourseSection[]};
 const groups=new Map<string,Finding>();
 const sourceItems=new Map(catalog.combined.circulatory.assembly.snapshot.items.map(i=>[JSON.stringify([i.fact.kind,i.fact.id,i.fact.revision]),i]));
 for(const e of catalog.items){
  const item=sourceItems.get(JSON.stringify([e.fact.kind,e.fact.id,e.fact.revision]));
  const chart=item?chartEntry(item):undefined;
  const category=e.metadata?.chart?.category??chart?.code;
  const label=e.metadata?.note?'Clinician-authored review':category?(categories[category]??chart?.label??words(category)):investigationPresentation(e.fact)?.label??names[String(e.fact.concept_id)]??(item?title(item):chart?.label??words(e.fact.kind));
  const id=category==='weight'||e.fact.kind==='observation'&&e.fact.concept_id==='body-weight'?JSON.stringify(['finding','recorded-weight']):JSON.stringify([e.fact.kind,e.metadata?.note?e.fact.id:category??e.fact.concept_id??e.fact.concept??e.fact.test??e.fact.signal??e.fact.event_type??label]);
  if(!groups.has(id))groups.set(id,{id,label,records:[]});
  groups.get(id)!.records.push(e);
 }
 for(const e of catalog.laboratory_reports){
  const components=(e.fact as unknown as {components?:LaboratoryComponent[]}).components??[];
  for(const [index,component] of components.entries()){
   const test=component.test_code?.raw_display??component.test_code?.code??'Laboratory result';
   const sourceCode=component.mapped_concept??`${component.test_code?.namespace??''}:${component.test_code?.code??''}`;
   const sourceComponent=component.source_component_id??String(index);
   const id=JSON.stringify(['laboratory',sourceCode,sourceComponent]);
   if(!groups.has(id))groups.set(id,{id,label:test,records:[],componentRecords:new Map()});
   const finding=groups.get(id)!;finding.records.push(e);finding.componentRecords!.set(key(pin(e)),component);
  }
 }
 for(const e of catalog.respiratory_records??[]){const category=String(e.fact.category) as keyof typeof respiratoryCategories;const id=JSON.stringify(['respiratory',category]);if(!groups.has(id))groups.set(id,{id,label:respiratoryCategories[category]?.label??'Respiratory record',records:[]});groups.get(id)!.records.push(e);}
 const findings=[...groups.values()];
 return {valid:true,findings,courseSections:courseSections(findings,catalog.respiratory_records!==undefined||findings.some(finding=>areaForFinding(finding)==='respiratory'))};
}
interface Props {onRespiratory?:()=>void;manualClearanceAvailable?:boolean;catalog?:Catalog;status:CatalogStatus;requested:Requested;retrievalMessage?:string;guarded:boolean;onRefresh?:()=>void|Promise<void>;transport?:Pick<RF2Client,'history'>;laboratoryTransport?:Pick<RF2Client,'importLaboratory'>;weightEntryEnabled?:boolean;weightTransport?:Pick<RF2Client,'action'>;onCharting?:()=>void;micro?:MicroState;antibioticOverview?:ReactNode;transfusionOverview?:ReactNode}
export function PatientOverview({onRespiratory,manualClearanceAvailable=false,catalog,status,requested,retrievalMessage,guarded,onRefresh,transport:providedTransport,laboratoryTransport,weightEntryEnabled=false,weightTransport,onCharting,antibioticOverview,micro,transfusionOverview}:Props){
 const [defaultTransport]=useState(()=>new RF2Client()),[selection,setSelection]=useState<SourceSelection>(),[addInformationOpen,setAddInformationOpen]=useState(false),[labEntryOpen,setLabEntryOpen]=useState(false);
 const [entry,setEntry]=useState<{scope:WeightScope;source?:Evidence;trigger:HTMLButtonElement}>();
 const addInformation=useRef<HTMLButtonElement>(null),addInformationDialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{if(addInformationOpen){addInformationDialog.current?.showModal();addInformationDialog.current?.querySelector<HTMLButtonElement>('button')?.focus();}},[addInformationOpen]);
 function closeAddInformation(){addInformationDialog.current?.close();setAddInformationOpen(false);addInformation.current?.focus();}
 const transport=providedTransport??defaultTransport;
 const model=useMemo(()=>catalog?patientOverviewModel(catalog,requested):undefined,[catalog,requested.patient,requested.encounter,requested.start,requested.end]);
 const reviewSummaries=model?.valid&&catalog?overviewReviewSummaries(catalog,requested,micro):[];
 const current=status==='current';
 const courseFinding=(ordered:CourseEvent[])=>{const latest=ordered[0];if(!latest)return null;const latestStates=sourceState(latest.evidence),withdrawn=latest.evidence.fact.record_status==='withdrawn',summary=courseSummary(latest.evidence,latest.component);return <article className="connected-finding course-finding" key={latest.label}><h4>{latest.label}</h4>{withdrawn?<><p className="course-latest-value course-withdrawn"><strong>Withdrawn source record</strong></p><p className="course-historical-value">Historical value: {summary}</p><p className="course-latest-time">Historical source time: {latest.timestamp??'Time not established'}</p>{withdrawalDetail(latest.evidence)&&<p className="course-state">{withdrawalDetail(latest.evidence)}</p>}</>:<><p className="course-latest-value">{summary}</p><p className="course-latest-time">{latest.timestamp?`Latest recorded in selected period · ${latest.timeLabel.toLowerCase()} ${latest.timestamp}`:'Time not established'}</p>{latestStates.length>0&&<p className="course-state">{latestStates.join(' · ')}</p>}</>}<details><summary>View recorded details</summary><p>{ordered.length} recorded sources</p><div className="course-history"><p className="course-history-note">Source entries are ordered by their supplied timestamps. This is not a current-state selection or clinical ranking.</p>{ordered.map(event=>{const e=event.evidence,states=sourceState(e),isWithdrawn=e.fact.record_status==='withdrawn';return <div className="course-event" key={event.id}>{isWithdrawn&&<p className="course-withdrawn"><strong>Withdrawn source record</strong></p>}<p><time>{event.timestamp?`${event.timeLabel}: ${event.timestamp}`:'Time not established'}</time> · <strong>{isWithdrawn?`Historical value: ${courseSummary(e,event.component)}`:courseSummary(e,event.component)}</strong></p>{states.length>0&&<p className="course-state">{states.join(' · ')}</p>}{withdrawalDetail(e)&&<p>{withdrawalDetail(e)}</p>}<details><summary>Exact source and context</summary><p>{sourceContext(e,catalog!)}</p><p>Recorded status: {String(e.fact.record_status??'Not supplied')}</p>{e.metadata?.note&&<p>Clinician-authored review — not a generated clinical conclusion.</p>}<button type="button" disabled={!current||guarded} aria-label={`Open recorded source ${e.fact.id} / ${e.fact.revision}`} onClick={click=>setSelection({evidence:e,catalog:catalog!,label:event.label,trigger:click.currentTarget})}>Open source details</button><details><summary>Source method, timing and exact reference</summary><pre>{JSON.stringify({reference:pin(e),time:e.fact.time,occurred:e.fact.occurred,interval:e.fact.recorded_interval,acquisition:e.fact.acquisition,uncertainty:e.fact.uncertainty},null,2)}</pre></details><details><summary>Complete original recorded content</summary><pre>{JSON.stringify({fact:e.fact,metadata:e.metadata},null,2)}</pre></details></details></div>;})}</div></details></article>;};
 return <section className="connected-overview" aria-label="Connected patient overview">
  <div className="connected-heading"><div><p className="connected-eyebrow">One patient · Shared recorded evidence</p><h2>Patient overview</h2></div>{onRefresh?<button ref={addInformation} type="button" disabled={!current||!model?.valid||guarded||!!entry||labEntryOpen} onClick={()=>setAddInformationOpen(true)}>Add information</button>:<span className="connected-readonly">Read-only source connection</span>}</div>
  <p className="connected-period">Selected period: {requested.start} → {requested.end}. Source timestamps retain their recorded offsets.</p>
  {!current&&<p role="alert" className="connected-warning">{status==='loading'?'Patient evidence is loading or refreshing.':'Patient evidence retrieval is unconfirmed.'} {catalog?'Retained prior data — not confirmed current.':'No confirmed patient overview is available.'} {retrievalMessage}</p>}
  {catalog&&!model?.valid&&<p role="alert" className="connected-warning">Overview withheld — patient, encounter, period or repository/cutoff correspondence could not be confirmed. No different source was substituted.</p>}
  {catalog&&model?.valid&&<>
   {transfusionOverview}
   <section className="connected-course" aria-label="Recorded course by area"><div><h3>Recorded course by area</h3><p>Review changes during the selected period, grouped by area. Source time orders records only; no diagnosis or severity ranking is generated.</p><p>{catalog.items.length+catalog.laboratory_reports.length?'The selected period includes records, and recorded assertions or source reports are available together.':'No recorded assertions or source reports are supplied in this bounded view.'}</p><p className="connected-caveat">Recorded evidence only. A combined clinical interpretation has not been generated. Expand a finding to inspect each source and its correction history.</p></div><div className="connected-course-grid">{model.courseSections.map(section=>{const grouped=new Map<string,CourseEvent[]>();for(const event of section.events){if(!grouped.has(event.label))grouped.set(event.label,[]);grouped.get(event.label)!.push(event);}return <section className="connected-course-area" aria-label={section.label} key={section.id}><h4>{section.label}</h4>{grouped.size?Array.from(grouped.values(),courseFinding):section.id==='infection'&&!antibioticOverview?<p>No culture finding is available in this patient response. This does not establish that no culture reports exist.</p>:section.id==='infection'?null:<p>No finding is supplied in this area for the selected view. This does not establish normal findings.</p>}{section.id==='infection'&&antibioticOverview}{section.id==='respiratory'&&onRespiratory&&<button type="button" disabled={guarded} onClick={onRespiratory}>Open respiratory review</button>}</section>;})}</div></section>
   <section className="connected-review-summaries" aria-label="Clinician reviews and next plans"><h3>Clinician reviews and next plans</h3><p>Latest saved review for this patient, encounter and repository. Notes are saved in this browser and are not shared chart documentation.</p><div className="connected-review-grid">{reviewSummaries.map(({domain,review,issue,matchesCurrent})=>{const action=String(review?.draft.action??'');const actionLabel=reviewActions[domain][action]??action.replaceAll('_',' ').replace(/^\w/,character=>character.toUpperCase());return <article key={domain}><h4>{domain} review</h4>{review?<><strong>{actionLabel}</strong><p>{String(review.draft.rationale)}</p><p><span>{matchesCurrent&&current?'Current evidence snapshot':'Historical · evidence snapshot differs or is unconfirmed'}</span></p><small>{String(review.draft.reviewer)} · Reviewed {review.recordedAt}</small><p><b>Next review plan:</b> {String(review.draft.nextReview)} <small>No reminder is scheduled.</small></p></>:<p>{issue||'No saved review is available in this browser for this encounter and repository.'}</p>}</article>})}</div></section>
   <aside className="connected-warning" aria-label="Overview limitations"><h3>Still unresolved</h3><p>Completeness and clinical interpretation. {manualClearanceAvailable?'Automated calculations remain inactive. A manual-input creatinine clearance calculator is available in Antibiotics.':'Calculations unavailable — source eligibility not established.'} Domains not supplied by this catalog are not treated as normal.</p></aside>

   <details className="connected-boundary"><summary>Review scope, source counts and recorded coverage</summary><p>Repository {catalog.repository} · cutoff {catalog.cutoff.fact_watermark} · {catalog.items.length} assertion records · {catalog.laboratory_reports.length} laboratory reports · {catalog.respiratory_records?.length??0} respiratory records.</p><pre>{JSON.stringify({coverage:catalog.combined.circulatory.assembly.snapshot.coverage,issues:catalog.combined.circulatory.assembly.snapshot.issues},null,2)}</pre></details>
  </>}
  {onRefresh&&<button type="button" disabled={status==='loading'||guarded||!!entry} onClick={()=>{void Promise.resolve(onRefresh()).catch(()=>{});}}>Refresh records</button>}
  {addInformationOpen&&<dialog ref={addInformationDialog} className="connected-source-dialog add-information-dialog" aria-labelledby="add-information-title" onCancel={event=>{event.preventDefault();closeAddInformation();}}><header><h2 id="add-information-title">Add information</h2><button type="button" onClick={closeAddInformation}>Close</button></header><p>Choose a supported source-entry workflow for this synthetic encounter.</p><div className="add-information-options">{weightEntryEnabled&&<button type="button" onClick={()=>{const trigger=addInformation.current;if(!trigger||!catalog)return;closeAddInformation();setEntry({scope:{patient:requested.patient,encounter:requested.encounter,repository:catalog.repository},trigger});}}>Recorded weight</button>}{onCharting&&<button type="button" onClick={()=>{closeAddInformation();onCharting();}}>Fluid or urine chart entry</button>}<button type="button" onClick={()=>{closeAddInformation();setLabEntryOpen(true);}}>Laboratory result</button>{onRespiratory&&<button type="button" onClick={()=>{closeAddInformation();onRespiratory();}}>Respiratory information</button>}</div><p className="m7-caption">Only listed entry types are available here. Results retain their source context.</p></dialog>}
  {labEntryOpen&&catalog&&<LaboratoryEntryDialog catalog={catalog} transport={laboratoryTransport??defaultTransport} onRefresh={async()=>{await onRefresh?.();}} onClose={()=>{setLabEntryOpen(false);addInformation.current?.focus();}}/>}
  {selection&&model?.valid&&catalog?.repository===selection.evidence.repository&&selection.evidence.fact.kind==='respiratory_record'&&<RespiratorySourceDialog evidence={selection.evidence} transport={transport} current={current} onClose={()=>setSelection(undefined)}/>}
  {selection&&model?.valid&&catalog?.repository===selection.evidence.repository&&selection.evidence.fact.kind!=='respiratory_record'&&<PatientSourceDialog selection={selection} transport={transport} current={current} onClose={()=>setSelection(undefined)} onCorrect={weightEntryEnabled&&current&&!guarded&&onRefresh?()=>{const selected=selection;setSelection(undefined);setEntry({scope:{patient:requested.patient,encounter:requested.encounter,repository:catalog.repository},source:selected.evidence,trigger:selected.trigger});}:undefined}/>}
  {entry&&<WeightEntryDialog {...entry} currentScope={{patient:requested.patient,encounter:requested.encounter,repository:catalog?.repository??''}} current={current&&!!model?.valid&&!guarded} transport={weightTransport??defaultTransport} onRefresh={async()=>{await onRefresh?.();}} onClose={()=>setEntry(undefined)} onReturnFocus={()=>addInformation.current?.focus()}/>}
  {!catalog&&status!=='loading'&&<p>This overview requires the existing RF2 shared catalog. Separate source snapshots are not combined to simulate a connected patient.</p>}
 </section>;
}
