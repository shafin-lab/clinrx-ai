export interface GuidanceSource {id:string;name:string;version:string;url:string;sha256:string}
export interface GuidanceGroup {id:string;name:string}
export interface GuidanceRegimen {id:string;label:string;instructions:string;duration:string|null;gaps:string[];source_branch?:boolean}
export interface InfectionCase {id:string;label:string;sourceId:string;locator:string;pdfPages:number[];regimens:GuidanceRegimen[];notes:string[];gaps:string[];management?:string[];reference?:{infectionId:string;label:string}}
export interface Infection {id:string;groupId:string;name:string;aliases:string[];cases:InfectionCase[]}
export interface InfectionCatalogue {version:string;executable:false;clinical_use_eligible:false;review_status:'unreviewed';sources:GuidanceSource[];groups:GuidanceGroup[];infections:Infection[]}
export function formatSourceText(text:string):string{return text.split(/\n\s*\n/).map(paragraph=>paragraph.replace(/\s+/g,' ').trim()).join('\n\n');}
const normalize=(s:string)=>s.normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
// Clinical synonyms belong to the source crosswalk; fuzzy case merging would be unsafe.
export function effectiveCases(cases:InfectionCase[]):InfectionCase[]{
 const result=new Map<string,InfectionCase>();
 for(const c of cases){if(c.sourceId!=='ncdc')continue;const key=normalize(c.label);if(!result.has(key))result.set(key,c);}
 return [...result.values()];
}
export function filterInfections(infections:Infection[],groupId:string,query:string):Infection[]{
 const terms=normalize(query).split(' ').filter(Boolean);
 return infections.filter(i=>i.groupId===groupId&&terms.every(t=>normalize([i.name,...i.aliases,...i.cases.map(c=>c.label)].join(' ')).includes(t)));
}
function record(v:unknown):v is Record<string,unknown>{return typeof v==='object'&&v!==null&&!Array.isArray(v);}
function strings(v:unknown):v is string[]{return Array.isArray(v)&&v.every(x=>typeof x==='string');}
function text(v:unknown):v is string{return typeof v==='string'&&v.trim().length>0;}
function referenceOnly(v:unknown):boolean{
 if(Array.isArray(v))return v.every(referenceOnly);
 if(!record(v))return true;
 if('executable' in v&&v.executable!==false||'clinical_use_eligible' in v&&v.clinical_use_eligible!==false||'review_status' in v&&v.review_status!=='unreviewed')return false;
 return Object.values(v).every(referenceOnly);
}
export function validateCatalogue(value:unknown):value is InfectionCatalogue{
 if(!record(value)||!referenceOnly(value)||value.executable!==false||value.clinical_use_eligible!==false||value.review_status!=='unreviewed'||!text(value.version))return false;
 if(!Array.isArray(value.sources)||!Array.isArray(value.groups)||!Array.isArray(value.infections))return false;
 const sources=new Set<string>(),groups=new Set<string>(),ids=new Set<string>(),caseIds=new Set<string>(),regimenIds=new Set<string>();
 for(const s of value.sources){if(!record(s)||!text(s.id)||s.id!=='ncdc'||sources.has(s.id)||!text(s.name)||!text(s.version)||typeof s.url!=='string'||!/^https:\/\//.test(s.url)||typeof s.sha256!=='string'||!/^[a-f\d]{64}$/i.test(s.sha256))return false;sources.add(s.id);}
 for(const g of value.groups){if(!record(g)||!text(g.id)||groups.has(g.id)||!text(g.name))return false;groups.add(g.id);}
 for(const i of value.infections){
  if(!record(i)||!text(i.id)||ids.has(i.id)||!text(i.groupId)||!groups.has(i.groupId)||!text(i.name)||!strings(i.aliases)||!Array.isArray(i.cases))return false;ids.add(i.id);
  for(const c of i.cases){
   if(!record(c)||!text(c.id)||caseIds.has(c.id)||!text(c.label)||!text(c.sourceId)||!sources.has(c.sourceId)||!text(c.locator)||!Array.isArray(c.pdfPages)||!c.pdfPages.length||!c.pdfPages.every(p=>Number.isInteger(p)&&p>0)||!Array.isArray(c.regimens)||!strings(c.notes)||!strings(c.gaps))return false;caseIds.add(c.id);
   if(c.management!==undefined&&!strings(c.management)||c.reference!==undefined&&(!record(c.reference)||!text(c.reference.infectionId)||!text(c.reference.label)))return false;
   for(const r of c.regimens){if(!record(r)||!text(r.id)||regimenIds.has(r.id)||!text(r.label)||!text(r.instructions)||r.duration!==null&&typeof r.duration!=='string'||!strings(r.gaps)||r.source_branch!==undefined&&typeof r.source_branch!=='boolean')return false;regimenIds.add(r.id);}
  }
 }
 for(const i of value.infections as unknown as Infection[]){for(const c of i.cases){if(c.reference){const target=(value.infections as unknown as Infection[]).find(t=>t.id===c.reference!.infectionId);if(c.regimens.length||!target||!target.cases.length||target.id===i.id||target.groupId!==i.groupId||target.cases.some(t=>t.reference))return false;}}}
 return sources.size>0&&groups.size>0&&ids.size>0;
}
