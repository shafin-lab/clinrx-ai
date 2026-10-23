import {describe,it,expect} from 'vitest';
import {quantityText,productLabel,extractLaboratory,validateProductEntry} from '../src/transfusion/model';
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
