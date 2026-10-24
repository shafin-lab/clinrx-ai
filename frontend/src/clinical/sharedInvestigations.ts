import type {Fact} from '../api/rf2Client';

/** Product coverage catalog, not an order set, terminology crosswalk or assay equivalence. */
export interface InvestigationGroup {
 id:string;
 label:string;
 aliases:readonly string[];
 modules:readonly string[];
 plannedTests:readonly string[];
}
const group=(id:string,label:string,aliases:string[],modules:string[],tests:string):InvestigationGroup=>
 ({id,label,aliases,modules,plannedTests:tests.split('; ')});
export const investigationGroups:readonly InvestigationGroup[]=[
 group('blood-count','Blood count',['CBC','FBC'],['M10','M17'],
  'Haemoglobin; Haematocrit; Red-cell count; MCV; MCH; MCHC; RDW; Total white-cell count; Neutrophil count; Lymphocyte count; Monocyte count; Eosinophil count; Basophil count; Platelet count; MPV; Immature granulocytes; Nucleated red cells; Reticulocyte count; Blood-film report'),
 group('kidney-electrolytes','Kidney and electrolytes',['KFT','RFT','Renal panel'],['M8','M9','M14','M17'],
  'Creatinine; Urea; Blood urea nitrogen; Source-reported eGFR; Sodium; Potassium; Chloride; Total carbon dioxide; Total calcium; Ionised calcium; Magnesium; Phosphate; Urate; Cystatin C'),
 group('liver','Liver and proteins',['LFT','Liver panel'],['M10','M11','M17'],
  'AST; ALT; ALP; GGT; Total bilirubin; Direct bilirubin; Albumin; Total protein; Source-reported globulin; Ammonia; Bile acids'),
 group('gases','Blood gases and co-oximetry',['ABG','VBG'],['M7','M8','M9','M10'],
  'pH; PaCO2; PaO2; Venous PO2; Blood-gas bicarbonate; Base excess; Arterial oxygen saturation; Mixed venous oxygen saturation; Central venous oxygen saturation; Co-oximetry haemoglobin; Carboxyhaemoglobin; Methaemoglobin; Lactate'),
 group('cardiac','Cardiac markers',[],['M7'],
  'Troponin I; High-sensitivity troponin I; Troponin T; High-sensitivity troponin T; BNP; NT-proBNP; CK-MB; Total CK; Myoglobin'),
 group('lipids','Lipids and apolipoproteins',['Lipid profile'],['M7','M14','M17'],
  'Total cholesterol; HDL cholesterol; Direct LDL cholesterol; Source-calculated LDL cholesterol; Triglycerides; Source-reported non-HDL cholesterol; Apolipoprotein B; Apolipoprotein A1; Lipoprotein(a)'),
 group('coagulation','Coagulation and anticoagulant monitoring',['Coagulation profile'],['M8','M10','M12'],
  'PT; INR; aPTT; Fibrinogen; D-dimer; Fibrin degradation products; Thrombin time; Reptilase time; UFH-calibrated anti-Xa; LMWH-calibrated anti-Xa; Drug-specific anticoagulant level; Mixing-study report; TEG report; ROTEM report'),
 group('blood-bank','Blood bank and transfusion',[],['M10','M12','M21'],
  'ABO group; RhD group; Red-cell antibody screen; Antibody identification; Crossmatch; Direct antiglobulin test; Indirect antiglobulin test; Transfusion-reaction investigation; HLA antibody report'),
 group('thrombophilia','Thrombophilia and prothrombotic investigations',['Thrombophilia panel'],['M10'],
  'Lupus-anticoagulant screen and confirmation; Anticardiolipin IgG; Anticardiolipin IgM; Anti-beta-2-glycoprotein I IgG; Anti-beta-2-glycoprotein I IgM; Protein C activity; Protein C antigen; Protein S activity; Free protein S antigen; Total protein S antigen; Antithrombin activity; Antithrombin antigen; Activated protein C resistance; Factor V Leiden genotype; Prothrombin G20210A genotype; HIT immunoassay; HIT functional assay; JAK2 mutation report; PNH flow-cytometry report'),
 group('special-haemostasis','Specialised haemostasis',[],['M10'],
  'Factor II activity; Factor V activity; Factor VII activity; Factor VIII activity; Factor IX activity; Factor X activity; Factor XI activity; Factor XII activity; Factor XIII assay; Factor-inhibitor assay; von Willebrand factor antigen; von Willebrand factor activity; von Willebrand multimer report; Platelet-function report; ADAMTS13 activity; ADAMTS13 inhibitor'),
 group('inflammation','Inflammation and infection biomarkers',[],['M6','M9','M20'],
  'CRP; High-sensitivity CRP; ESR; Procalcitonin; Interleukin-6; Beta-D-glucan; Galactomannan'),
 group('microbiology','Microbiology and infectious-disease reports',[],['M6','M15'],
  'Culture report; Organism identification; Antimicrobial susceptibility; Molecular pathogen assay; Viral load; Pathogen antigen; Pathogen serology; HIV antigen-antibody assay; HBsAg; Anti-HBc; Anti-HBs; HBV DNA; Anti-HCV; HCV RNA; CMV PCR; EBV PCR; CMV serology; EBV serology; Resistance-gene report; Colonisation-screen report'),
 group('glucose','Glucose and ketones',[],['M14','M17'],
  'Laboratory glucose; Capillary point-of-care glucose; CGM observation; HbA1c; Fructosamine; Beta-hydroxybutyrate; Urine ketones; Insulin; C-peptide; Proinsulin'),
 group('thyroid','Thyroid',[],['M12','M14'],
  'TSH; Free T4; Free T3; Total T4; Total T3; Thyroid peroxidase antibody; Thyroglobulin antibody; TSH-receptor antibody; Thyroglobulin'),
 group('adrenal','Adrenal and mineralocorticoid',[],['M7','M14'],
  'Serum cortisol; ACTH; Salivary cortisol; Urinary free cortisol; Renin activity; Direct renin concentration; Aldosterone; Plasma free metanephrines; Urinary fractionated metanephrines; DHEAS; 17-hydroxyprogesterone'),
 group('bone','Calcium, bone and vitamin D',[],['M8','M14','M17'],
  'PTH; 25-hydroxyvitamin D; 1,25-dihydroxyvitamin D; Bone-specific ALP; PTH-related peptide; Source bone-turnover marker'),
 group('pituitary-reproductive','Pituitary and reproductive endocrine',[],['M12','M14'],
  'Prolactin; LH; FSH; Estradiol; Progesterone; Total testosterone; Free testosterone; SHBG; IGF-1; Growth hormone; Serum hCG; Copeptin; Dynamic endocrine-test series'),
 group('haematinics','Haematinics and haemolysis',[],['M10','M17'],
  'Ferritin; Serum iron; Transferrin; TIBC; Source-reported transferrin saturation; Vitamin B12; Folate; Methylmalonic acid; Homocysteine; LDH; Haptoglobin; Plasma free haemoglobin; G6PD assay; Haemoglobinopathy report'),
 group('nutrition','Specialised nutrition assays',[],['M8','M14','M17'],
  'Thiamine assay; Vitamin A; Vitamin E; Vitamin C; Vitamin K assay; Zinc; Copper; Selenium; Ceruloplasmin; Prealbumin; Urinary urea nitrogen; Urinary total nitrogen; Essential-fatty-acid report'),
 group('immunology','Immunology and complement',[],['M8','M16','M20'],
  'ANA; Anti-dsDNA; ENA report; ANCA; Anti-GBM antibody; Rheumatoid factor; Anti-CCP; C3; C4; CH50; Immunoglobulin G; Immunoglobulin A; Immunoglobulin M; Immunoglobulin E; IgG subclasses; Cryoglobulin report; Cryofibrinogen report'),
 group('paraprotein','Paraproteins and haematological reports',[],['M8','M10'],
  'Serum electrophoresis; Urine electrophoresis; Serum immunofixation; Urine immunofixation; Free kappa light chains; Free lambda light chains; Source-reported light-chain ratio; Bone-marrow report; Flow-cytometry report; Cytogenetic report; Molecular haematology report'),
 group('drug-levels','Therapeutic drug monitoring and toxicology',[],['M6','M8','M13','M18'],
  'Tacrolimus level; Cyclosporine level; Sirolimus level; Everolimus level; Vancomycin level; Aminoglycoside level; Antifungal level; Digoxin level; Lithium level; Antiseizure-drug level; Paracetamol level; Salicylate level; Ethanol level; Toxicology screen; Toxic-alcohol report; Heavy-metal assay'),
 group('osmolality-urine','Osmolality and urine investigations',[],['M8','M14'],
  'Measured serum osmolality; Urine osmolality; Urine sodium; Urine potassium; Urine chloride; Urine creatinine; Urine urea; Urine albumin; Urine protein; Source-reported ACR; Source-reported PCR; Urinalysis; Urine microscopy; Timed urine collection report'),
 group('rare-metabolic','Rare metabolic, genetic and specialised reports',[],['M8','M14','M16','M17'],
  'Plasma amino-acid report; Urine organic-acid report; Acylcarnitine profile; Carnitine assay; Porphyrin report; Lactate-pyruvate report; Lysosomal-enzyme report; Genetic-test report; Tumour-marker report; Other original investigation report'),
 group('body-fluids','CSF, body fluids and tissue reports',[],['M6','M8','M9','M11','M12','M13','M16'],
  'CSF cell count; CSF protein; CSF glucose; Body-fluid cell count; Body-fluid differential; Body-fluid protein; Body-fluid albumin; Body-fluid LDH; Body-fluid glucose; Body-fluid pH; Body-fluid amylase; Body-fluid triglycerides; Body-fluid creatinine; Fluid cytology; Tissue pathology report'),
];

/** Only existing, decoded source discriminants are mapped. Labels/aliases never admit data. */
const sourceMappings:Readonly<Record<string,{label:string;groupId:string}>>={
 'observation:synthetic-serum-creatinine':{label:'Creatinine',groupId:'kidney-electrolytes'},
 'circulatory_lactate:':{label:'Lactate',groupId:'gases'},
 'circulatory_oxygen:ph':{label:'pH',groupId:'gases'},
 'circulatory_oxygen:paco2':{label:'PaCO₂',groupId:'gases'},
 'circulatory_oxygen:pao2':{label:'PaO₂',groupId:'gases'},
 'circulatory_oxygen:pvo2':{label:'Venous PO₂',groupId:'gases'},
 'circulatory_oxygen:bicarbonate':{label:'Bicarbonate',groupId:'gases'},
 'circulatory_oxygen:base_excess':{label:'Base excess',groupId:'gases'},
 'circulatory_oxygen:hemoglobin':{label:'Haemoglobin',groupId:'gases'},
 'circulatory_oxygen:sao2':{label:'Arterial oxygen saturation',groupId:'gases'},
 'circulatory_oxygen:svo2':{label:'Mixed venous oxygen saturation',groupId:'gases'},
 'circulatory_oxygen:scvo2':{label:'Central venous oxygen saturation',groupId:'gases'},
};
export function investigationPresentation(fact:Fact){
 const discriminator=fact.kind==='observation'?fact.concept_id:fact.kind==='circulatory_oxygen'?fact.concept:fact.kind==='circulatory_lactate'?'':undefined;
 if(typeof discriminator!=='string')return undefined;
 const mapped=sourceMappings[`${fact.kind}:${discriminator}`];
 if(!mapped)return undefined;
 return {...mapped,group:investigationGroups.find(g=>g.id===mapped.groupId)!};
}

/** Search the development catalog; aliases organise labels, never classify an original assay. */
export function searchInvestigationCatalog(query:string){
 const text=query.trim().toLocaleLowerCase();
 return investigationGroups.filter(g=>[g.label,...g.aliases,...g.plannedTests].some(v=>v.toLocaleLowerCase().includes(text)));
}
