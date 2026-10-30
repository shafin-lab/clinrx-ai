/** Separate external references; never used to assemble or alter NCDC treatment. */
export interface SupplementarySource {
  id: string;
  organisation: string;
  title: string;
  version: string;
  year: number;
  url: string;
}
export interface SupplementaryEntry {
  id: string;
  sourceId: string;
  title: string;
  kind: 'Dosing reference' | 'Clinical context';
  why: string;
  appliesTo: string;
  details: {label: string; text: string}[];
  difference: string;
  limits: string;
  location: string;
  bindings: {infectionId: string; rowIds?: string[]}[];
}

export const supplementarySources: Readonly<Record<string, SupplementarySource>> = {
  'teicoplanin-2026': {
    id: 'teicoplanin-2026', organisation: 'UK product information',
    title: 'Teicoplanin 200 mg — approved product information', version: 'Updated 10 March 2026', year: 2026,
    url: 'https://www.medicines.org.uk/emc/product/101956/smpc',
  },
  'esc-ie-2023': {
    id: 'esc-ie-2023', organisation: 'ESC', title: 'Guidelines for the management of endocarditis',
    version: '2023', year: 2023, url: 'https://academic.oup.com/eurheartj/article/44/39/3948/7243107',
  },
  'naco-2024': {
    id: 'naco-2024', organisation: 'NACO', title: 'National Technical Guidelines on STI and RTI',
    version: '2024', year: 2024,
    url: 'https://naco.mohfw.gov.in/wp-content/uploads/2025/05/National-Technical-Guidelines-on-STI-and-RTI_Final.pdf',
  },
  'dfi-2023': {
    id: 'dfi-2023', organisation: 'IWGDF/IDSA', title: 'Diabetes-related foot infections guideline',
    version: '2023', year: 2023, url: 'https://www.idsociety.org/practice-guideline/diabetic-foot-infections/',
  },
  'who-diphtheria-2024': {
    id: 'who-diphtheria-2024', organisation: 'WHO', title: 'Clinical management of diphtheria',
    version: '2 February 2024', year: 2024, url: 'https://www.who.int/publications/i/item/WHO-DIPH-Clinical-2024.1',
  },
  'cuti-2025': {
    id: 'cuti-2025', organisation: 'IDSA', title: 'Complicated urinary tract infections guideline',
    version: '2025', year: 2025, url: 'https://www.idsociety.org/practice-guideline/complicated-urinary-tract-infections/',
  },
  'ebmt-2024': {
    id: 'ebmt-2024', organisation: 'EBMT', title: 'The EBMT Handbook, eighth edition',
    version: '2024', year: 2024, url: 'https://www.ebmt.org/sites/default/files/2024-04/978-3-031-44080-9.pdf',
  },
  'sdcep-2026': {
    id: 'sdcep-2026', organisation: 'SDCEP', title: 'Drug Prescribing for Dentistry — bacterial infections',
    version: 'Updated May 2026', year: 2026,
    url: 'https://www.sdcepdentalprescribing.nhs.scot/guidance/bacterial-infections/acute-periodontal-conditions/metronidazole/',
  },
  'ssc-2026': {
    id: 'ssc-2026', organisation: 'Surviving Sepsis Campaign', title: 'Adult sepsis and septic shock guideline',
    version: '2026', year: 2026,
    url: 'https://sccm.org/clinical-resources/guidelines/guidelines/surviving-sepsis-campaign-international-guidelines-for-management-of-sepsis-and-septic-shock-2026',
  },
};

export const supplementaryEntries: readonly SupplementaryEntry[] = [
  {
    id: 'ie-teicoplanin', sourceId: 'teicoplanin-2026', title: 'Teicoplanin: additional dosing information', kind: 'Dosing reference',
    why: 'Provides a separate weight-based schedule; it does not establish what NCDC intended by its incomplete maintenance expression.',
    appliesTo: 'Adults with normal renal function, for infective endocarditis.',
    details: [
      {label: 'Loading', text: '12 mg/kg IV every 12 hours for 3–5 doses.'},
      {label: 'Maintenance', text: '12 mg/kg IV or IM once daily.'},
      {label: 'Duration', text: 'Determined by clinical response; the label usually considers at least 21 days appropriate.'},
      {label: 'Monitoring', text: 'Teicoplanin concentrations, kidney function and toxicity monitoring.'},
    ],
    difference: 'This label has its own loading, maintenance and duration statements. These do not replace the NCDC combination or its duration.',
    limits: 'Renal impairment requires a different schedule. This drug-specific information is not a complete replacement endocarditis regimen; pathogen susceptibility and companion therapy still need review.',
    location: 'Sections 4.2–4.4; adult endocarditis posology.',
    bindings: [{infectionId: 'ncdc-1-1', rowIds: ['ncdc-1-1-source-row-3']}],
  },
  {
    id: 'ie-valve-context', sourceId: 'esc-ie-2023', title: 'Endocarditis: organism and valve context', kind: 'Clinical context',
    why: 'Adds organism- and valve-specific context when an empirical source row does not settle definitive treatment.',
    appliesTo: 'Endocarditis assessed by organism, native or prosthetic valve, complications and allergy history.',
    details: [{label: 'Further guidance', text: 'ESC separates empirical treatment from organism-directed regimens and recommends Endocarditis Team assessment for complex decisions.'}],
    difference: 'A regimen for a different organism, valve setting or companion-drug combination cannot supply a missing duration in the NCDC row.',
    limits: 'No single alternative regimen is selected here. Culture results, susceptibility, valve timing, source control and patient factors determine applicability.',
    location: 'Sections 7.1–7.2, 7.6–7.7 and 7.12.', bindings: [{infectionId: 'ncdc-1-1'}],
  },
  {
    id: 'naco-genital-herpes', sourceId: 'naco-2024', title: 'Genital ulcers: herpes-specific guidance', kind: 'Dosing reference',
    why: 'NCDC refers this syndrome to the national STI/RTI guidance.',
    appliesTo: 'Genital herpes in the NACO genital-ulcer pathway; establish the cause and disease stage first.',
    details: [{label: 'Source option', text: 'Acyclovir 400 mg orally three times daily for 7 days.'}],
    difference: 'This is a herpes-specific option, not a universal treatment for all genital ulcers.',
    limits: 'Syphilis, pregnancy, breastfeeding, age under 16 years, immunocompromise and renal impairment need their own assessment.',
    location: 'Table 3.6; printed pages 52–55, PDF pages 72–75.', bindings: [{infectionId: 'ncdc-6-1'}],
  },
  {
    id: 'naco-external-warts', sourceId: 'naco-2024', title: 'Anogenital warts: a local treatment option', kind: 'Dosing reference',
    why: 'Adds a treatment option from the national source referred to by NCDC.',
    appliesTo: 'Suitable external anogenital warts after lesion-site assessment; not for pregnancy or children.',
    details: [{label: 'Source option', text: 'Podophyllotoxin 0.5% applied twice daily for 3 days, then 4 days off; up to 4 cycles.'}],
    difference: 'A local wart treatment, not a systemic antibiotic regimen.',
    limits: 'Internal lesions, pregnancy and unsuitable sites require a different pathway; provider-administered options are described in the source.',
    location: 'Printed pages 91–92, PDF pages 111–112.', bindings: [{infectionId: 'ncdc-6-2'}],
  },
  {
    id: 'naco-vaginal-candida', sourceId: 'naco-2024', title: 'Vaginal discharge: candidiasis-specific option', kind: 'Dosing reference',
    why: 'The referred national guidance distinguishes causes of vaginal discharge.',
    appliesTo: 'Vulvovaginal candidiasis; not every vaginal-discharge presentation.',
    details: [{label: 'Source option', text: 'Clotrimazole 100 mg intravaginally nightly for 7 nights.'}],
    difference: 'This cause-specific option does not treat cervicitis or replace the full syndromic assessment.',
    limits: 'Pregnancy, breastfeeding, age and recurrent or complicated disease require the applicable source pathway.',
    location: 'Table 3.4; printed pages 42–43, PDF pages 62–63.', bindings: [{infectionId: 'ncdc-6-4'}],
  },
  {
    id: 'naco-pid', sourceId: 'naco-2024', title: 'PID: national programme regimen', kind: 'Dosing reference',
    why: 'Supplies the distinct national programme schedule to which NCDC refers.',
    appliesTo: 'The NACO lower-abdominal-pain/PID syndromic pathway; exclude referral conditions first.',
    details: [
      {label: 'Together', text: 'Cefixime 800 mg orally once PLUS Doxycycline 100 mg orally twice daily for 14 days PLUS Metronidazole 400 mg orally twice daily for 14 days.'},
    ],
    difference: 'This is the intact Table 3.5 schedule; it does not modify any NCDC dose or use the inconsistent route printed in another NACO chapter.',
    limits: 'Pregnancy, postpartum or recent-abortion presentations and red flags require referral, not routine outpatient substitution. Individual contraindications and organ function still need review.',
    location: 'Table 3.5; printed page 49, PDF page 69.', bindings: [{infectionId: 'ncdc-6-6'}],
  },
  {
    id: 'naco-urethral', sourceId: 'naco-2024', title: 'Urethral discharge: uncomplicated NG/CT regimen', kind: 'Dosing reference',
    why: 'Makes the referred national source schedule available beside this syndrome.',
    appliesTo: 'Uncomplicated gonococcal/chlamydial urethral infection in the NACO pathway.',
    details: [{label: 'Together', text: 'Ceftriaxone 500 mg IM once PLUS Doxycycline 100 mg orally twice daily for 7 days.'}],
    difference: 'A separate urethral-infection regimen; it is not a prostatitis or recurrent-infection regimen.',
    limits: 'Doxycycline is not for pregnancy. Persistent disease, children, contraindications and organ-function concerns need a different assessment.',
    location: 'Table 3.3; printed page 36, PDF page 56.', bindings: [{infectionId: 'ncdc-6-9'}],
  },
  {
    id: 'dfi-duration-context', sourceId: 'dfi-2023', title: 'Diabetic foot infection: duration and bone involvement', kind: 'Clinical context',
    why: 'Distinguishes soft-tissue treatment from deeper infection when considering duration.',
    appliesTo: 'Diabetes-related foot infection after assessment of infection extent, perfusion and source control.',
    details: [{label: 'Duration context', text: 'Soft-tissue infection: usually 1–2 weeks; consider up to 3–4 weeks for extensive, slowly resolving infection or severe peripheral artery disease. Bone infection has separate recommendations.'}],
    difference: 'These soft-tissue durations cannot be attached automatically to the NCDC moderate/severe rows, which can include osteomyelitis.',
    limits: 'This is not a complete antibiotic regimen. Organism, susceptibility, geography, recent cultures, surgery and clinical response guide agent selection.',
    location: 'Recommendations 12–15 and the separate osteomyelitis recommendations.', bindings: [{infectionId: 'ncdc-9-7'}],
  },
  {
    id: 'diphtheria-context', sourceId: 'who-diphtheria-2024', title: 'Diphtheria: antimicrobial and antitoxin context', kind: 'Clinical context',
    why: 'Adds recent disease-specific guidance with a different antimicrobial preference.',
    appliesTo: 'Suspected or confirmed respiratory diphtheria; case treatment, not contact prophylaxis.',
    details: [{label: 'WHO guidance', text: 'WHO prefers macrolides over penicillins and considers antitoxin separately by disease severity and time since onset. Airway and complication management remain essential.'}],
    difference: 'WHO preference differs from NCDC’s treatment organisation. Neither NCDC doses nor antitoxin condition–dose pairs are replaced here.',
    limits: 'This context summary is not a full dosing regimen. Review the disease-specific source, antimicrobial susceptibility, antitoxin preparation and public-health pathway.',
    location: 'Sections 5–6; WHO/DIPH/Clinical/2024.1.', bindings: [{infectionId: 'ncdc-13-2'}],
  },
  {
    id: 'cuti-duration-context', sourceId: 'cuti-2025', title: 'Complicated UTI: duration evidence and exclusions', kind: 'Clinical context',
    why: 'Explains the population limits of recent short-course evidence.',
    appliesTo: 'Complicated UTI improving on effective treatment, within the guideline’s studied populations.',
    details: [{label: 'Duration context', text: 'For selected improving patients, IDSA suggests 7 days of a non-fluoroquinolone, counted from the first day of effective therapy.'}],
    difference: 'The studies largely excluded indwelling catheters, severe sepsis, immunocompromise, CKD and bacterial prostatitis. This does not resolve NCDC’s severe-CAUTI duration or single-dose ambiguity.',
    limits: 'A duration reference, not a drug choice or complete regimen. Source control, susceptibility, severity and exclusions require individual assessment.',
    location: 'Duration recommendations and comments.', bindings: [{infectionId: 'ncdc-5-2'}, {infectionId: 'ncdc-18-6'}],
  },
  {
    id: 'hct-hsv', sourceId: 'ebmt-2024', title: 'Transplant HSV: severe disease treatment', kind: 'Dosing reference',
    why: 'Adds phenotype-specific transplant guidance rather than borrowing an HIV or neonatal schedule.',
    appliesTo: 'Adult HCT recipients with severe mucocutaneous or visceral HSV; CNS disease requires a different regimen.',
    details: [{label: 'Source regimen', text: 'Acyclovir 5 mg/kg IV every 8 hours for 7–10 days.'}],
    difference: 'This severe-HSV schedule is distinct from the general NCDC oral schedule and is not CMV or VZV treatment.',
    limits: 'Renal adjustment and the transplant protocol need review. This is not a prophylaxis, paediatric, neonatal, CNS or HSV-pneumonia schedule.',
    location: 'Chapter 38, sections 38.1.6.3–38.1.6.4.',
    bindings: [{infectionId: 'ncdc-17-4', rowIds: ['ncdc-17-4-source-row-6']}],
  },
  {
    id: 'dental-periodontal', sourceId: 'sdcep-2026', title: 'Acute periodontal infection: a scoped oral regimen', kind: 'Dosing reference',
    why: 'Adds recent guidance for specific acute periodontal indications.',
    appliesTo: 'Adults with necrotising gingivitis, necrotising periodontitis or pericoronitis when antibiotics are indicated alongside local treatment.',
    details: [{label: 'Source regimen', text: 'Metronidazole 400 mg orally three times daily for 3 days; review ideally at 3 days.'}],
    difference: 'This is not a regimen for every chronic-periodontitis presentation and does not change NCDC’s treatment or failure interval.',
    limits: 'Children require different doses. Check interactions and contraindications. Deep-space infection, airway symptoms or other severe red flags require urgent hospital assessment.',
    location: 'Bacterial infections, acute periodontal conditions: metronidazole.',
    bindings: [{infectionId: 'ncdc-16-1', rowIds: ['ncdc-16-1-source-row-1', 'ncdc-16-1-source-row-2']}],
  },
  {
    id: 'sepsis-infusion-context', sourceId: 'ssc-2026', title: 'Beta-lactam infusion in adult sepsis', kind: 'Clinical context',
    why: 'Adds recent infusion-strategy guidance for the severe-sepsis situation.',
    appliesTo: 'Adults with sepsis or septic shock receiving an appropriate beta-lactam.',
    details: [{label: 'Infusion strategy', text: 'Prolonged beta-lactam maintenance infusion after an initial loading dose is recommended over bolus maintenance.'}],
    difference: 'This does not select an antibiotic or change NCDC’s drug doses, combinations or infusion instructions.',
    limits: 'No drug-specific loading amount, infusion time or stability instruction is supplied here; preparation, compatibility and product stability need their own verified protocol.',
    location: 'Antimicrobial administration: prolonged beta-lactam maintenance after loading.',
    bindings: [{infectionId: 'ncdc-1-1', rowIds: ['ncdc-1-1-source-row-3']}],
  },
];

/** Each entry is evaluated once, even if more than one of its bindings matches. */
export function supplementaryFor(infectionId: string, rowId?: string): SupplementaryEntry[] {
  return supplementaryEntries.filter(entry => entry.bindings.some(binding =>
    binding.infectionId === infectionId && (!binding.rowIds || (rowId !== undefined && binding.rowIds.includes(rowId)))
  ));
}
