import catalogueData from './data/antibiotic-catalogue.json';
import libraryData from './data/antibiotics-evidence.json';
import nationalData from './data/drug-specific-guidance.json';
import supplementalData from './data/supplemental-renal-crrt.json';
import policyData from './data/guidance-references.json';

// Isolated reference collection. No patient-state, prescribing or dosing imports.
export function assertUnreviewed(value:unknown):void {
 if(!value||typeof value!=='object')return;
 if(Array.isArray(value)){value.forEach(assertUnreviewed);return;}
 const record=value as Record<string,unknown>;
 if('review_status' in record&&record.review_status!=='unreviewed')throw Error('Reference review state is not unreviewed');
 if('clinical_use_eligible' in record&&record.clinical_use_eligible!==false)throw Error('Clinically eligible reference rejected');
 if('executable' in record&&record.executable!==false)throw Error('Executable reference rejected');
 Object.values(record).forEach(assertUnreviewed);
}
export const referenceDataValid=(()=>{try{[catalogueData,libraryData,nationalData,supplementalData,policyData].forEach(assertUnreviewed);return true;}catch{return false;}})();
export const catalogue=catalogueData,library=libraryData,nationalGuidance=nationalData,supplementalGuidance=supplementalData,policyReferences=policyData;
export type Medicine=typeof catalogue.records[number];
export type LibrarySource=typeof library.records[number];
export type SupplementalRecord=typeof supplementalGuidance.records[number];
export type SupplementalReference=SupplementalRecord['crrt'][number]&{remaining_gap?:string;pages?:number[]};
export type ReferenceMode='renal'|'crrt';
export const normalizeMedicine=(text:string)=>text.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
export function searchMedicines(query='',category=''){
 const terms=normalizeMedicine(query).split(' ').filter(Boolean);
 return catalogue.records.filter(r=>(!category||r.categories.includes(category))&&terms.every(term=>normalizeMedicine([r.name,...r.official_names,...r.aliases,...r.atc_codes,...r.categories].join(' ')).includes(term)));
}
export function medicineEntry(name:string){return catalogue.records.find(r=>normalizeMedicine(r.name)===normalizeMedicine(name));}
export function guidanceForMedicine(name:string){const entry=medicineEntry(name);return entry?nationalGuidance.records.find(r=>r.medicine_id===entry.id)??null:null;}
export function guidanceSource(id:string){return nationalGuidance.sources.find(r=>r.id===id);}
export function supplementalForMedicine(name:string){const entry=medicineEntry(name);return entry?supplementalGuidance.records.find(r=>r.medicine_id===entry.id)??null:null;}
export function supplementalSource(id:string){return supplementalGuidance.sources.find(r=>r.id===id);}
export function hasSupplementalDose(record:SupplementalRecord|null,mode:ReferenceMode){return !!record?.[mode].some(r=>r.status==='numerical_reference');}
export function supplementalModeState(record:SupplementalRecord|null,mode:ReferenceMode){
 const refs=record?.[mode]??[];
 if(hasSupplementalDose(record,mode))return 'dose_table';
 if(refs.some(r=>r.status==='no_adjustment_reference'))return 'no_adjustment';
 if(refs.some(r=>r.status==='loading_only_reference'))return 'loading_only';
 return refs.length?'review_gap':'not_mapped';
}
export const supplementalStateLabels:Record<string,string>={dose_table:'Source dose table',no_adjustment:'No adjustment stated',loading_only:'Loading only · maintenance via TDM',review_gap:'Dose gap · specialist review',not_mapped:'No reference mapped'};
export const guidanceCoverage={entries:nationalGuidance.records.length,indications:nationalGuidance.records.filter(r=>r.indications.items.length).length,renal:nationalGuidance.records.filter(r=>r.renal.sources.length).length,renalDose:nationalGuidance.records.filter(r=>r.renal.dose_text).length};
export const EVIDENCE_TYPES:Record<string,string>={guideline:'Guideline',guideline_chapter:'Guideline chapter',dosing_table:'Dosing reference',drug_label:'Drug label',safety_notice:'Safety notice'};
export function filterEvidence(query='',type='',jurisdiction=''){
 const terms=normalizeMedicine(query).split(' ').filter(Boolean);
 return library.records.filter(r=>(!type||r.source_type===type)&&(!jurisdiction||r.jurisdiction===jurisdiction)&&terms.every(term=>normalizeMedicine([r.evidence_id,r.title,r.issuer,r.source_version,...r.topics].join(' ')).includes(term)));
}
