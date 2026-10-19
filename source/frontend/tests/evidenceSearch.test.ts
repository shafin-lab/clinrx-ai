import {expect,it} from 'vitest';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {matchesEvidenceSearch,bloodGasLabel} from '../src/demo/evidenceSearch';
const items=decodeCirculatoryState({...structuredClone(fixture),execution_enabled:false}).assembly.snapshot.items;
const arterial=structuredClone(items.find(i=>i.fact.id==='fs-PH-60')!);
arterial.fact.collected={...(arterial.fact.collected as object),source_timestamp:'2026-10-08T09:45:00Z'};
// The model's recorded time remains visible as supplied; search never calculates a replacement time.
it.each(['ABG 09:45','arterial pH 09:45','  abg   09:45  ','09:45','2026-10-08'])('finds the arterial source by %s',query=>{expect(matchesEvidenceSearch(arterial,query)).toBe(true);});
it('keeps venous samples distinct, without guessing ABG from a gas name',()=>{
 const venous=structuredClone(arterial);venous.fact.sample_type='central_venous';
 expect(matchesEvidenceSearch(venous,'ABG 09:45')).toBe(false);expect(matchesEvidenceSearch(venous,'VBG 09:45')).toBe(true);
 const unknown=structuredClone(arterial);unknown.fact.sample_type='unknown';expect(matchesEvidenceSearch(unknown,'ABG')).toBe(false);expect(bloodGasLabel(unknown)).toBe('unknown sample');
});
it('does not match a note as ABG or treat a time mentioned in its narrative as the note source time',()=>{
 const note=structuredClone(items.find(i=>i.fact.kind==='circulatory_event')!);note.fact.description={raw_display:'Discuss ABG pH at 09:45'};
 expect(matchesEvidenceSearch(note,'ABG 09:45')).toBe(false);expect(matchesEvidenceSearch(note,'09:45')).toBe(false);
});
it('preserves time spelling and offsets without inferring equivalent time or day',()=>{
 expect(matchesEvidenceSearch(arterial,'ABG 10:45')).toBe(false);expect(matchesEvidenceSearch(arterial,'ABG 2026-10-09')).toBe(false);
 const other=structuredClone(arterial);other.fact.collected={...(other.fact.collected as object),source_timestamp:'2026-10-08T10:45:00+01:00'};
 expect(matchesEvidenceSearch(other,'ABG 09:45')).toBe(false);expect(matchesEvidenceSearch(other,'ABG 10:45')).toBe(true);
});
it('retains exact quantities, units, identity, quality and unplaced unknown times without mutation',()=>{
 const before=JSON.stringify(arterial);expect(matchesEvidenceSearch(arterial,'fs-PH-60')).toBe(true);expect(bloodGasLabel(arterial)).toBe('Arterial blood gas (ABG)');expect(JSON.stringify(arterial)).toBe(before);
 const unplaced=items.find(i=>i.fact.id==='m7-UNPLACED')!;expect(matchesEvidenceSearch(unplaced,'09:45')).toBe(false);expect(matchesEvidenceSearch(unplaced,'')).toBe(true);
});
