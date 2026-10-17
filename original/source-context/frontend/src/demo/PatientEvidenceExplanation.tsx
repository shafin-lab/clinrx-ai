import type {CirculatoryItem} from '../api/circulatoryTypes';
import {method,quality,sourceTime,title,value,words} from './evidencePresentation';
import {explanationStreams,sourceUncertainties,streamItems,recordedViewCaveats} from './explanationSources';

type Props={items:CirculatoryItem[];onInspect:(item:CirculatoryItem,trigger:HTMLButtonElement)=>void};
function SourceLink({item,onInspect}:{item:CirculatoryItem;onInspect:Props['onInspect']}){
  const result=value(item);
  return <button className="demo-explanation-source" aria-label={'Explain source '+title(item)+' '+item.fact.id} onClick={event=>onInspect(item,event.currentTarget)}>
    <strong>{title(item)}: {result.text} {result.unit==='1'?'(unit: 1)':result.unit}</strong>
    <span>{method(item)} · {sourceTime(item)} · {words(item.inclusion)} · Quality: {quality(item)} · {item.fact.id} / {item.fact.revision}</span>
  </button>;
}
export function EvidenceExplanation({items,onInspect}:Props){
  const uncertainty=sourceUncertainties(items),viewCaveats=recordedViewCaveats(items);
  const present=explanationStreams.filter(stream=>streamItems(items,stream.kinds).length>0);
  const outputs=items.filter(item=>item.fact.kind==='circulatory_cardiac'&&item.fact.concept==='co');
  return <section className="demo-explanation" aria-label="How the evidence fits together">
    <div className="demo-explanation-heading"><h3>How these records fit together</h3><span className="demo-explanation-status">Patient-level relationship: not established</span></div>
    <p>{present.length} of 3 evidence streams have records in this view. Blood sample, measured flow/pressures and echo report provide complementary source information. Their presence together does not prove agreement, simultaneity or cause.</p>
    <p><strong>What this explanation does:</strong> shows what each stream contributes and links its recorded values to their sources. Source quality labels are not confidence in a combined interpretation.</p>
    <div className="demo-explanation-streams">{explanationStreams.map(stream=>{
      const sources=streamItems(items,stream.kinds);
      return <section key={stream.key} aria-label={stream.label}><h4>{stream.label}</h4>
        {sources.length?<><p>{stream.contribution}</p><p className="demo-explanation-connection">{stream.connection}</p><details><summary>Recorded sources behind this explanation ({sources.length})</summary><div className="demo-explanation-source-list">{sources.map(item=><SourceLink key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])} item={item} onInspect={onInspect}/>)}</div></details></>:<p className="demo-empty">No records for this stream in the bounded view. No finding or connection is inferred from its absence.</p>}
      </section>;
    })}</div>
    <section aria-label="What remains uncertain" className="demo-explanation-uncertainty"><h4>What remains uncertain</h4>
      <p>These are limited display checks, not an eligibility or full quality assessment. Values and units remain as recorded; unit mapping and calibration applicability are not resolved by this explanation.</p>
      <ul><li>Cross-stream timing and clinical agreement have not been established. The review window is not a claim that these observations describe the same physiological moment.</li>
        {outputs.length>1&&<li>{outputs.length} cardiac-output records are present. Their separate methods, source times and placement remain visible; no preferred value, equivalence, average or trend is inferred.</li>}
        <li>No causal link between the gas results, flow measurements and echo findings is established. No integrated diagnosis, shock subtype, PH/PAH classification or treatment recommendation is generated.</li></ul>
      {uncertainty.length?<details open><summary>Record-specific uncertainty and source caveats ({uncertainty.length} records)</summary><ul>{uncertainty.map(({item,reasons,notes})=><li key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])}>
        <button className="demo-explanation-inspect" aria-label={'Inspect uncertainty '+title(item)+' '+item.fact.id} onClick={event=>onInspect(item,event.currentTarget)}>{title(item)} · {item.fact.id} / {item.fact.revision} ↗</button>
        <ul>{reasons.map(reason=><li key={reason}>{reason}</li>)}{notes.map(note=><li key={note}>Source note: {note}</li>)}</ul>
      </li>)}</ul></details>:<p>No additional flags were identified by these limited display checks. This does not establish reliable measurements, clinical agreement or a combined interpretation.</p>}
    </section>
    {!!viewCaveats.length&&<details><summary>Recorded-view caveats</summary><ul>{viewCaveats.map(({note,sources})=><li key={note}><p>{note}</p><details><summary>Sources carrying this caveat ({sources.length})</summary>{sources.map(item=><button className="demo-explanation-inspect" key={JSON.stringify([item.fact.kind,item.fact.id,item.fact.revision])} onClick={event=>onInspect(item,event.currentTarget)}>{title(item)} · {item.fact.id} / {item.fact.revision} ↗</button>)}</details></li>)}</ul></details>}
    <details className="demo-explanation-boundary"><summary>Explanation scope and clinical source context</summary><p>This is a template-based explanation of recorded evidence. It does not apply clinical thresholds, calculate oxygen delivery, recalculate echo pressures or infer acid–base status. Individual source records remain available below. HPI remains optional.</p><p>General source context: <a href="https://www.aarc.org/wp-content/uploads/2025/03/davis-et-al-2013-aarc-clinical-practice-guideline-blood-gas-analysis-and-hemoximetry-2013.pdf" target="_blank" rel="noreferrer">AARC blood-gas guidance</a> and <a href="https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/" target="_blank" rel="noreferrer">ASE right-heart/PH guidance</a>. These links do not validate this synthetic case or the combined explanation.</p></details>
  </section>;
}
