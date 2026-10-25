import {expect,it} from 'vitest';
import complete from '../src/infectionLibrary/data/ncdc-complete-guidance.json';
import {supplementaryEntries,supplementaryFor,supplementarySources} from '../src/infectionLibrary/supplementaryCatalogue';

it('uses one canonical recent source per work, with intact HTTPS URLs and explicit publication versions',()=>{
 const sources=Object.values(supplementarySources);
 expect(new Set(sources.map(s=>s.id)).size).toBe(sources.length);
 expect(new Set(sources.map(s=>s.url)).size).toBe(sources.length);
 for(const source of sources){
  expect(source.year).toBeGreaterThanOrEqual(2023);expect(source.year).toBeLessThanOrEqual(2026);
  expect(source.version).toContain(String(source.year));
  expect(source.url).not.toMatch(/\s/);expect(new URL(source.url).protocol).toBe('https:');
  expect(supplementaryEntries.some(entry=>entry.sourceId===source.id)).toBe(true);
 }
});

it('binds every reference to real NCDC infections and rows, without duplicate entries or repeated clinical questions',()=>{
 expect(new Set(supplementaryEntries.map(entry=>entry.id)).size).toBe(supplementaryEntries.length);
 expect(new Set(supplementaryEntries.map(entry=>entry.sourceId+'|'+entry.title)).size).toBe(supplementaryEntries.length);
 for(const entry of supplementaryEntries){
  expect(supplementarySources[entry.sourceId]).toBeDefined();
  expect(entry.why.trim()).not.toBe('');expect(entry.appliesTo.trim()).not.toBe('');
  expect(entry.limits.trim()).not.toBe('');expect(entry.difference.trim()).not.toBe('');
  for(const binding of entry.bindings){
   const section=complete.sections.find(s=>s.infectionId===binding.infectionId);
   expect(section,entry.id).toBeDefined();
   for(const rowId of binding.rowIds??[])expect(section!.rows.some(row=>row.id===rowId),`${entry.id}/${rowId}`).toBe(true);
  }
 }
 for(const section of complete.sections){
  for(const row of [undefined,...section.rows]){
   const result=supplementaryFor(section.infectionId,row?.id);
   expect(new Set(result.map(entry=>entry.id)).size).toBe(result.length);
   expect(new Set(result.map(entry=>entry.sourceId)).size).toBe(result.length);
  }
 }
});

it('does not guess a clinical situation when a row is missing, unknown or belongs to another infection',()=>{
 const teicoplanin=(row?:string)=>supplementaryFor('ncdc-1-1',row).some(entry=>entry.id==='ie-teicoplanin');
 expect(teicoplanin()).toBe(false);expect(teicoplanin('unknown')).toBe(false);
 expect(teicoplanin('ncdc-17-4-source-row-6')).toBe(false);
 expect(supplementaryFor('unknown','ncdc-1-1-source-row-3')).toEqual([]);
});
