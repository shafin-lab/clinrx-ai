import type {PrescriptionDetails} from '../api/antibioticClient';
export const frequencies=['Every 4 hours','Every 6 hours','Every 8 hours','Every 12 hours','Every 24 hours','Every 48 hours','Once daily','Twice daily','Three times daily','Once only'];
export function parseDose(text:string){const m=/^((?:0|[1-9]\d*)(?:\.\d+)?|\.\d+)\s*(mg|g|IU)$/i.exec(text.trim());if(!m||!Number.isFinite(Number(m[1]))||Number(m[1])<=0)throw Error('Enter a positive dose with its unit, for example 500 mg. Supported units: mg, g, IU.');return {amount:m[1].startsWith('.')?'0'+m[1]:m[1],unit:(m[2].toLowerCase()==='iu'?'IU':m[2].toLowerCase()) as 'mg'|'g'|'IU'};}
export function frequencyChoice(text:string){return !text?'':frequencies.includes(text)?text:'custom';}
export function prescriptionSchedule(details:PrescriptionDetails){return [details.frequency,details.duration_review?'Duration / review: '+details.duration_review:'',details.administration_instructions?'Administration instructions: '+details.administration_instructions:''].filter(Boolean).join('; ');}
export function localEventTime(point:string){if(!point)return '';const date=new Date(point);if(!Number.isFinite(date.getTime()))return '';const pad=(v:number)=>String(v).padStart(2,'0');return date.getFullYear()+'-'+pad(date.getMonth()+1)+'-'+pad(date.getDate())+'T'+pad(date.getHours())+':'+pad(date.getMinutes())+':'+pad(date.getSeconds());}
export function eventTimeISO(value:string,originalPoint?:string){
 if(!value)return '';const date=new Date(value);if(!Number.isFinite(date.getTime())||localEventTime(date.toISOString()).slice(0,value.length)!==value)throw Error('Enter a valid local date and time.');
 const stamp=date.getTime(),offset=date.getTimezoneOffset(),offsets=new Set([offset,new Date(stamp-86400000).getTimezoneOffset(),new Date(stamp+86400000).getTimezoneOffset()]);
 const candidates=[...offsets].map(candidate=>stamp+(candidate-offset)*60000).filter(candidate=>localEventTime(new Date(candidate).toISOString()).slice(0,value.length)===value);
 if(candidates.length>1){const original=originalPoint?new Date(originalPoint):undefined;const preserved=original&&localEventTime(originalPoint!).slice(0,10)===value.slice(0,10)?candidates.find(candidate=>new Date(candidate).getTimezoneOffset()===original.getTimezoneOffset()):undefined;if(preserved!==undefined)return new Date(preserved).toISOString();throw Error('This local time occurs twice. In Source details, enter the exact source timestamp with its UTC offset.');}
 return date.toISOString();
}
export function checkSourceTime(value:string){
 const match=/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d{1,6})?(Z|([+-])(\d{2}):(\d{2}))$/.exec(value);
 if(!match||Number(match[4]??0)>23||Number(match[5]??0)>59||!Number.isFinite(Date.parse(value)))throw Error('Enter a source date and time with its UTC offset.');
 const offset=match[2]==='Z'?0:(match[3]==='+'?1:-1)*(Number(match[4])*60+Number(match[5]));
 if(new Date(Date.parse(value)+offset*60000).toISOString().slice(0,19)!==match[1])throw Error('Enter a valid source date and time.');
 return value;
}
