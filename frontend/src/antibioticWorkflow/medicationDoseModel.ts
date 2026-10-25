import type {AutomaticRenalModel} from './automaticRenalModel';
import {blankDoseContext,indicationOptions,profileName,renalDose,type DoseResult,type DoseReview,type PrescriptionSeed} from './renalDoseModel';
export interface MedicineAssessment {indication:string;phase:string;infusion:string;empiricReviewed:boolean;productReviewed:boolean}
export const blankMedicineAssessment:MedicineAssessment={indication:'',phase:'',infusion:'',empiricReviewed:false,productReviewed:false};
export const ANIDULAFUNGIN_SOURCE='https://www.medicines.org.uk/emc/product/13906/smpc';
export const medicineIndications=(name:string)=>name.toLowerCase()==='anidulafungin'?[{id:'invasive_candidiasis',label:'Adult invasive candidiasis · maintenance after loading'}]:indicationOptions[profileName(name)!]??[];
export function medicationDoseReview(medicine:string,route:string,m:AutomaticRenalModel,a:MedicineAssessment):DoseResult&{seed?:PrescriptionSeed}{
 const hold=(reason:string):DoseResult=>({status:'review',reason,version:'automatic-patient-dose-review/1'});
 if(!m.routineEligible||!m.context)return hold(m.reasons[0]??'Current renal evidence and patient context need review.');
 if(!a.productReviewed)return hold('Confirm the exact product, formulation and dose basis for this medicine.');
 if(!a.empiricReviewed)return hold('Review the infection and treatment rationale explicitly; no culture-directed choice is inferred.');
 const c=m.context,context={...blankDoseContext,medicine,route,indication:a.indication,phase:a.phase,infusion:a.infusion,bodySize:c.bodySize,hepatic:c.hepatic,special:c.special,safetyReviewed:c.safetyReviewed,renalFunction:c.renalFunction,support:c.support,cultureReviewed:true,empiricReviewed:true};
 let result:DoseResult;
 if(medicine.toLowerCase()==='anidulafungin'){
  if(a.indication!=='invasive_candidiasis'||a.phase!=='maintenance'||route!=='IV')return hold('Review adult invasive candidiasis, completed loading and IV maintenance; an initiation schedule is not generated here.');
  if(c.bodySize!=='standard'||c.hepatic!=='reviewed'||c.special!=='none'||!c.safetyReviewed)return hold('Review patient-specific applicability, interactions and special circumstances.');
  result={status:'suggested',reason:'No renal maintenance adjustment for the reviewed indication',medicine:undefined,version:'anidulafungin-smPC-2026-10-26/1',source:ANIDULAFUNGIN_SOURCE,band:'No renal adjustment required',maintenance:{amount:'100',unit:'mg',route:'IV',schedule:'Every 24 hours',display:'100 mg IV · Every 24 hours'},notes:['Maintenance after separately reviewed loading; duration and infusion instructions require the source prescription.']};
 }else result=renalDose(m.inputs,context,m.crcl);
 if(result.status!=='suggested'||!result.maintenance||!result.source||!m.scope)return result;
 const {medicine:_medicine,route:_route,cultureSource:_cs,cultureBlock:_cb,cultureReviewed:_cr,empiricReviewed:_er,...reviewContext}=context;
 const doseReview:DoseReview={version:'CandidateDoseReview/v1',profile_version:result.version,source:result.source,suggestion:{medicine,amount:result.maintenance.amount,unit:result.maintenance.unit,route:result.maintenance.route,schedule:result.maintenance.schedule,initial:result.initial??null,band:result.band??''},inputs:{...m.inputs},crcl:m.crcl??null,context:reviewContext,basis:'empiric',scope:{...m.scope},sources:m.sources.map(s=>({...s}))};
 return {...result,seed:{medicine,amount:result.maintenance.amount,unit:result.maintenance.unit,route:result.maintenance.route,schedule:result.maintenance.schedule,dose_detail:'Source candidate; exact product/component reviewed.',indication:medicineIndications(medicine).find(i=>i.id===a.indication)?.label??a.indication,doseReview}};
}
