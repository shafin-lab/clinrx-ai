import {measurementText,respiratoryTime,type RespiratorySample,respiratoryModel} from './respiratoryModel';
import type {RespiratoryTab} from './respiratoryCatalog';
import type {RespiratoryRecord} from './respiratoryTypes';

export interface RespiratoryReviewSummary {signature:string;reviewer:string;rationale:string;nextReview:string}
interface Props {
 model:ReturnType<typeof respiratoryModel>;
 current:boolean;
 selected?:RespiratorySample;
 review?:RespiratoryReviewSummary;
 onNavigate:(tab:RespiratoryTab)=>void;
}
const timeLabel=(value:string|null)=>value?new Date(value).toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})+' UTC':'Collection time not recorded';
function reading(record:RespiratoryRecord,concept:string){
 const matches=record.measurements.filter(m=>m.concept===concept);
 if(matches.length>1)return 'Conflicting results';
 if(!matches.length)return 'Not recorded';
 if(matches[0].quality!=='usable')return 'Quality needs review';
 return measurementText(matches[0]);
}

/** Source display only: selection, arithmetic and saved records stay with their owners. */
export function RespiratoryBedsideOverview({model,current,selected,review,onNavigate}:Props){
 const confirmed=current&&model.valid;
 const supports=model.items.filter(e=>e.fact.kind==='respiratory_record'&&(e.fact as RespiratoryRecord).category==='support');
 const mechanics=model.items.filter(e=>e.fact.kind==='respiratory_record'&&(e.fact as RespiratoryRecord).category==='mechanics');
 const gas=confirmed&&selected?.record.category==='blood_gas'&&selected.record.record_status==='recorded'&&['final','corrected','preliminary','interim'].includes(selected.record.report_status)?selected:undefined;
 const plan=confirmed&&review?.signature===model.signature?review:undefined;
 const count=(n:number,singular:string,plural:string)=>n===1?'1 '+singular:n+' '+plural;
 const navigate=(tab:RespiratoryTab)=>()=>onNavigate(tab);
 return <section className="resp-bedside-overview" aria-labelledby="resp-overview-heading">
  <div className="resp-overview-heading"><div><p className="resp-eyebrow">Support · Gas · Mechanics · Next review</p><h3 id="resp-overview-heading">Respiratory bedside overview</h3></div><span className="resp-badge">Recorded facts & clinician review</span></div>
  <div className="resp-overview-grid">
   <section className="resp-overview-card" aria-labelledby="resp-support-title"><span className="resp-overview-number">01 · SUPPORT</span><h3 id="resp-support-title">Breathing support</h3>
    <strong className="resp-overview-headline">{!confirmed?'Evidence unconfirmed':supports.length?count(supports.length,'support record','support records'):'Support not established'}</strong>
    <p>{supports.length&&confirmed?'No support record is selected as current. Inspect actual delivery and source times.':'Review the device, oxygen concentration and what support was actually delivered.'}</p>
    {confirmed&&supports.length===1&&<small>Recorded {timeLabel(respiratoryTime(supports[0]))} · {String(supports[0].fact.title)}</small>}
    <button type="button" disabled={!confirmed} onClick={navigate('course')}>Inspect breathing support <span aria-hidden="true">↗</span></button>
   </section>
   <section className="resp-overview-card" aria-labelledby="resp-gas-title"><span className="resp-overview-number">02 · SPECIMEN & TIMING</span><h3 id="resp-gas-title">Blood gas</h3>
    {!confirmed?<strong className="resp-overview-headline">Evidence unconfirmed</strong>:!gas?<><strong className="resp-overview-headline">Choose a sample</strong><p>Keep the specimen and its collection-time support together.</p></>:<>
     <p className="resp-overview-sample">{gas.record.context.sample_type.replaceAll('_',' ')} · {timeLabel(gas.record.times.collected.value)}</p>
     <dl className="resp-overview-gas"><div><dt>pH</dt><dd>{reading(gas.record,'ph')}</dd></div><div><dt>CO₂</dt><dd>{reading(gas.record,gas.record.context.sample_type==='arterial'?'paco2':'venous_pco2')}</dd></div><div><dt>O₂</dt><dd>{reading(gas.record,gas.record.context.sample_type==='arterial'?'pao2':'pvo2')}</dd></div></dl>
     <div className="resp-overview-settings"><span>Sample-time FiO₂</span><strong>{reading(gas.record,'fio2')}</strong><small>{gas.legacy||gas.record.context.settings_confirmed_at_sample!==true?'Alignment not independently confirmed':'Sample-time confirmation recorded'}</small></div>
    </>}
    <button type="button" disabled={!confirmed} onClick={navigate('physiology')}>Choose or review blood gas <span aria-hidden="true">↗</span></button>
   </section>
   <section className="resp-overview-card" aria-labelledby="resp-mechanics-title"><span className="resp-overview-number">03 · MEASUREMENT CONDITIONS</span><h3 id="resp-mechanics-title">Lung mechanics</h3>
    <strong className="resp-overview-headline">{!confirmed?'Evidence unconfirmed':mechanics.length?count(mechanics.length,'mechanics record','mechanics records'):'Mechanics not established'}</strong>
    <p>Check measured versus set volumes, patient effort, leak and hold conditions.</p><small>Plateau pressure and total PEEP need a valid measurement method.</small>
    <button type="button" disabled={!confirmed} onClick={navigate('physiology')}>Inspect lung mechanics <span aria-hidden="true">↗</span></button>
   </section>
   <section className="resp-overview-card" aria-labelledby="resp-plan-title"><span className="resp-overview-number">04 · CLINICIAN ASSESSMENT</span><h3 id="resp-plan-title">Review plan</h3>
    <strong className="resp-overview-headline">{!confirmed?'Evidence unconfirmed':plan?'Review recorded':'Not assessed'}</strong>
    <p>{plan?plan.rationale:'Record your assessment, uncertainty and the next review step.'}</p><small>{plan?`${plan.reviewer} · Next: ${plan.nextReview}`:'Targets and treatment decisions require a clinician assessment.'}</small>
    <button type="button" onClick={navigate('review')}>Open respiratory review plan <span aria-hidden="true">↗</span></button>
   </section>
  </div>
  <details className="resp-overview-help"><summary>Terms and postoperative context</summary><div className="resp-overview-explainer"><div><h4>Common terms</h4><p><strong>SpO₂:</strong> pulse-oximeter oxygen estimate. <strong>FiO₂:</strong> inspired oxygen concentration. <strong>PEEP:</strong> pressure maintained at the end of expiration.</p><p>Source results, calculated physiology and your assessment remain separate. A later oxygen setting does not replace the setting at collection.</p></div><div><h4>Surgical patients</h4><ul><li><strong>Postoperative respiratory failure</strong> — review the operation, airway protection and possible surgical complications.</li><li><strong>Prevention after planned extubation</strong> — record risk assessment and the intended monitoring/support plan.</li><li><strong>Deterioration after extubation</strong> — reassess urgently; prevention evidence is not a rescue protocol.</li></ul><a href="https://www.thoracic.org/statements/resources/cc/niv-guidelines.pdf" target="_blank" rel="noreferrer">ERS/ATS NIV guidance · 2017</a></div></div></details>
 </section>;
}
