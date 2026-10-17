import {describe,it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import fixtures from './fixtures/circulatory.json';
import {CirculatoryClient} from '../src/api/circulatoryClient';
import {CirculatoryReview} from '../src/patient/CirculatoryReview';
import {decodeCirculatoryExecution as execution} from '../src/api/circulatoryDecoders';
const scope={patient_id:'synthetic-p1',encounter_id:'synthetic-e1'};
const config={start:'2026-10-08T08:00:00+00:00',end:'2026-10-08T10:00:00+00:00'};
afterEach(cleanup);
function mockClient(){return {circulatoryLookup:vi.fn().mockResolvedValue({data:execution(fixtures.released,scope)})};}
describe('PR23 retained lookup identity',()=>{
  it.each(['failed','not_found','malformed'])('clears result A when lookup B is %s',async reason=>{
    const client=mockClient();render(<CirculatoryReview client={client as unknown as CirculatoryClient} config={config}/>);
    const input=screen.getByLabelText('Retained circulatory execution UUID');
    fireEvent.change(input,{target:{value:fixtures.released.execution_id}});
    fireEvent.click(screen.getByRole('button',{name:'Look up retained circulatory execution'}));await screen.findByText('Retained decision');
    let fail!:(error:unknown)=>void;client.circulatoryLookup.mockImplementation(()=>new Promise((_,reject)=>{fail=reject;}));
    fireEvent.change(input,{target:{value:fixtures.prepared2.execution_id}});
    fireEvent.click(screen.getByRole('button',{name:'Look up retained circulatory execution'}));
    expect(screen.queryByText('Retained decision')).toBeNull();
    fail(reason==='not_found'?new (await import('../src/api/client')).ApiFailure('not_found'):new Error(reason));
    await screen.findByRole('alert');expect(screen.queryByText('Retained decision')).toBeNull();
    expect(client.circulatoryLookup.mock.calls[1][0]).toBe(fixtures.prepared2.execution_id);
  });
});
