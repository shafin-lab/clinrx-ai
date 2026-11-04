import type {Fact} from '../api/rf2Client';
import type {RecordedTime} from '../respiratory/respiratoryTypes';
export const giCategories={symptoms:'Symptoms',examination:'Examination',stool_output:'Stool / GI output',feeding_tolerance:'Feeding tolerance',imaging:'Imaging report',procedure:'Procedure report',other:'Other GI finding'} as const;
export interface GIRecord extends Fact {
 kind:'gastrointestinal_record';category:keyof typeof giCategories;title:string;narrative:string;
 source_identity:{issuer_namespace:string;source_report_id:string;source_version:string;accession_id:string|null};
 times:{occurred:RecordedTime;reported:RecordedTime;available:RecordedTime};
 report_status:string;record_status:string;change_state:string;linked_sources:{kind:string;id:string;version:string}[];
 supersedes:{kind:string;id:string;version:string}|null;correction_reason:string|null;
}
export const giLabLabels:Record<string,string>={total_bilirubin:'Total bilirubin',direct_bilirubin:'Direct bilirubin',ast:'AST',alt:'ALT',alp:'ALP',ggt:'GGT',albumin:'Albumin',total_protein:'Total protein',pt:'PT',inr:'INR',amylase:'Amylase',lipase:'Lipase'};
