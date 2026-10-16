import {useState} from 'react';
import {overviewGroup,overviewGroups,overviewTimeWindow,shortSourceInterval} from './flowsheetOverview';
import {chartEntry,chartSections,intervalText,type ChartSection} from './chartEntries';
import {deliverySupport,quantityText} from './HemodynamicContext';
import type {CirculatoryItem} from '../api/circulatoryTypes';
import {buildFlowsheet,infusionText,infusionSeries,sourceTime} from './flowsheetPresentation';
import {overviewEvidenceContext} from './overviewEvidenceContext';
import {record,quality,title,value,words} from './evidencePresentation';
type Props={items:CirculatoryItem[];onInspect:(item:CirculatoryItem,trigger:HTMLButtonElement)=>void};
function ChartPoint({item,onInspect,prefix='Chart source',compact=false}:{item:CirculatoryItem;onInspect:Props['onInspect'];prefix?:string;compact?:boolean}){
  const entry=chartEntry(item),interval=intervalText(item);
  const result=value(item),drug=item.fact.kind==='circulatory_vasoactive',infusion=infusionText(item);
  const sourceQuality=quality(item),status=words(item.fact.record_status);
  const eventType=String(record(item.fact.action).event_type),eventLabel=({initiation:'Started',rate_change:'Changed',permanent_stop:'Stopped',pause:'Paused',restart:'Restarted',order:'Order',preparation:'Prepared'} as Record<string,string>)[eventType]??infusion.event;
  const interruption=['pause','permanent_stop','non_delivery'].includes(eventType);
  return <button className={'demo-chart-point'+(compact?' demo-chart-point-compact':'')} aria-label={prefix+' '+item.fact.id+' revision '+item.fact.revision} title={compact?[item.fact.id+' / '+item.fact.revision,interval??'',drug?infusion.event+' · '+infusion.rate:'Quality: '+sourceQuality,'Status: '+status].filter(Boolean).join(' · '):undefined} onClick={event=>onInspect(item,event.currentTarget)}>
    <strong>{drug?(compact?eventLabel:infusion.event):result.text+' '+(result.unit==='1'?'(unit: 1)':result.unit)}</strong>
    {drug&&(!compact||!interruption)&&<span>{interruption?infusion.reason:infusion.rate}</span>}
    {compact?<>
      {!drug&&sourceQuality!=='acceptable'&&<small className="demo-chart-quality">Quality: {sourceQuality}</small>}
      {overviewEvidenceContext(item).map((note,index)=><small key={index}>{note}</small>)}
      {status!=='recorded'&&<small className="demo-chart-status">{status}</small>}
      {interval&&<small>{shortSourceInterval(item)}</small>}
    </>:<>
      <small>Quality: {drug?'not assessed here':sourceQuality} · {status}</small>
      {entry&&<small>{entry.sourceType}</small>}{interval&&<small>{interval}</small>}
      <small>{item.fact.id} / {item.fact.revision}</small>
      {drug&&record(infusion.delivery.rate).value!=null&&<small>Concentration: {String(record(infusion.delivery.concentration).value??'Not recorded')} {String(record(record(infusion.delivery.concentration).unit).raw??'')} · Dosing weight: {infusion.delivery.dosing_weight?'see source reference':'not recorded'}</small>}
    </>}
  </button>;
}
export function ICUFlowsheet({items,onInspect}:Props){
  const chart=buildFlowsheet(items);
  const [section,setSection]=useState<ChartSection|'all'|'overview'>('overview');
  const [page,setPage]=useState(0),[showAllTimes,setShowAllTimes]=useState(false);
  const compact=section==='overview';
  const rows=chart.rows.filter(row=>compact?overviewGroup(row)!==null:section==='all'||row.section===section);
  const window=overviewTimeWindow(chart.times,page,!compact||showAllTimes);
  const times=window.times;
  const visibleRows=compact&&!showAllTimes?rows.filter(row=>times.some(at=>row.cells.has(at))):rows;
  const groups=compact?overviewGroups.filter(label=>rows.some(row=>overviewGroup(row)===label)).map(label=>({label,rows:visibleRows.filter(row=>overviewGroup(row)===label)})):[{label:'Recorded sources',rows}];
  const notes=items.filter(item=>chartEntry(item)?.section==='goals');
  const displayed=rows.flatMap(row=>times.flatMap(at=>row.cells.get(at)??[])).length;
  return <section className="demo-flowsheet" aria-label="Read-only ICU flowsheet">
    <h2>Hemodynamics and infusions over time</h2>
    <p>Fictional recorded evidence. Open any value for its exact source and history. No prescribing, pump control or execution.</p>
    <div className="demo-chart-controls"><label>Flowsheet section<select value={section} onChange={event=>setSection(event.target.value as ChartSection|'all'|'overview')}><option value="overview">Combined overview</option><option value="all">All hemodynamic sections</option>{Object.entries(chartSections).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label></div>
    {compact&&<p className="demo-chart-overview-scope">Together: BP/MAP, cardiac output/index, rhythm/heart rate, ABG/blood gases, echo findings, infusion events, interval urine output, source-reported interval/cumulative chart balance, lactate and capillary refill. Scroll down within the chart to compare all available groups; the time headings stay visible. Rows without records in these selected times are omitted; they remain available through time navigation. Other measurements, pump context and perfusion observations remain in the detailed sections. CO methods and devices stay on separate rows; no preferred output or rhythm diagnosis is inferred. Blood-gas sample types and sample-specific FiO₂ remain explicit. Echo estimates and report findings are source assertions, not diagnoses or current measurements; use earlier/all-times views for older studies.</p>}
    {compact&&chart.times.length>0&&<div className="demo-chart-time-controls" aria-label="Recorded time navigation">
      <button disabled={showAllTimes||window.page===window.lastPage} onClick={()=>setPage(window.page+1)}>Earlier times</button>
      <span role="status">{showAllTimes?'All recorded times':`Recorded times ${window.start+1}–${window.end} of ${chart.times.length}`} · UTC</span>
      <button disabled={showAllTimes||window.page===0} onClick={()=>setPage(window.page-1)}>Later times</button>
      <label><input type="checkbox" checked={showAllTimes} onChange={event=>setShowAllTimes(event.target.checked)}/>Show all recorded times</label>
    </div>}
    <p className="demo-chart-reading-key"><strong>Blank means no record at that time.</strong> No carry-forward, dose conversion or treatment-response inference. Quality concerns and non-recorded statuses stay visible; open a cell for full source quality and context.</p>
    <a className="demo-chart-jump" href="#demo-icu-time-chart">Focus chart ↓</a>
    <p className="demo-chart-count">{displayed} source records shown · {chart.unplaced.length} off-axis · {compact?'Use earlier/later times and detailed sections for remaining records.':'Other evidence remains in the Evidence library.'}</p>
    {!!notes.length&&(section==='all'||section==='goals')&&<details className="demo-chart-notes"><summary>Recorded goals, review and handover ({notes.length})</summary><p>These are source-recorded clinician notes and targets, not system recommendations, active prescriptions or automatic escalation rules.</p>{notes.map(item=><ChartPoint key={item.fact.id+item.fact.revision} prefix="Note source" item={item} onInspect={onInspect}/>)}</details>}
    {times.length>0&&rows.length>0?<div id="demo-icu-time-chart" className={'demo-chart-scroll'+(compact?' demo-chart-scroll-compact':'')} role="region" aria-label="Scrollable ICU time chart" tabIndex={0}><table className={'demo-chart'+(compact?' demo-chart-compact':'')}><caption>Recorded source times in UTC · — means no record, not zero or continued delivery · source intervals stay separate from point measurements</caption><thead><tr><th scope="col">Measurement / infusion</th>{times.map(at=><th scope="col" key={at}><time dateTime={at}>{at.slice(0,10)}<br/>{at.slice(11,19)}</time></th>)}</tr></thead>{groups.map(group=><tbody key={group.label} aria-label={group.label}>
      {compact&&<tr className="demo-chart-group"><th scope="rowgroup" colSpan={times.length+1}>{group.label}{group.label==='Fluid records'&&<small>Volumes over recorded intervals · balances are source-reported, not calculated here</small>}</th></tr>}
      {compact&&group.rows.length===0&&<tr><td colSpan={times.length+1}>No records in these selected times for {group.label}. Use Earlier times or Show all recorded times; older values are not carried forward.</td></tr>}
      {group.rows.map(row=><tr key={row.key}><th scope="row">{row.label}<small title={row.context}>{compact&&row.drug?(row.context.startsWith('Infusion: ')?row.context.slice(10).replace(' · documented events only',''):'Infusion identity not recorded'):row.context}</small></th>{times.map(at=><td key={at}>{row.cells.get(at)?.map(item=><ChartPoint key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])} item={item} onInspect={onInspect} compact={compact}/>)??<span className="demo-chart-empty" aria-label={row.drug?'No event recorded':'No observation recorded'}>{compact?'—':row.drug?'No event recorded':'No observation recorded'}</span>}</td>)}</tr>)}
    </tbody>)}</table></div>:<p>No observations can be placed on this time axis for the selected section. No values or infusion intervals are inferred.</p>}
    <details className="demo-chart-policy"><summary>How to read this chart and fluid records</summary>
      <p>Fictional charted observations and infusion events — not a treatment protocol or dosing advice. No pump control, prescribing or execution is available.</p>
      <p><strong>Read each column as a recorded timestamp, not proof of physiological simultaneity or treatment response.</strong> Rates are shown only at documented events. Blank cells do not mean zero, unchanged measurements, continued delivery or a stopped infusion. No dose conversion, averaging or carry-forward is performed.</p>
      <p>Orders and preparations are not administration. Dose units are preserved, including mcg/min, units/h and mcg/kg/min. Pump rates and dosing weights appear only when separately source-recorded and exactly linked; missing context is not filled in. CO methods, oxygen sample types and acquisition sites remain distinct. Infusion quality is not assessed by this display. HPI is optional.</p>
      <p className="demo-chart-ownership">Fluid volumes are hemodynamic context, not a replacement for renal or nutrition records. Reported net balances and cumulative totals are source assertions, not ClinRx calculations; completeness of all intake/losses is not established. Intervention volumes may already be included in input totals and must not be counted again. Interval bounds are source assertions; duration and interval ordering are not assessed here.</p>
    </details>
    <details className="demo-chart-policy"><summary>Scope and international documentation context</summary><p>This synthetic chart uses public documentation patterns. Local institutions differ in units, recording practices, goals and protocols; no hospital’s treatment policy is imposed here. Source drug units, clinician targets, methods and timestamps remain explicit. HPI is optional. Nutrition, comprehensive renal management and other organ-system assessments remain separate modules; VA-ECMO, Impella and IABP remain deferred.</p><p>Examples: <a href="https://www.lhsc.on.ca/critical-care-trauma-centre/standard-of-care-cardiovascular-monitoring" target="_blank" rel="noreferrer">Canada: LHSC monitoring documentation</a> · <a href="https://www.austin.org.au/Assets/Files/Austin%20Intensive%20Care%20Unit%20Referral%20Form.pdf" target="_blank" rel="noreferrer">Australia: Austin ICU referral form</a> · <a href="https://londonccn.nhs.uk/wp-content/uploads/critical-care_ncr-pages_2015-1.pdf" target="_blank" rel="noreferrer">UK: historical critical-care transfer chart</a> · <a href="https://mimic.mit.edu/docs/iv/modules/icu/inputevents.html" target="_blank" rel="noreferrer">US: archived MIMIC infusion data structure</a>. Historical examples illustrate recording patterns, not current institutional-policy approval.</p></details>
    <section aria-label="Evidence kept off the time axis" className="demo-chart-unplaced"><h3>Evidence kept off the time axis</h3><p>Contextual/unplaced records and source times that this restrictive display cannot place confidently remain inspectable. The source timestamp is preserved.</p>{chart.unplaced.map(item=><div key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])}><button className="demo-explanation-inspect" onClick={event=>onInspect(item,event.currentTarget)}>{title(item)} · {item.fact.id} / {item.fact.revision} ↗</button><span> {sourceTime(item)} · {words(item.inclusion)}</span></div>)}</section>
  </section>;
}

export function InfusionDetails({item,items=[]}:{item:CirculatoryItem;items?:CirculatoryItem[]}){
  const support=deliverySupport(item,items);
  const event=infusionText(item),a=record(item.fact.action),d=event.delivery;
  const q=(v:unknown)=>{const quantity=record(v);return typeof quantity.value==='string'?quantity.value+' '+String(record(quantity.unit).raw??''):'Not recorded';};
  const source=(v:unknown)=>{const code=record(v);return String(code.raw_display??code.code??'Not recorded');};
  return <section aria-label="Recorded infusion event details"><h3>Recorded infusion event</h3><dl className="demo-source-summary">
    <dt>Event</dt><dd>{event.event}</dd>
    <dt>{a.event_type==='order'?'Prescribed rate — not delivery':a.event_type==='preparation'?'Prepared rate — not delivery':'Documented event rate'}</dt><dd>{event.rate}</dd>
    <dt>Concentration</dt><dd>{q(d.concentration)}</dd><dt>Route</dt><dd>{source(d.route)}</dd>
    <dt>Dosing weight</dt><dd>{support.weight?quantityText(support.weight.fact.recorded_amount)+' · source '+support.weight.fact.id+' / '+support.weight.fact.revision+' · '+words(support.weight.fact.record_status):d.dosing_weight?'Exact weight reference unavailable in this view; not replaced':'Not recorded; no weight-based conversion'}</dd>
    <dt>Weight basis</dt><dd>{words(d.dosing_weight_basis)||'Not recorded'}</dd>
    <dt>Pump</dt><dd>{source(d.pump)}</dd><dt>Channel</dt><dd>{source(d.channel)}</dd><dt>Infusion identity</dt><dd>{source(infusionSeries(item))}</dd>
    <dt>Pump volumetric rate</dt><dd>{support.pumps.length?support.pumps.map(source=>quantityText(source.fact.recorded_amount)+' · '+source.fact.id+' / '+source.fact.revision+' · '+sourceTime(source)+' · '+words(source.fact.record_status)).join('; '):'No exact linked pump-rate record available; not calculated from dose or concentration'}</dd>
    {event.reason&&<><dt>Reason</dt><dd>{event.reason}</dd></>}
  </dl><p>No continuous exposure, dose conversion or treatment effect is inferred from this event. Orders and preparations do not establish administration.</p></section>;
}
