import type {CirculatoryItem} from '../api/circulatoryTypes';
import {bloodGasSummary,method,quality,sourceTime,title,value,words} from './evidencePresentation';
import {matchesAuthoredCase,casePanels,type CaseScope} from './syntheticCaseInterpretation';
type Props=CaseScope&{items:CirculatoryItem[];onInspect:(item:CirculatoryItem,trigger:HTMLButtonElement)=>void};
export function PatientCaseInterpretation({items,onInspect,...scope}:Props){
  const matched=matchesAuthoredCase(items,scope);
  const byId=new Map(items.map(item=>[item.fact.id,item]));
  return <section className="demo-case" aria-label="Patient-specific possibilities">
    <div className="demo-explanation-heading"><h3>What might these findings mean together?</h3><span className="demo-case-status">Synthetic case interpretation · unconfirmed</span></div>
    <p>This section separates recorded source findings from possible clinical meaning. It is an authored explanation for this exact synthetic case, not a general diagnostic engine or a clinically validated result. It creates no execution, inference or receipt.</p>
    {matched?<>
      <section aria-label="Possible combined interpretation" className="demo-case-combined"><h4>Possible combined interpretation — not a confirmed diagnosis</h4><p>A possible respiratory acid–base disturbance and possible RV pressure loading may coexist. The flow records do not establish whether either is limiting oxygen delivery or tissue perfusion. A respiratory-to-RV causal link, low-output state and shock diagnosis remain unconfirmed.</p><p><strong>Before connecting them:</strong> the observation times and acquisition contexts would need to be reconciled. A shared review window does not establish one physiological episode.</p></section>
      <p className="demo-case-confirmed"><strong>Confirmed here means only that the source records are present.</strong> It does not confirm their physiological accuracy or any diagnosis. Recorded quality labels and estimates retain their limits.</p>
      <div className="demo-case-panels">{casePanels.map(panel=><section key={panel.id} aria-label={panel.title}><h4>{panel.title}</h4>
        <h5>Recorded findings — source assertions</h5><div className="demo-case-source-list">{panel.sources.map(id=>{
          const item=byId.get(id)!,result=value(item);
          return <button key={id} className="demo-explanation-source" aria-label={'Case source '+title(item)+' '+id} onClick={event=>onInspect(item,event.currentTarget)}><strong>{title(item)}: {result.text} {result.unit==='1'?'(unit: 1)':result.unit}</strong><span>{method(item)} · {sourceTime(item)} · {words(item.inclusion)} · Quality: {quality(item)} · {id} / {item.fact.revision}</span></button>;
        })}</div>
        {panel.id==='abg'&&<p className="demo-case-context">Arterial pH source context: {bloodGasSummary(byId.get('m7-ABG-PH')!).map(([k,v])=>k+': '+v).join(' · ')}. Each other sample retains its own context in the source inspector.</p>}
        <div className="demo-case-possible"><h5>Possible meaning — unconfirmed</h5><p>{panel.possibility}</p></div>
        <div className="demo-case-limits"><h5>What prevents confirmation</h5><p>{panel.limits}</p></div>
      </section>)}</div>
      <p>No confirmed integrated diagnosis is established. No treatment recommendation or automatic execution follows from these possibilities. HPI remains optional and is not used in this interpretation.</p>
    </>:<p className="demo-case-limits" role="status">Case interpretation unavailable: the patient, review window or recorded evidence differs from the authored synthetic case. The previous possibilities are withheld; inspect the current source records below. Nothing is automatically regenerated.</p>}
    <details><summary>Basis and limits of this case interpretation</summary><p>Version: synthetic-case-interpretation/1. The authored text is tied to the complete non-HPI source set, exact revisions, fact content, digests, placement, contextual links and disclosures. Changed, missing, duplicate or additional non-HPI records withhold it. It applies no general threshold rules or patient-level confidence score. Independent review of this new interpretation is pending.</p><p>Clinical background: <a href="https://www.thoracic.org/professionals/clinical-resources/critical-care/clinical-education/abgs.php" target="_blank" rel="noreferrer">ATS ABG interpretation</a> and <a href="https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/" target="_blank" rel="noreferrer">ASE right-heart/PH guidance</a>. These explain the clinical concepts; they do not validate this synthetic case or approve its interpretation.</p></details>
  </section>;
}
