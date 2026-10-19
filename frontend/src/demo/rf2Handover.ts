import {type Pin,key} from '../api/rf2Client';
export interface SavedRF2 {version:2;repository:string;patient:'synthetic-p1';encounter:'synthetic-e1';savedAt:string;pins:Pin[]}
export const storageKey=(repository:string)=>'clinrx.synthetic.handover.v2:'+JSON.stringify([repository,'synthetic-p1','synthetic-e1']);
export function decodeRF2Saved(raw:string,repository:string):SavedRF2{
 if(raw.length>131072)throw Error('Saved handover exceeds bounds');const v=JSON.parse(raw) as SavedRF2;
 if(JSON.stringify(v)!==raw||!v||Object.keys(v).sort().join()!=='encounter,patient,pins,repository,savedAt,version'||v.version!==2||v.repository!==repository||v.patient!=='synthetic-p1'||v.encounter!=='synthetic-e1'||typeof v.savedAt!=='string'||!Number.isFinite(Date.parse(v.savedAt))||!Array.isArray(v.pins)||v.pins.length>32)throw Error('Saved handover cannot be confirmed; original bytes preserved');
 const keys=new Set<string>();for(const p of v.pins){if(!p||Object.keys(p).sort().join()!=='cutoff,digest,ingestion,reference,repository'||p.repository!==repository||!p.reference||Object.keys(p.reference).sort().join()!=='id,kind,version'||!Object.values(p.reference).every(x=>typeof x==='string'&&x.length>0&&x.length<=256)||!(p.reference.kind==='observation'||p.reference.kind.startsWith('circulatory_'))||!/^[a-f0-9]{64}$/.test(p.digest)||!Number.isSafeInteger(p.ingestion)||p.ingestion<1||!Number.isSafeInteger(p.cutoff)||p.cutoff<p.ingestion||keys.has(key(p)))throw Error('Invalid handover pin');keys.add(key(p));}return v;
}
