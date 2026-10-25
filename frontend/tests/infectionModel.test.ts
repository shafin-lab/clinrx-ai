import {expect,it} from 'vitest';
import {effectiveCases,filterInfections,validateCatalogue,type InfectionCase} from '../src/infectionLibrary/model';

const treatment=(id:string,label:string,sourceId:string):InfectionCase=>({id,label,sourceId,locator:'Printed page 83',pdfPages:[90],regimens:[{id:id+'-r',label:'Primary guidance',instructions:'Source treatment',duration:null,gaps:[]}],notes:[],gaps:[]});
it('excludes non-NCDC contexts even when their clinical label is distinct',()=>{
 const cases=[treatment('j-ward','Adult inpatient ward','jipmer'),treatment('n-ward','Adult inpatient ward','ncdc'),treatment('j-extra','Uncovered clinical situation','jipmer')];
 expect(effectiveCases(cases).map(c=>c.id)).toEqual(['n-ward']);
});
it('does not merge ward with ICU, or adult with neonatal guidance',()=>{
 expect(effectiveCases([treatment('ward','Adult ward','ncdc'),treatment('icu','Adult ICU','ncdc'),treatment('neo','Neonatal ICU','ncdc')]).map(c=>c.id)).toEqual(['ward','icu','neo']);
});
it('searches infection aliases and clinical situations within the selected group',()=>{
 const data=[{id:'cap',groupId:'resp',name:'Community-acquired pneumonia',aliases:['CAP'],cases:[treatment('ward','Inpatient ward','ncdc')]},{id:'renal',groupId:'urine',name:'Renal abscess',aliases:[],cases:[]}];
 expect(filterInfections(data,'resp','CAP').map(x=>x.id)).toEqual(['cap']);
 expect(filterInfections(data,'resp','community acquired').map(x=>x.id)).toEqual(['cap']);
 expect(filterInfections(data,'resp','ward').map(x=>x.id)).toEqual(['cap']);
 expect(filterInfections(data,'resp','renal')).toEqual([]);
});
it('rejects executable guidance and unknown provenance before a reference can render',()=>{
 const base={version:'1',executable:false,clinical_use_eligible:false,review_status:'unreviewed',sources:[{id:'ncdc',name:'NCDC',version:'2025',url:'https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf',sha256:'a'.repeat(64)}],groups:[{id:'resp',name:'Respiratory'}],infections:[{id:'cap',groupId:'resp',name:'CAP',aliases:[],cases:[treatment('c','Ward','ncdc')]}]};
 expect(validateCatalogue(base)).toBe(true);
 expect(validateCatalogue({...base,sources:[...base.sources,{...base.sources[0],id:'jipmer'}]})).toBe(false);
 expect(validateCatalogue({...base,executable:true})).toBe(false);
 expect(validateCatalogue({...base,infections:[{...base.infections[0],cases:[{...base.infections[0].cases[0],clinical_use_eligible:true}]}]})).toBe(false);
 expect(validateCatalogue({...base,infections:[{...base.infections[0],cases:[treatment('c','Ward','other')]}]})).toBe(false);
 expect(validateCatalogue({...base,infections:[...base.infections,...base.infections]})).toBe(false);
});
