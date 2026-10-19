import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import type {CirculatoryItem} from '../src/api/circulatoryTypes';
import {buildGuided} from '../src/demo/guidedEvidence';
import {evidenceKey} from '../src/demo/evidenceIdentity';
import {ReassessmentComparison,reassessmentReference} from '../src/demo/ReassessmentComparison';
afterEach(cleanup);
function data(){
 const state=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false});
 const source=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-60')!;
 const baseline=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-PH-30')!;
 const intervention=state.assembly.snapshot.items.find(i=>i.fact.id==='fs-D-CHANGE')!;
 const corrected=structuredClone(source);corrected.fact.revision='corrected/revision';
 const fields={baseline:evidenceKey(baseline.fact),intervention:evidenceKey(intervention.fact),followup:evidenceKey(source.fact),question:'Review after transcription correction',findings:'Original authored pH 7.35; source time retained.',possibilities:'Patient-level relationship is not established.',uncertainty:'Unknown clock; synthetic source only.',nextReview:'Review full source.'};
 const make=(id:string,followup:CirculatoryItem)=>({...source,fact:structuredClone(buildGuided('reassessment',{...fields,followup:evidenceKey(followup.fact)},'Synthetic reviewer',[baseline,intervention,followup],id,'2026-10-18T12:00:00Z'))});
 const a=make('note/original',source),b=make('note/new',corrected);
 state.assembly.snapshot.items=[baseline,intervention,corrected,a,b];return {state,a,b,source,corrected};
}
function select(a:CirculatoryItem,b:CirculatoryItem){
 fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(a.fact)}});
 fireEvent.change(screen.getByRole('combobox',{name:'Note B'}),{target:{value:evidenceKey(b.fact)}});
}
it('compares exact original and successor references without replacing missing historical measurements or mutating notes',()=>{
 const {state,a,b}=data(),before=JSON.stringify(state);render(<ReassessmentComparison state={state}/>);select(a,b);
 const row=within(screen.getByRole('table')).getAllByRole('row').find(r=>r.textContent?.includes('Follow-up ABG / evidence reference'))!;
 const cells=within(row).getAllByRole('cell');expect(cells[0]).toHaveTextContent('Revision: 1');expect(cells[1]).toHaveTextContent('Revision: corrected/revision');
 expect(screen.getByText(/Referenced measurement values are not reloaded or substituted/)).toBeInTheDocument();
 expect(screen.getByText('Note A full authored narrative')).toBeInTheDocument();expect(screen.getByText('Note B uncertainty and provenance')).toBeInTheDocument();
 expect(JSON.stringify(state)).toBe(before);
});
it('preserves explicit selection on reordered snapshots and discloses missing selected notes without substituting another',()=>{
 const {state,a,b}=data();const view=render(<ReassessmentComparison state={state}/>);select(a,b);
 view.rerender(<ReassessmentComparison state={{...state,assembly:{...state.assembly,snapshot:{...state.assembly.snapshot,items:[...state.assembly.snapshot.items].reverse()}}}}/>);
 expect(screen.getByRole('combobox',{name:'Note A'})).toHaveValue(evidenceKey(a.fact));
 view.rerender(<ReassessmentComparison state={{...state,assembly:{...state.assembly,snapshot:{...state.assembly.snapshot,items:[b]}}}}/>);
 expect(screen.getByRole('cell',{name:'Selected note unavailable in this snapshot'})).toBeInTheDocument();expect(screen.queryByText('Note A full authored narrative')).not.toBeInTheDocument();
});
it('discloses same-note selection and excludes foreign encounter or unmarked notes',()=>{
 const {state,a,b}=data();b.fact.binding.target.encounter_id='foreign';const unmarked=structuredClone(a);unmarked.fact.id='not-a-note';unmarked.fact.source_identifiers=[];state.assembly.snapshot.items.push(unmarked);
 render(<ReassessmentComparison state={state}/>);expect(screen.queryByRole('option',{name:/note\/new/})).not.toBeInTheDocument();expect(screen.queryByRole('option',{name:/not-a-note/})).not.toBeInTheDocument();select(a,a);expect(screen.getByRole('status')).toHaveTextContent('same exact note');
});
it.each(['duplicate','malformed','contradictory','foreign','missing'] as const)('withholds %s stage references rather than guessing',kind=>{
 const {a}=data();const entries=a.fact.external_evidence as Record<string,unknown>[],associations=a.fact.associations as Record<string,unknown>[];
 if(kind==='duplicate')entries.push(structuredClone(entries[2]));
 if(kind==='malformed')entries[2].code='bad json';
 if(kind==='contradictory')associations[2].exact={kind:'circulatory_oxygen',id:'different',version:'1'};
 if(kind==='foreign')associations[2].scope={patient_id:'foreign',encounter_id:'synthetic-e1'};
 if(kind==='missing')a.fact.external_evidence=[];
 expect(reassessmentReference(a,'followup')).toBeUndefined();
});
it('retains full exact identities when delimiters collide and source order changes',()=>{
 const {state,a,b}=data();a.fact.id='note/x';a.fact.revision='y';b.fact.id='note';b.fact.revision='x/y';state.assembly.snapshot.items=[b,a];render(<ReassessmentComparison state={state}/>);select(a,b);
 expect(screen.getByRole('combobox',{name:'Note A'})).toHaveValue('["circulatory_event","note/x","y"]');expect(screen.getByRole('combobox',{name:'Note B'})).toHaveValue('["circulatory_event","note","x/y"]');
});

const duplicateMembers=[
 ['kind','"kind"'],['id','"id"'],['version','"version"'],
 ['kind',String.raw`"\u006bind"`],['id',String.raw`"\u0069d"`],['version',String.raw`"ver\u0073ion"`],
] as const;
it.each(duplicateMembers)('C1: withholds conflicting duplicate %s member with spelling %s and renders the warning',(field,spelling)=>{
 const {state,a,b}=data();const entries=b.fact.external_evidence as Record<string,unknown>[];
 const ref=JSON.parse(String(entries[2].code)) as Record<string,string>;
 const code='{'+JSON.stringify(field)+':"foreign",'+Object.entries(ref).map(([k,v])=>(k===field?spelling:JSON.stringify(k))+':'+JSON.stringify(v)).join(',')+'}';
 // Establish the dangerous old last-member-wins path with matching exact support.
 expect(JSON.parse(code)).toEqual(ref);entries[2].code=code;
 const before=JSON.stringify(state);expect(reassessmentReference(b,'followup')).toBeUndefined();
 render(<ReassessmentComparison state={state}/>);select(a,b);
 const row=screen.getAllByRole('row').find(r=>r.textContent?.includes('Follow-up ABG / evidence reference'))!;
 const cells=within(row).getAllByRole('cell');expect(cells[0]).toHaveTextContent('Revision: 1');
 expect(cells[1]).toHaveTextContent('Reference missing, ambiguous or inconsistent');expect(cells[1]).not.toHaveTextContent('corrected/revision');expect(JSON.stringify(state)).toBe(before);
});
it.each(['kind','id','version'])('C1: rejects identical repeated %s members too',field=>{
 const {b}=data(),entries=b.fact.external_evidence as Record<string,unknown>[],ref=JSON.parse(String(entries[2].code));
 entries[2].code='{'+JSON.stringify(field)+':'+JSON.stringify(ref[field])+','+JSON.stringify(ref).slice(1);
 expect(reassessmentReference(b,'followup')).toBeUndefined();
});
it.each([
 ' \t\r\n{ "version" : "corrected/revision", "id" : "fs-PH-60", "kind" : "circulatory_oxygen" }\r\n',
 String.raw`{"\u006bind":"circulatory_oxygen","\u0069d":"fs-PH-60","ver\u0073ion":"corrected\u002frevision"}`,
 String.raw`{"version":"corrected\/revision","kind":"circulatory_oxygen","id":"fs-PH-60"}`,
])('C1: preserves valid member order, whitespace and string escapes: %s',code=>{
 const {b}=data(),entries=b.fact.external_evidence as Record<string,unknown>[];entries[2].code=code;
 expect(reassessmentReference(b,'followup')).toEqual({kind:'circulatory_oxygen',id:'fs-PH-60',version:'corrected/revision'});
});
it('C1: accepts escaped punctuation inside values without treating it as object structure',()=>{
 const {b}=data(),entries=b.fact.external_evidence as Record<string,unknown>[],associations=b.fact.associations as Record<string,unknown>[];
 const ref={kind:'circulatory_oxygen',id:'record/"id",}\\\n\tΩ',version:'revision/"quoted"'};
 entries[2].code=JSON.stringify(ref);associations[2].exact=ref;
 expect(reassessmentReference(b,'followup')).toEqual(ref);
});
it.each([
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":1}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":null}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":{}}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":[]}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":""}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60"}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":"corrected/revision",}',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":"corrected/revision"}garbage',
 '{"kind":"circulatory_oxygen","id":"fs-PH-60","version":"corrected/revision","extra":"x"}',
 String.raw`{"kind":"circulatory_oxygen","id":"fs-PH-60","version":"bad\x20escape"}`,
])('C1: rejects invalid flat reference grammar: %s',code=>{
 const {b}=data();(b.fact.external_evidence as Record<string,unknown>[])[2].code=code;
 expect(reassessmentReference(b,'followup')).toBeUndefined();
});

it.each(['repository','patient','encounter'] as const)('M1: clears only comparison selections after a %s scope change and requires explicit reselection',boundary=>{
 const {state,a,b}=data(),onHandover=vi.fn();const view=render(<ReassessmentComparison state={state} onHandover={onHandover}/>);select(a,b);
 const next=structuredClone(state),scope=next.assembly.request.scope;
 if(boundary==='repository')scope.repository_cutoff.repository_id='replacement-repository';
 else if(boundary==='patient')scope.patient_id='replacement-patient';else scope.encounter_id='replacement-encounter';
 for(const note of next.assembly.snapshot.items){note.fact.binding.target.patient_id=scope.patient_id;note.fact.binding.target.encounter_id=scope.encounter_id;}
 const replacement=next.assembly.snapshot.items.find(i=>i.fact.id===a.fact.id)!;replacement.fact.description={raw_display:'Replacement content with reused identity'};replacement.expected_digest='b'.repeat(64);
 view.rerender(<ReassessmentComparison state={next} onHandover={onHandover}/>);
 for(const name of ['Note A','Note B'])expect(screen.getByRole('combobox',{name})).toHaveValue('');
 expect(screen.queryByRole('button',{name:'Add Note A to handover'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Add Note B to handover'})).not.toBeInTheDocument();expect(onHandover).not.toHaveBeenCalled();
 fireEvent.change(screen.getByRole('combobox',{name:'Note A'}),{target:{value:evidenceKey(replacement.fact)}});fireEvent.click(screen.getByRole('button',{name:'Add Note A to handover'}));expect(onHandover).toHaveBeenCalledExactlyOnceWith(replacement);
});
it('M1: same-repository refresh preserves both explicit choices and exact handover actions',()=>{
 const {state,a,b}=data(),onHandover=vi.fn();const view=render(<ReassessmentComparison state={state} onHandover={onHandover}/>);select(a,b);
 const next=structuredClone(state);next.state_context+='-refresh';next.assembly.request.scope.repository_cutoff.fact_watermark++;next.assembly.snapshot.items.reverse();
 view.rerender(<ReassessmentComparison state={next} onHandover={onHandover}/>);
 expect(screen.getByRole('combobox',{name:'Note A'})).toHaveValue(evidenceKey(a.fact));expect(screen.getByRole('combobox',{name:'Note B'})).toHaveValue(evidenceKey(b.fact));
 fireEvent.click(screen.getByRole('button',{name:'Add Note B to handover'}));expect(onHandover).toHaveBeenCalledExactlyOnceWith(next.assembly.snapshot.items.find(i=>i.fact.id===b.fact.id));
});
