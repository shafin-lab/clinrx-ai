import {expect,it} from 'vitest';
import {render,screen,within} from '@testing-library/react';
import catalogFixture from './fixtures/rf2-api.json';
import respiratoryFixture from './fixtures/respiratory-record.json';
import type {Catalog,Evidence} from '../src/api/rf2Client';
import type {RecordedTime,RespiratoryRecord,RespiratorySupportType} from '../src/respiratory/respiratoryTypes';
import {RespiratorySourceDialog} from '../src/respiratory/RespiratorySources';

const end:RecordedTime={status:'known',precision:'instant',value:'2026-10-08T09:10:00Z',lower:null,upper:null,uncertainty:null};
const cases:{type:RespiratorySupportType;until:RecordedTime|null;device?:string;expected:string}[]=[
 {type:'invasive',until:end,expected:'Invasive ventilation · Ends 08 Oct, 09:10 UTC'},
 {type:'hfnc',until:null,expected:'HFNC · End not recorded'},
 {type:'other',device:'Recorded custom interface',until:{...end,precision:'bounded',value:null,lower:'2026-10-08T09:10:00Z',upper:'2026-10-08T09:20:00Z',uncertainty:'Source estimates the interval'},expected:'Recorded custom interface · End between 2026-10-08T09:10:00Z and 2026-10-08T09:20:00Z · Source uncertainty: Source estimates the interval'},
 {type:'nasal_cannula',until:{...end,status:'unknown',value:null},expected:'Nasal prongs / cannula · End unknown'},
];

it.each(cases)('makes $type support and its recorded end readable without inventing timing',async({type,until,device,expected})=>{
 const catalog=structuredClone(catalogFixture.catalog) as unknown as Catalog;
 const fact=structuredClone(respiratoryFixture) as RespiratoryRecord;
 fact.category='support';fact.context.support_episode={type,until};
 if(device)fact.context.oxygen_device=device;
 const evidence:Evidence={repository:catalog.repository,fact,canonical_fact:'{}',digest:'a'.repeat(64),ingestion:{repository_id:catalog.repository,ingestion_sequence:1},cutoff:catalog.cutoff.fact_watermark,terminal_reference:{kind:fact.kind,id:fact.id,version:fact.revision},superseded:false,metadata:null};
 render(<RespiratorySourceDialog evidence={evidence} current transport={{history:async()=>[evidence]}} onClose={()=>{}}/>);
 const field=screen.getByText('support episode').closest('div')!;
 expect(within(field).getByRole('definition')).toHaveTextContent(expected);
 expect(field).not.toHaveTextContent('[object Object]');
 expect(await screen.findByText('Version '+fact.revision)).toBeVisible();
});
