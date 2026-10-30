export interface CompleteNcdcSource {id:string;name:string;version:string;url:string;sha256:string}
export interface CompleteNcdcRow {id:string;label:string;firstLine:string;alternative:string;comments:string;pdfPages:number[]}
export interface CompleteNcdcSection {infectionId:string;section:string;name:string;pdfPages:number[];rows:CompleteNcdcRow[];notes:{text:string;pdfPages:number[]}[];figures:{imagePath:string;pdfPage:number;caption:string;primary?:boolean}[];sourceText:string}
export interface CompleteNcdcGuidance {source:CompleteNcdcSource;sections:CompleteNcdcSection[]}
export const ncdcSnapshotHash='0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a';
export function formatTreatment(text:string):string[]{
 const result:string[]=[];let paragraph:string[]=[];
 const flush=()=>{if(paragraph.length){result.push(paragraph.join(' ').replace(/\s+/g,' ').trim());paragraph=[];}};
 for(const line of text.split(/\r?\n/)){
  const value=line.trim();
  if(!value){flush();continue;}
  if(/^(or|\+|\+\/-|±)$/i.test(value)){flush();result.push(/^or$/i.test(value)?'OR':value);}
  else paragraph.push(value);
 }
 flush();return result;
}
export function doseNotes(text:string):string[]{
 const value=text.replace(/\s+/g,' '),notes:string[]=[];
 if(/teicoplanin/i.test(value)&&/followed by\s+6\s*-\s*12\s*mg\b/i.test(value)&&!/followed by\s+6\s*-\s*12\s*mg\s*\/\s*kg/i.test(value))notes.push('NCDC prints maintenance as 6–12 mg; the weight basis is not stated. Confirm the intended dose before prescribing.');
 if(/ceftriaxone\s+500\s+IM/i.test(value))notes.push('The unit for ceftriaxone 500 is not printed in this NCDC row; confirm it before prescribing.');
 if(/penicillin V\s+250\s*-\s*500\s+q6h/i.test(value))notes.push('The unit for penicillin V 250–500 is not printed in this NCDC row.');
 if(/vancom\w*\s+15\s*-\s*20\s*mg\/kg\/day.*every\s+8\s*-\s*12/i.test(value))notes.push('NCDC prints a daily dose basis with an 8–12 hourly interval; confirm the intended dosing basis.');
 return notes;
}
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const string=(v:unknown):v is string=>typeof v==='string';
const pages=(v:unknown):v is number[]=>Array.isArray(v)&&v.length>0&&v.every(p=>Number.isInteger(p)&&p>0&&p<=157);
export function validateCompleteGuidance(data:unknown):data is CompleteNcdcGuidance{
 if(!object(data)||!object(data.source)||data.source.id!=='ncdc'||data.source.sha256!==ncdcSnapshotHash||!string(data.source.name)||!string(data.source.version)||data.source.url!=='https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf'||!Array.isArray(data.sections)||!data.sections.length)return false;
 const ids=new Set<string>(),rowIds=new Set<string>();
 for(const section of data.sections){
  if(!object(section)||!string(section.section)||!/^\d+\.\d+$/.test(section.section)||section.infectionId!=='ncdc-'+section.section.replaceAll('.','-')||!string(section.name)||ids.has(String(section.infectionId))||!pages(section.pdfPages)||!Array.isArray(section.rows)||!Array.isArray(section.notes)||!Array.isArray(section.figures)||!string(section.sourceText))return false;
  ids.add(String(section.infectionId));
  for(const row of section.rows){if(!object(row)||!string(row.id)||!row.id||rowIds.has(row.id)||!string(row.label)||!string(row.firstLine)||!string(row.alternative)||!string(row.comments)||!pages(row.pdfPages))return false;rowIds.add(row.id);}
  for(const note of section.notes){if(!object(note)||!string(note.text)||!pages(note.pdfPages))return false;}
  for(const figure of section.figures){if(!object(figure)||!string(figure.imagePath)||!/^\/assets\/infection-sources\/ncdc-sections\/[a-zA-Z0-9_-]+\.png$/.test(figure.imagePath)||!pages([figure.pdfPage])||!string(figure.caption)||figure.primary!==undefined&&typeof figure.primary!=='boolean')return false;}
 }
 return true;
}
