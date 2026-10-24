import {describe,it,expect} from 'vitest';
import {quantityText,productLabel,extractLaboratory,laboratoryProjection,validateProductEntry} from '../src/transfusion/model';
describe('transfusion clarity and original evidence',()=>{
 it('keeps RDP, SDP, pools and concentrate dose bases distinct',()=>{
  expect(productLabel('platelets_rdp')).toContain('random donor');
  expect(productLabel('platelets_sdp')).toContain('apheresis');
  expect(quantityText({value:'2',unit:'pool',basis:'pool'})).toBe('2 pool');
  expect(quantityText({value:'1500',unit:'IU',basis:'factor_ix'})).toContain('factor ix');
  expect(quantityText(null)).toBe('Not documented');
 });
 it('rejects positive delivery for a product explicitly not given',()=>{
  expect(validateProductEntry({status:'not_given',count:'1',volume:''})).toMatch(/not given/i);
  expect(validateProductEntry({status:'stopped',count:'',volume:'25'})).toBeNull();
 });
 it('preserves original calcium identity, exact source revision and missing results',()=>{
  const source:any={fact:{id:'gas-1',revision:'r1',kind:'respiratory_record',measurements:[{concept:'ionised_calcium',label:'Ionised calcium',result:{kind:'numeric',value:'0.92',unit:{raw_display:'mmol/L'}}}]}};
  const rows=extractLaboratory({items:[],laboratory_reports:[],respiratory_records:[source]} as any);
  expect(rows).toHaveLength(1);expect(rows[0].label).toBe('Ionised calcium');expect(rows[0].value).toContain('0.92');expect(rows[0].source).toBe(source);
 });
});

it('retains same-ID cross-kind and cross-repository laboratory rows while collapsing exact repeats',()=>{
 const lab:any={repository:'repo-a',fact:{kind:'laboratory_report',id:'same',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9.0'}}]},digest:'a'.repeat(64)};
 const respiratory:any={...lab,fact:{kind:'respiratory_record',id:'same',revision:'1',measurements:[{source_component_id:'hb',label:'Hb',result:{kind:'numeric',raw_value:'9.0'}}]}};const elsewhere={...lab,repository:'repo-b'};
 const rows=extractLaboratory({laboratory_reports:[lab,lab,elsewhere],respiratory_records:[respiratory],items:[]} as any);expect(rows).toHaveLength(3);expect(rows.map(r=>r.source)).toEqual([lab,elsewhere,respiratory]);
});
it('withholds conflicting digest variants of an identical laboratory component',()=>{
 const source:any={repository:'repo',fact:{kind:'laboratory_report',id:'same',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9'}}]},digest:'a'.repeat(64)};
 expect(extractLaboratory({laboratory_reports:[source,{...source,digest:'b'.repeat(64)}],items:[]} as any)).toEqual([]);
});

it('preserves equal-valued serial laboratory sources with distinct IDs',()=>{
 const source:any={repository:'repo',fact:{kind:'laboratory_report',id:'first',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9'}}]},digest:'a'.repeat(64)};
 const later={...source,fact:{...source.fact,id:'later'}};expect(extractLaboratory({laboratory_reports:[source,later],items:[]} as any).map(r=>r.source.fact.id)).toEqual(['first','later']);
});
it('withholds conflicting content for an identical component even if the declared digest is repeated',()=>{
 const source:any={repository:'repo',fact:{kind:'laboratory_report',id:'same',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9'}}]},digest:'a'.repeat(64)};
 const changed=structuredClone(source);changed.fact.components[0].result.raw_value='8';expect(extractLaboratory({laboratory_reports:[source,changed],items:[]} as any)).toEqual([]);
});

it('exposes laboratory identity conflicts as invalid evidence rather than true absence',()=>{
 const source:any={repository:'repo',fact:{kind:'laboratory_report',id:'same',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9'}}]},digest:'a'.repeat(64)};
 const result=laboratoryProjection({laboratory_reports:[source,{...source,digest:'b'.repeat(64)}],items:[]} as any);expect(result.valid).toBe(false);expect(result.rows).toEqual([]);expect(result.error).toMatch(/conflict/i);expect(laboratoryProjection({laboratory_reports:[],items:[]} as any)).toEqual({valid:true,rows:[]});
});
it('detects source conflicts even when changed labels no longer match the M10 laboratory filter',()=>{
 const source:any={repository:'repo',fact:{kind:'laboratory_report',id:'same',revision:'1',components:[{source_component_id:'hb',test_code:{raw_display:'Hb'},result:{kind:'numeric',raw_value:'9'}}]},digest:'a'.repeat(64)};
 const changed=structuredClone(source);changed.fact.components[0].test_code.raw_display='Unmapped result';
 expect(laboratoryProjection({laboratory_reports:[source,changed],items:[]} as any).valid).toBe(false);
});
