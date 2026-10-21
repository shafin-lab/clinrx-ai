import type {RenalSource} from './renalBedsideModel';

type Test={id:string;label:string;note?:string;source?:'creatinine'|'bicarbonate'|'ph'};
export const renalInvestigationPanels:readonly {id:string;title:string;description:string;tests:readonly Test[]}[]=[
 {id:'core',title:'Core kidney tests',description:'Core fields stay visible. Actual testing and repeat frequency follow the clinical assessment.',tests:[
  {id:'urea',label:'Urea / BUN',note:'Keep urea and BUN identified as reported; their numeric values and units differ.'},
  {id:'creatinine',label:'Creatinine',source:'creatinine'},
  {id:'sodium',label:'Sodium'},
  {id:'potassium',label:'Potassium',note:'Retain specimen time and haemolysis flag.'},
  {id:'urine-routine',label:'Urine routine',note:'Blood, protein, leukocytes, nitrites and glucose; urine microscopy is separate.'}
 ]},
 {id:'electrolytes',title:'Electrolytes, acid–base and CRRT monitoring',description:'Keep chemistry and blood-gas specimens distinct. Review calcium, magnesium and phosphate in the KRT context.',tests:[
  {id:'chloride',label:'Chloride'},{id:'total-co2',label:'Total CO₂ · chemistry'},
  {id:'bicarbonate',label:'Bicarbonate · blood gas',source:'bicarbonate'},
  {id:'ph',label:'pH · blood gas',source:'ph'},
  {id:'calcium',label:'Total calcium'},{id:'systemic-ica',label:'Systemic ionised calcium'},
  {id:'postfilter-ica',label:'Post-filter ionised calcium',note:'Circuit sample; separate from systemic calcium.'},
  {id:'magnesium',label:'Magnesium'},{id:'phosphate',label:'Phosphate'},
  {id:'glucose',label:'Glucose'},{id:'albumin',label:'Albumin'}
 ]},
 {id:'urine',title:'Urine studies and osmolality',description:'Use paired collection times where interpretation requires them. Measured osmolality (mOsm/kg) stays separate from calculated osmolarity (mOsm/L).',tests:[
  {id:'urine-sodium',label:'Urine sodium'},{id:'urine-osmolality',label:'Urine osmolality'},
  {id:'serum-osmolality',label:'Measured serum osmolality'},
  {id:'urine-potassium',label:'Urine potassium'},{id:'urine-chloride',label:'Urine chloride'},
  {id:'urine-creatinine',label:'Urine creatinine'},{id:'urine-urea',label:'Urine urea'},
  {id:'urine-microscopy',label:'Urine microscopy',note:'Cells, casts, crystals and source-reported morphology.'},
  {id:'urine-acr',label:'Urine ACR',note:'Albumin:creatinine ratio; retain assay, specimen and unit basis.'},
  {id:'urine-pcr',label:'Urine PCR',note:'Protein:creatinine ratio; distinct from albumin.'},
  {id:'specific-gravity',label:'Urine specific gravity',note:'Not a substitute for measured osmolality.'},
  {id:'urine-culture',label:'Urine culture · when indicated',note:'Reuse the M6 specimen and microbiology owner.'}
 ]},
 {id:'targeted',title:'Targeted investigations',description:'Available when the clinical question calls for them; this list does not order a panel.',tests:[
  {id:'cystatin',label:'Cystatin C'},
  {id:'ck',label:'CK / rhabdomyolysis work-up'},
  {id:'immune',label:'Immune / glomerular work-up'},
  {id:'hemolysis',label:'Haemolysis / TMA work-up'},
  {id:'drug-levels',label:'Drug levels / transplant levels'},
  {id:'imaging',label:'Renal imaging / obstruction review'}
 ]}
];

/** Only exact supported discriminants admit results. The option list never admits new assays. */
export function renalInvestigationSources(test:Test,sources:readonly RenalSource[]){
 if(test.source==='creatinine')return sources.filter(s=>s.lab?.fact.concept_id==='synthetic-serum-creatinine');
 if(test.source==='bicarbonate'||test.source==='ph')return sources.filter(s=>s.fluid?.fact.kind==='circulatory_oxygen'&&s.fluid.fact.concept===test.source);
 return [];
}
export function RenalInvestigations({sources,current,onOpen}:{sources:readonly RenalSource[];current:boolean;onOpen:(query:string)=>void}){
 function row(test:Test){const records=renalInvestigationSources(test,sources);const supported=!!test.source;
  return <li key={test.id}><div><strong>{test.label}</strong><span>{!current?'Current results unconfirmed':records.length?`${records.length} recorded source${records.length===1?'':'s'}`:supported?'No result supplied':'Result feed not connected'}</span></div>{records.length>0&&<button type="button" className="m7-text-button" aria-label={'Inspect sources for '+test.label} disabled={!current} onClick={()=>onOpen(test.source!)}>Inspect sources ↗<span className="m7-visually-hidden"> for {test.label}</span></button>}{test.note&&<small>{test.note}</small>}</li>;
 }
 return <section className="m8-investigations" aria-labelledby="m8-investigations-title"><div className="m7-section-line"><h2 id="m8-investigations-title">Kidney investigations</h2><span>Results and options</span></div><p className="m7-caption">Shared investigation records. Missing results stay explicit; no test is ordered from this view.</p><ul className="m8-core-tests" aria-label="Core kidney investigation fields">{renalInvestigationPanels[0].tests.map(row)}</ul>{renalInvestigationPanels.slice(1).map(panel=><details key={panel.id}><summary>{panel.title}</summary><p className="m7-caption">{panel.description}</p><ul className="m8-other-tests" aria-label={panel.title}>{panel.tests.map(row)}</ul></details>)}<p className="m7-caption">Urine output is a separate collection record. Urine sodium, FENa and FEurea need clinical context, including diuretics, timing and kidney disease; no cause is diagnosed here.</p></section>;
}
