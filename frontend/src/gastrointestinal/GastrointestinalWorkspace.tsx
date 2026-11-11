import {compareLaboratoryCollections,hasUniqueLatestCollection} from '../clinicalEvidence/laboratoryDisplay';
import {GIOverviewFindings} from './GIOverviewFindings';
import {GIResultQuality,giRepeatedComponent} from './GIResultQuality';
import {laboratoryQualifications} from './laboratoryPresentation';
import type {MicroState} from '../api/microTypes';
import {AntibioticOverview} from '../antibioticWorkflow/AntibioticOverview';
import {useCallback,useEffect,useMemo,useState} from 'react';
import {RF2Client,key,pin,type Catalog,type Evidence} from '../api/rf2Client';
import {evidenceText} from '../demo/RenalFluidEntryWorkspace';
import {PatientSourceDialog} from '../demo/PatientSourceDialog';
import {LaboratoryEntryDialog} from '../demo/LaboratoryEntryDialog';
import {respiratoryDisplayTime} from '../respiratory/RespiratorySupportTimeline';
import {giCategories,giLabLabels,type GIRecord} from './types';
import {gastrointestinalModel,giTime,type GILab,type GIScope} from './model';
import {GIReview} from './GIReview';
import {GIEntry,giPendingKey} from './GIEntry';
import {GISource} from './GISource';
import './gastrointestinal.css';
const tabs={overview:'Overview',labs:'Results & trends',imaging:'Imaging & procedures',review:'Review & plan'} as const;
export function GastrointestinalWorkspace({catalog,requested,current,loading,error,onRefresh,onGuardChange,micro,onAntibiotics,transport:provided}:{catalog?:Catalog;requested:GIScope;current:boolean;loading:boolean;error?:string;onRefresh:()=>Promise<void>;onGuardChange?:(value:boolean)=>void;transport?:RF2Client;micro?:MicroState;onAntibiotics?:()=>void}){
 const [defaultTransport]=useState(()=>new RF2Client()),transport=provided??defaultTransport,model=useMemo(()=>gastrointestinalModel(catalog,requested,micro),[catalog,micro,requested.patient,requested.encounter,requested.start,requested.end]),confirmed=current&&!loading&&!error&&model.valid;
 const [tab,setTab]=useState<keyof typeof tabs>('overview'),[entry,setEntry]=useState<{prior?:Evidence}>(),[labEntry,setLabEntry]=useState(false),[selection,setSelection]=useState<{evidence:Evidence;trigger:HTMLButtonElement}>(),[guarded,setGuarded]=useState(false),[pendingIssue,setPendingIssue]=useState('');
 useEffect(()=>{if(!catalog)return;try{if(localStorage.getItem(giPendingKey(catalog.repository)))setEntry({});}catch{setPendingIssue('Pending request storage is unavailable. Source entry is withheld.');}},[catalog?.repository]);
 const guard=useCallback((value:boolean)=>{setGuarded(value);onGuardChange?.(value);},[onGuardChange]);
 function inspect(e:Evidence,trigger:HTMLButtonElement){setSelection({evidence:e,trigger});}
 const records=model.records,findings=records.filter(e=>!['imaging','procedure'].includes(String(e.fact.category))),reports=records.filter(e=>['imaging','procedure'].includes(String(e.fact.category)));
 function resultTable(all: boolean) {
  const concepts = all ? Object.keys(giLabLabels) : ['total_bilirubin','ast','alt','alp','albumin','inr'];
  const groups = concepts.map(concept => ({
   concept,
   rows: model.labs.filter(lab => lab.concept === concept)
    .sort((left, right) => compareLaboratoryCollections(left.time, right.time)),
  }));
  const visible = groups.flatMap(group => all ? group.rows : group.rows.slice(0, 2));
  const sourceButton = (row: GILab) => <button type="button" className="gi-link" disabled={guarded}
   onClick={event => inspect(row.evidence, event.currentTarget)}>Source &amp; history</button>;
  const qualifications = (row: GILab) => laboratoryQualifications(row.evidence, row.component, false)
   .map(qualification => <small key={qualification}>{qualification}</small>);
  const repeatedComponent = (row: GILab) => {
   const component = giRepeatedComponent(row, model.labs);
   return component && <small>{component}</small>;
  };

  return <>
   <GIResultQuality rows={visible} onInspect={inspect} disabled={guarded}/>
   <table className="gi-results">
    <caption>{all ? 'GI, liver and pancreatic laboratory results' : 'Recorded liver profile'}</caption>
    <thead><tr><th>Investigation</th>{all
     ? <><th>Recorded result</th><th>Specimen / collected</th></>
     : <th colSpan={2}>Recorded specimens</th>}</tr></thead>
    <tbody>{groups.flatMap(({concept, rows}) => {
     if (all) return rows.map(row =>
      <tr key={key(pin(row.evidence)) + '-' + String(row.component.source_component_id)}>
       <th scope="row">{row.label}</th>
       <td>{row.text}{repeatedComponent(row)}{qualifications(row)}
        <small>{String(row.evidence.fact.report_status)}{row.evidence.fact.conflict === 'unresolved' ? ' · Conflict unresolved' : ''}</small></td>
       <td>{row.collectionText}
        <small>Specimen: {String((row.evidence.fact.specimen as {source_specimen_id?:string})?.source_specimen_id ?? 'ID not recorded')}</small>
        {sourceButton(row)}</td>
      </tr>);
     const ordered = hasUniqueLatestCollection(rows.map(row => row.time));
     return <tr key={concept}>
      <th scope="row">{giLabLabels[concept]}</th>
      {[0, 1].map(index => {
       const row = rows[index];
       return <td key={index}>{row ? <>
        <strong>{row.text}</strong>{repeatedComponent(row)}{qualifications(row)}
        {ordered && <small>{index === 0 ? 'Latest specimen' : 'Earlier specimen'}</small>}
        <small>{row.collectionText} · {String(row.evidence.fact.report_status)}</small>
        {sourceButton(row)}
       </> : index === 0 && <span>Not recorded</span>}</td>;
      })}
     </tr>;
    })}</tbody>
   </table>
  </>;
 }
 function recordCard(e:Evidence){const f=e.fact as GIRecord,withdrawn=f.record_status==='withdrawn';return <article className="gi-finding" key={key(pin(e))}><header><strong>{f.title}</strong><small>{giTime(e)&&Date.parse(giTime(e)!)<Date.parse(requested.start)?'Earlier source · ':''}{giTime(e)?respiratoryDisplayTime(giTime(e)!):'Exact observation time not recorded'} · {f.report_status} · {f.record_status}</small></header>{withdrawn?<strong>Withdrawn source record</strong>:<p className="gi-narrative">{f.narrative}</p>}{f.correction_reason&&<small>Correction: {f.correction_reason}</small>}<button type="button" className="gi-link" disabled={guarded} onClick={event=>inspect(e,event.currentTarget)}>Source & history</button></article>;}
 return <section className="gi-workspace" aria-label="Gastrointestinal and liver workspace"><header className="gi-heading"><div><p className="gi-eyebrow">M11 · Shared patient workspace</p><h2>Gastrointestinal & liver</h2><p>Current findings, investigations and the patient’s course.</p><small>{respiratoryDisplayTime(requested.start)} → {respiratoryDisplayTime(requested.end)}</small></div><div><button type="button" disabled={!confirmed||guarded||!!pendingIssue} onClick={()=>setEntry({})}>Record finding</button><button type="button" disabled={loading||guarded} onClick={()=>void onRefresh().catch(()=>{})}>Refresh evidence</button></div></header>
 {!confirmed&&<p role="status">{loading?'Refreshing patient evidence…':'Current evidence is unconfirmed. Visible records are retained context.'} {error}</p>}{pendingIssue&&<p role="alert">{pendingIssue}</p>}
 <div role="tablist" className="gi-tabs" aria-label="GI and liver review areas">{Object.entries(tabs).map(([id,label])=><button id={'gi-tab-'+id} aria-controls={'gi-panel-'+id} type="button" role="tab" aria-selected={tab===id} disabled={guarded} key={id} onClick={()=>setTab(id as keyof typeof tabs)}>{label}</button>)}</div>
 <div id="gi-panel-overview" role="tabpanel" aria-labelledby="gi-tab-overview" hidden={tab!=='overview'}><div className="gi-columns"><section><h3>Current GI findings</h3>{findings.length?<GIOverviewFindings records={findings} renderRecord={recordCard}/>:<p>No GI finding recorded. Missing findings do not establish normality.</p>}</section><section><h3>Liver profile</h3>{model.labs.length?resultTable(false):<p>No mapped GI/liver results supplied.</p>}<button type="button" onClick={()=>setTab('labs')} disabled={guarded}>Full results & trends</button></section></div><section className="gi-section"><h3>Imaging & procedures</h3>{reports.length?reports.map(e=><button type="button" className="gi-report-link" key={key(pin(e))} disabled={guarded} onClick={event=>inspect(e,event.currentTarget)}>{String(e.fact.title)} · {giTime(e)??'Time not recorded'} · {String(e.fact.report_status)}</button>):<p>No linked abdominal report supplied. This does not establish that a study was unperformed or normal.</p>}</section><GIReview compact catalog={catalog} requested={requested} model={model} current={confirmed} onOpen={()=>setTab('review')}/></div>
 <div id="gi-panel-labs" role="tabpanel" aria-labelledby="gi-tab-labs" hidden={tab!=='labs'}><header className="gi-section-heading"><h3>Results & trends</h3><button type="button" disabled={!confirmed||guarded} onClick={()=>setLabEntry(true)}>Record laboratory result</button></header>{model.labs.length?resultTable(true):<p>No mapped GI/liver results supplied.</p>}{model.unmapped.length>0&&<details><summary>Other original laboratory reports · mapping not established</summary>{model.unmapped.map(e=><button type="button" key={key(pin(e))} onClick={event=>inspect(e,event.currentTarget)}>Original report {e.fact.id} · Source & history</button>)}</details>}<p className="gi-muted">Original units and specimen identities are retained. Repeated samples are separate observations; report corrections remain in source history.</p></div>
 <div id="gi-panel-imaging" role="tabpanel" aria-labelledby="gi-tab-imaging" hidden={tab!=='imaging'}><h3>Imaging & procedures</h3>{reports.length?reports.map(recordCard):<p>No abdominal imaging or procedure report supplied.</p>}<p className="gi-muted">Review the original ultrasound, CT, MRI/MRCP, endoscopy, ERCP or other report. This workspace does not interpret images.</p></div>
 <div id="gi-panel-review" role="tabpanel" aria-labelledby="gi-tab-review" hidden={tab!=='review'}><div className="gi-columns"><GIReview catalog={catalog} requested={requested} model={model} current={confirmed}/><section><h3>Patient course</h3>{[...records,...new Map(model.labs.map(l=>[key(pin(l.evidence)),l.evidence])).values()].sort((a,b)=>(Date.parse(giTime(b)??'')||0)-(Date.parse(giTime(a)??'')||0)).map(e=><article className="gi-history" key={key(pin(e))}><small>{giTime(e)??'Time not established'}</small><p>{String(e.fact.title??'Laboratory report')} · {String(e.fact.report_status)}</p><button type="button" className="gi-link" onClick={event=>inspect(e,event.currentTarget)}>Source & history</button></article>)}</section></div></div>
 <details className="gi-section"><summary>Relevant patient context · circulation, kidneys, fluid and medicines</summary>{model.context.length?model.context.map(e=><button className="gi-context-row" type="button" disabled={guarded} key={key(pin(e))} onClick={event=>inspect(e,event.currentTarget)}>{evidenceText(e)} · {String(e.fact.concept??e.metadata?.chart?.category??e.fact.kind).replaceAll('_',' ')}</button>):<p>No relevant context supplied in this source catalog.</p>}{onAntibiotics&&<AntibioticOverview state={micro} current={confirmed} onOpen={onAntibiotics}/>}</details>
 {entry&&catalog&&<GIEntry catalog={catalog} current={confirmed} prior={entry.prior} transport={transport} onRefresh={onRefresh} onGuardChange={guard} onClose={()=>{setEntry(undefined);guard(false);}}/>}
 {labEntry&&catalog&&<LaboratoryEntryDialog catalog={catalog} transport={transport} onRefresh={onRefresh} onClose={()=>setLabEntry(false)}/>}
 {selection&&catalog&&(selection.evidence.fact.kind==='gastrointestinal_record'||selection.evidence.fact.kind==='laboratory_report'?<GISource evidence={selection.evidence} current={confirmed} transport={transport} onClose={()=>{selection.trigger.focus();setSelection(undefined);}} onCorrect={e=>{setSelection(undefined);setEntry({prior:e});}}/>:<PatientSourceDialog selection={{...selection,catalog,label:String(selection.evidence.fact.kind)}} current={confirmed} transport={transport} onClose={()=>{selection.trigger.focus();setSelection(undefined);}}/>)}
 </section>;
}
