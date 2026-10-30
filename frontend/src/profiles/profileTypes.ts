export type Reference={id:string;title:string;url:string;jurisdiction?:string;accessed_date?:string};
export type SourceSection={text:string;status:string;source_ids?:string[];source_inclusion_approval?:{status:string}};
export type ClinicalTable={title:string;columns:string[];rows:string[][];context:string;source_ids:string[]};
export type ClinicalFact={label:string;value:string;context:string;source_ids:string[]};
export type Advanced={title:string;text:string;tables:ClinicalTable[];source_ids:string[]};
export type Expanded={dosing:ClinicalTable[];renal:ClinicalTable[];pk:ClinicalFact[];pd:ClinicalFact[];spectrum:ClinicalTable[];interactions:ClinicalTable[];advanced:Advanced[];audit:{reviewed_on:string;sources_inspected:string[];limitations:string[]}};
export type Profile={id:string;name:string;class:string;scope:string;forms:string[];sections:Record<string,SourceSection>;references:Reference[];india_evidence:{status:string;note:string};review_status:string;clinical_use_eligible:boolean;expanded?:Expanded};
export type Library={version:string;records:Profile[];section_labels:Record<string,string>};
