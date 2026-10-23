import {it,expect} from 'vitest';
import {M10Client} from '../src/transfusion/client';
import type {M10Command} from '../src/transfusion/types';
const origin=(globalThis as typeof globalThis&{process?:{env:Record<string,string|undefined>}}).process?.env.CLINRX_M10_SEVEN_ORIGIN;
it.skipIf(!origin)('verifies seven products, repeat PRBC, correction, replay and history through the real client on disposable storage',async()=>{
 if(origin!=='http://127.0.0.1:5261')throw Error('This write verification is restricted to the disposable M10 example origin.');
 const client=new M10Client((input,init)=>globalThis.fetch(new URL(String(input),origin),{...init,headers:{...init?.headers,Origin:origin!}}));
 const before=await client.catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');expect(before.items).toHaveLength(0);
 const commands:M10Command[]=[];const saved:any[]=[];
 const values=[['prbc','prbc','6','count','units','component units'],['prbc','prbc','4','count','units','component units'],['plasma','ffp','10','count','units','component units'],['platelets','platelets_sdp','1','count','units','apheresis units'],['platelets','platelets_rdp','6','count','units','component units'],['cryoprecipitate','cryo','10','count','units','component units'],['pcc','pcc','1000','dose','IU','factor IX'],['fibrinogen_concentrate','fibrinogen_concentrate','2','dose','g','fibrinogen_concentrate']];
 for(const [family,preparation,value,dimension,unit,basis] of values){
  const command:M10Command={repository:before.repository,command_id:crypto.randomUUID(),id:crypto.randomUUID(),revision:crypto.randomUUID(),kind:dimension==='dose'?'haemostatic_medication_course':'transfusion_administration',predecessor:null,predecessor_digest:null,correction_reason:null,source_record:'seven-product-example-'+crypto.randomUUID(),source_issuer:'Disposable synthetic acceptance example',actor:'M10 workflow verification',recorded_at:'2026-10-08T09:30:00Z',available_at:'2026-10-08T09:30:00Z',patient_id:'synthetic-p1',encounter_id:'synthetic-e1',data:{title:'Synthetic '+preparation+' administration',product:{family,preparation,label:preparation,factor_basis:family==='pcc'?'factor IX':null,modifications:family==='prbc'?[{name:'leukodepleted',value:'yes',source:'Synthetic source bag',verification:'source_reported'},{name:'irradiated',value:'no',source:'Synthetic source bag',verification:'source_reported'}]:[]},occurred:{status:'known',precision:'instant',value:'2026-10-08T09:00:00Z'},delivery_id:crypto.randomUUID(),grain:'component_episode',status:'completed',indication:'Synthetic acceptance scenario',amounts:[{dimension,value,unit,basis}],promote_to_medication:dimension==='dose'}};
  await client.validate(command);commands.push(command);saved.push(await client.save(command));
 }
 await client.save(commands[0]);
 const read=()=>client.catalog('2026-10-08T08:00:00Z','2026-10-08T10:00:00Z');let view=await read();
 const quantities=Object.fromEntries(view.totals.groups.map((g:any)=>[g.preparation,g.known_subtotal+' '+g.unit]));
 expect(quantities).toEqual({prbc:'10 units',ffp:'10 units',platelets_sdp:'1 units',platelets_rdp:'6 units',cryo:'10 units',pcc:'1000 IU',fibrinogen_concentrate:'2 g'});expect(view.medication_exposures).toHaveLength(2);expect(view.items.filter(e=>e.fact.kind==='transfusion_administration')).toHaveLength(6);
 const original=commands[1],source=saved[1];const correction={...original,command_id:crypto.randomUUID(),revision:crypto.randomUUID(),predecessor:{kind:original.kind,id:original.id,version:original.revision},predecessor_digest:source.digest,correction_reason:'Synthetic correction verification',data:{...original.data,amounts:[{dimension:'count',value:'5',unit:'units',basis:'component units'}]}};
 const changed=await client.save(correction);view=await read();expect(view.totals.groups.find((g:any)=>g.preparation==='prbc').known_subtotal).toBe('11');
 const restore={...correction,command_id:crypto.randomUUID(),revision:crypto.randomUUID(),predecessor:{kind:original.kind,id:original.id,version:correction.revision},predecessor_digest:changed.digest,data:original.data};await client.save(restore);view=await read();expect(view.totals.groups.find((g:any)=>g.preparation==='prbc').known_subtotal).toBe('10');
 const history=await client.history({repository:view.repository,reference:{kind:original.kind,id:original.id,version:restore.revision},cutoff:typeof view.cutoff==='number'?view.cutoff:view.cutoff.fact_watermark,review_end:'2026-10-08T10:00:00Z',offset:0,limit:128});expect(history.items).toHaveLength(3);
},60000);
