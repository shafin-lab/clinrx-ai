import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,within} from '@testing-library/react';
import fixture from './fixtures/icuFlowsheet.json';
import {decodeCirculatoryState} from '../src/api/circulatoryDecoders';
import {sourceUnitMappings} from '../src/demo/sourceUnitMappings';
import {ComprehensiveDemo} from '../src/demo/ComprehensiveDemo';
import type {CirculatoryClient} from '../src/api/circulatoryClient';
const items=()=>decodeCirculatoryState(structuredClone(fixture)).assembly.snapshot.items;
afterEach(cleanup);
it.each([
 ['fs-IO-output_urine-15','Event amount','mL'],
 ['fs-D-ORDER','Prescribed rate','mcg/kg/min'],
 ['fs-D-CHANGE','Delivered rate','mcg/kg/min'],
])('displays the actual quantity mapping for %s',async(id,label,unit)=>{
 const state=decodeCirculatoryState(structuredClone(fixture)),item=state.assembly.snapshot.items.find(i=>i.fact.id===id)!;
 expect(sourceUnitMappings(item)).toContainEqual({label,unit,status:'unresolved'});
 const client={circulatoryState:vi.fn().mockResolvedValue({data:state}),circulatoryPrepare:vi.fn(),circulatoryExecute:vi.fn()};
 render(<ComprehensiveDemo client={client as unknown as CirculatoryClient} config={{start:fixture.assembly_request.scope.review_start,end:fixture.assembly_request.scope.review_end,releasedExample:'released',withheldExample:'withheld'}}/>);
 await screen.findByRole('heading',{name:'Cardiac output + echo'});fireEvent.click(screen.getByRole('button',{name:'Evidence library'}));
 fireEvent.change(screen.getByLabelText('Search recorded evidence'),{target:{value:id}});
 const source=screen.getAllByRole('button',{name:/^Inspect /}).find(b=>b.textContent?.includes(id))!;fireEvent.click(source);
 const inspector=screen.getByRole('complementary',{name:'Selected source evidence'});
 expect(within(inspector).getByText(label+': unresolved · '+unit)).toBeInTheDocument();
 expect(inspector).not.toHaveTextContent('Not supplied / not applicable');expect(client.circulatoryPrepare).not.toHaveBeenCalled();expect(client.circulatoryExecute).not.toHaveBeenCalled();
});
it('distinguishes rate and concentration and preserves missing quantities without inferring applicability',()=>{
 const event=items().find(i=>i.fact.id==='fs-D-CHANGE')!;
 expect(sourceUnitMappings(event)).toEqual([{label:'Delivered rate',unit:'mcg/kg/min',status:'unresolved'},{label:'Delivered concentration',unit:'mg/mL',status:'unresolved'}]);
 expect(sourceUnitMappings(items().find(i=>i.fact.id==='fs-D-PAUSE')!)).toEqual([]);
 expect(sourceUnitMappings(items().find(i=>i.fact.id==='fs-PH-15')!)).toEqual([{label:'Result',unit:'1',status:'unresolved'}]);
});
