import {afterEach,expect,it} from 'vitest';
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
