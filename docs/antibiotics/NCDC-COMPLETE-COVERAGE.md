# Complete NCDC source projection

Source: NCDC / ICMR National Treatment Guidelines for Antimicrobial Use in Infectious Disease Syndromes — Version 2.0 — November 2025. SHA-256 `0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a`.

All 19 groups and 87 named clinical subsections are projected. There are 178 structured clinical source rows, 174 exact section/page images and complete section text/notes. First-line, alternative and comment columns remain separate; OR, +, maxima, staged doses, age/weight conditions and referrals are retained as printed source content.

Table-by-table audit: 122 discovered source grids; 109 mapped to separate treatment columns and 13 different-layout grids retained as primary exact-image crops plus complete original source text. There are 20 primary detail images in total, including the nonstandard grids, original algorithms and text-layer-symbol fallbacks. Grid row counts in the detailed audit include table headers.

This is a source projection, not a new prescription or a clinical validation. It contains no other guideline source. Existing curated records remain separate and untouched. No renal adjustment, patient matching or prescribing action is performed.

## What completeness means

Each section is bounded by its actual PDF heading and the next heading, including all intervening pages through the end of neonatal section 19.1 on PDF126. Chapter headings and printed page numbers are excluded from neighboring section content. Every retained segment has an exact raster crop as an independent visual record. These images include every treatment table, alternative column, additional-information paragraph, referral, reference and figure in that segment.

Main four-column treatment grids are projected by source column. Vertically merged comment cells are copied only to source rows lying inside that same source cell. Continuation text is appended within its original column, with both PDF pages cited. Nonstandard column layouts are not forced into treatment fields: they remain visible in primary exact images and complete original section text, with surrounding non-table notes retained. No valid row is removed because it contains OR, a combination, a maximum or a conditional instruction.

Notes exclude all discovered table rectangles, avoiding dose duplication or flattened nonstandard table associations in the main notes view. Images with primary=true are separate crops of nonstandard tables or source figures/algorithms, suitable for the main section view without repeating the entire structured table; primary=false images are complete section/page proof crops for original-source details. Complete sourceText intentionally retains the entire section for original-source inspection. Text encoding imperfections remain explicit and the raster image is authoritative for those glyphs. Source anomalies such as an unexpected unit are preserved, not silently corrected.

The inventory below audits every section and each discovered table layout; the claim is source-content coverage, not that every nonstandard table has been semantically curated into a prescription-ready structure.

## Verification

TDD RED: all seven initial content/provenance tests failed against the absent new projection. Tests then cover full endocarditis first-line/alternative cells, shared comments, chronic osteomyelitis referrals in both columns, CAP continuation, source-only identity, all section images, algorithms and additional information, and section boundaries.

Rebuild with bundled Python: `python tools/build_ncdc_complete_library.py`. Verify deterministic JSON/report and image existence with `--check`. Run focused tests with `python -m unittest tools/test_ncdc_complete_library.py -v`. No frontend full-suite run is part of this source-only task.

## Source-semantics regression corrections

The PDF60 MRSA cellulitis cell is projected as two severity subrows using verified vertical source-word coordinates: mild treatment columns remain distinct from moderate-to-severe treatment columns; their source common comment is retained for both. Full-width merged headings are recognized before cell propagation, so Viral Keratitis is contextual metadata for Epithelial/Stromal/Endothelial and never copied into treatment columns. Subsequent VZV/fungal rows do not inherit that HSV context. All Unicode private-use characters and replacement characters trigger primary exact-table crops; no clinical symbol is guessed. All nonstandard tables remain primary images, with their flattened table text removed from narrative notes.

## Every-section coverage audit

| Section | Name | PDF pages | Clinical rows | Main grids / other grids | Column continuations | Image or text considerations |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | Infective Endocarditis (Empirical therapy pending blood culture results) | 21, 22 | 3 | 1 / 0 | 0 | Figure included in exact section image |
| 1.2 | Acute Myocarditis | 23 | 1 | 1 / 0 | 1 | Structured source grid plus original notes/image |
| 1.3 | Pericarditis | 23, 24 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 1.4 | Rheumatic fever | 24 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 2.1 | Brain Abscess | 25 | 2 | 1 / 0 | 0 | Text-layer glyphs: exact images authoritative |
| 2.2 | Encephalitis syndrome | 26 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 2.3 | Meningitis syndrome | 27 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 2.4 | CSF shunt infections | 28, 29, 30 | 2 | 2 / 1 | 1 | Different-layout table(s): notes/text + exact images |
| 2.5 | Healthcare Associated Ventriculitis | 30, 31, 32 | 1 | 1 / 3 | 0 | Different-layout table(s): notes/text + exact images; Text-layer glyphs: exact images authoritative |
| 3.1 | Acute Undifferentiated Febrile illness | 33, 34 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images; Figure included in exact section image |
| 3.2 | Enteric fever | 35 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 3.3 | Pyrexia of unknown origin (PUO) | 36 | 0 | 0 / 1 | 0 | Different-layout table(s): notes/text + exact images; Narrative/referral/algorithm: notes/text + exact images |
| 3.4 | Sepsis syndrome- Community acquired and Hospital acquired | 36, 37, 38 | 4 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 4.1 | Oesophagitis | 39 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.2 | Acute Gastroenteritis | 40 | 3 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.3 | Hepatitis Syndrome | 40 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 4.4 | Infections of Liver, Gall Bladder and Biliary tract | 41, 42 | 4 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 4.5 | Appendicitis | 42 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.6 | Diverticulitis | 42 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.7 | Peritonitis – Primary / Secondary | 43 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.8 | Splenic Abscess | 43, 44 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 4.9 | Pancreatitis | 44, 45 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 5.1 | Cystitis | 46 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 5.2 | Pyelonephritis | 46 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 6.1 | Genital Ulcers | 47 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 6.2 | Anogenital Warts | 47 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 6.3 | Septic abortion | 48 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 6.4 | Vaginal Discharge Syndrome | 48 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 6.5 | Epididymo-Orchitis | 49 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 6.6 | Pelvic Inflammatory Disease syndrome | 49 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 6.7 | Prostatitis | 50 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 6.8 | Puerperal sepsis | 50, 51 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 6.9 | Urethral discharge syndrome | 51 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 6.10 | Chorio-amnionitis | 51, 52 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 7.1 | Rhinitis/ Common cold | 53, 54 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 7.2 | Laryngitis/Laryngopharyngitis/URTI | 54, 55 | 5 | 3 / 1 | 1 | Different-layout table(s): notes/text + exact images |
| 7.3 | Sinusitis | 55, 56 | 3 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 7.4 | Otitis media | 56 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 7.5 | Otitis externa | 57 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 7.6 | Head and neck abscesses (peritonsillar/parapharyngeal and retropharyngeal abscess) | 57 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 8.1 | Oropharyngeal Candidiasis | 58 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 9.1 | Paronychia | 59 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 9.2 | Impetigo | 59, 60 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 9.3 | Cellulitis | 60, 61 | 5 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 9.4 | Necrotizing fasciitis | 61, 62 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 9.5 | Primary Pyomyositis | 62 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 9.6 | Folliculitis | 62, 63, 64 | 6 | 3 / 0 | 1 | Figure included in exact section image |
| 9.7 | Diabetic foot infections (DFI) | 65, 66 | 3 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 10.1 | Acute Osteomyelitis | 67, 68 | 3 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 10.2 | Chronic Osteomyelitis | 68 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 10.3 | Gas gangrene | 68, 69 | 1 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 10.4 | Septic arthritis | 69, 70 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 10.5 | Skin and soft tissue injuries | 70 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 10.6 | Orthopaedic implant associated infections | 71, 72 | 1 | 1 / 0 | 0 | Figure included in exact section image |
| 10.7 | Surgical Prophylaxis | 72, 73, 74, 75 | 1 | 1 / 4 | 0 | Different-layout table(s): notes/text + exact images |
| 11.1 | Conjunctivitis & Keratitis | 76, 77, 78, 79, 80, 81 | 11 | 5 / 0 | 4 | Structured source grid plus original notes/image |
| 11.2 | Endophthalmitis | 81, 82, 83, 84 | 4 | 4 / 0 | 3 | Structured source grid plus original notes/image |
| 11.3 | Periocular infections (Eyelid infections, Orbital cellulitis) | 85, 86 | 3 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 11.4 | Retinitis | 87 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.1 | Bronchitis | 88 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.2 | Bronchiolitis | 88 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.3 | Infective exacerbation of asthma/COPD | 88, 89 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.4 | Infective Exacerbation of Bronchiectasis | 89 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.5 | Community Acquired Pneumonia | 90, 91 | 5 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 12.6 | Lung Abscess | 91, 92 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 12.7 | Para-pneumonic pleural effusion/empyema | 92, 93 | 1 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 13.1 | Botulism | 94 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 13.2 | Diphtheria | 94, 95 | 1 | 2 / 1 | 1 | Different-layout table(s): notes/text + exact images |
| 13.3 | Tetanus | 95, 96 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 13.4 | Toxic shock syndrome | 96 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 14.1 | Animal (Dog/cat/monkey/Human) | 97 | 5 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 14.2 | Insect Bites | 98 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 15.1 | Minor Burn Wounds | 99 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 15.2 | Major burn wounds | 99, 100, 101 | 2 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 16.1 | Odontogenic tooth infections | 102, 103 | 3 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 17.1 | Febrile neutropenia syndrome | 104, 105 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 17.2 | Infections in Solid Organ Transplant recipients | 105 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 17.3 | Infections in Asplenia | 106 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 17.4 | Invasive Fungal Infections | 106, 107, 108, 109, 110, 111, 112 | 9 | 4 / 2 | 2 | Different-layout table(s): notes/text + exact images |
| 18.1 | Fever in ICU | 113 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 18.2 | Invasive Candidiasis | 113, 114 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 18.3 | Hospital-acquired pneumonia or Ventilator associated pneumonia | 114, 115 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 18.4 | Central Line-Associated Bloodstream Infection (CLABSI) | 115, 116, 117 | 2 | 2 / 0 | 1 | Structured source grid plus original notes/image |
| 18.5 | Antibiotic Associated Diarrhoea | 117, 118 | 0 | 0 / 0 | 0 | Narrative/referral/algorithm: notes/text + exact images |
| 18.6 | Catheter associated urinary tract infection (CAUTI) | 118, 119 | 2 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 18.7 | Intra-abdominal infection | 119 | 1 | 1 / 0 | 0 | Structured source grid plus original notes/image |
| 19.1 | Neonatal Infections | 120, 121, 122, 123, 124, 125, 126 | 8 | 5 / 0 | 3 | Text-layer glyphs: exact images authoritative |

## Exact image coverage and table layouts

### 1.1 Infective Endocarditis (Empirical therapy pending blood culture results)

- PDF 21 (printed 14), crop points [0.00, 117.57, 595.32, 791.92]: [section-1-1-pdf-21.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-1-pdf-21.png).
- PDF 22 (printed 15), crop points [0.00, 50.00, 595.32, 791.92]: [section-1-1-pdf-22.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-1-pdf-22.png).
- PDF 21: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage Alternative First Line Comments Infection and Duration) (with dosage and Duration).

### 1.2 Acute Myocarditis

- PDF 23 (printed 16), crop points [0.00, 73.27, 595.32, 558.86]: [section-1-2-pdf-23.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-2-pdf-23.png).
- PDF 23: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 1.3 Pericarditis

- PDF 23 (printed 16), crop points [0.00, 558.86, 595.32, 791.92]: [section-1-3-pdf-23.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-3-pdf-23.png).
- PDF 24 (printed 17), crop points [0.00, 50.00, 595.32, 177.45]: [section-1-3-pdf-24.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-3-pdf-24.png).
- PDF 23: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative (with Comments Infection (with Dosage dosage and Duration) and Duration).

### 1.4 Rheumatic fever

- PDF 24 (printed 17), crop points [0.00, 177.45, 595.32, 791.92]: [section-1-4-pdf-24.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-1-4-pdf-24.png).
- PDF 24: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and dosage and Duration) Duration).

### 2.1 Brain Abscess

- PDF 25 (printed 18), crop points [0.00, 107.89, 595.32, 791.92]: [section-2-1-pdf-25.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-1-pdf-25.png).
- PDF 25: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infec�on First Line (with Alterna�ve (with dosage and Comments Dosage and Dura�on) Dura�on).

### 2.2 Encephalitis syndrome

- PDF 26 (printed 19), crop points [0.00, 73.27, 595.32, 791.92]: [section-2-2-pdf-26.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-2-pdf-26.png).
- PDF 26: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).

### 2.3 Meningitis syndrome

- PDF 27 (printed 20), crop points [0.00, 73.27, 595.32, 791.92]: [section-2-3-pdf-27.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-3-pdf-27.png).
- PDF 27: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and Duration) dosage and Duration).

### 2.4 CSF shunt infections

- PDF 28 (printed 21), crop points [0.00, 73.27, 595.32, 791.92]: [section-2-4-pdf-28.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-4-pdf-28.png).
- PDF 29 (printed 22), crop points [0.00, 50.00, 595.32, 791.92]: [section-2-4-pdf-29.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-4-pdf-29.png).
- PDF 30 (printed 23), crop points [0.00, 50.00, 595.32, 306.72]: [section-2-4-pdf-30.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-4-pdf-30.png).
- PDF 28: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 29: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 29: 2 grid columns, 9 grid rows; original table retained in primary image/original source text; source header/context: Drug Dose.

### 2.5 Healthcare Associated Ventriculitis

- PDF 30 (printed 23), crop points [0.00, 306.72, 595.32, 791.92]: [section-2-5-pdf-30.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-5-pdf-30.png).
- PDF 31 (printed 24), crop points [0.00, 50.00, 595.32, 791.92]: [section-2-5-pdf-31.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-5-pdf-31.png).
- PDF 32 (printed 25), crop points [0.00, 50.00, 595.32, 791.92]: [section-2-5-pdf-32.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-2-5-pdf-32.png).
- PDF 30: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Comments Duration) dosage and Duration).
- PDF 31: 3 grid columns, 7 grid rows; original table retained in primary image/original source text; source header/context: S. No Suspected Condition and time of Specimen to be collected collection.
- PDF 31: 3 grid columns, 8 grid rows; original table retained in primary image/original source text; source header/context: Drug Adult dose Paediatric dose.
- PDF 32: 3 grid columns, 14 grid rows; original table retained in primary image/original source text; source header/context: Drug Adult dose Paediatric dose.

### 3.1 Acute Undifferentiated Febrile illness

- PDF 33 (printed 26), crop points [0.00, 107.61, 595.32, 791.92]: [section-3-1-pdf-33.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-1-pdf-33.png).
- PDF 34 (printed 27), crop points [0.00, 50.00, 595.32, 791.92]: [section-3-1-pdf-34.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-1-pdf-34.png).

### 3.2 Enteric fever

- PDF 35 (printed 28), crop points [0.00, 73.27, 595.32, 791.92]: [section-3-2-pdf-35.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-2-pdf-35.png).
- PDF 35: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line Alternative Comments.

### 3.3 Pyrexia of unknown origin (PUO)

- PDF 36 (printed 29), crop points [0.00, 73.27, 595.32, 332.76]: [section-3-3-pdf-36.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-3-pdf-36.png).
- PDF 36: 3 grid columns, 2 grid rows; original table retained in primary image/original source text; source header/context: Type of Infection First Line (with Dosage and Comments Duration).

### 3.4 Sepsis syndrome- Community acquired and Hospital acquired

- PDF 36 (printed 29), crop points [0.00, 332.76, 595.32, 791.92]: [section-3-4-pdf-36.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-4-pdf-36.png).
- PDF 37 (printed 30), crop points [0.00, 50.00, 595.32, 791.92]: [section-3-4-pdf-37.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-4-pdf-37.png).
- PDF 38 (printed 31), crop points [0.00, 50.00, 595.32, 791.92]: [section-3-4-pdf-38.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-3-4-pdf-38.png).
- PDF 36: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative Comments Infection.
- PDF 37: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: specific infection is dealt under HAI) units IV stat, then 7.5-10 lakhs IV q12h Or Colistin 9MU IV stat, then 4.5 MU IV .

### 4.1 Oesophagitis

- PDF 39 (printed 32), crop points [0.00, 125.61, 595.32, 791.92]: [section-4-1-pdf-39.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-1-pdf-39.png).
- PDF 39: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 4.2 Acute Gastroenteritis

- PDF 40 (printed 33), crop points [0.00, 73.27, 595.32, 548.30]: [section-4-2-pdf-40.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-2-pdf-40.png).
- PDF 40: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative Comments Infection Dosage and (with dosage Duration) and Duration).

### 4.3 Hepatitis Syndrome

- PDF 40 (printed 33), crop points [0.00, 548.30, 595.32, 791.92]: [section-4-3-pdf-40.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-3-pdf-40.png).

### 4.4 Infections of Liver, Gall Bladder and Biliary tract

- PDF 41 (printed 34), crop points [0.00, 73.27, 595.32, 791.92]: [section-4-4-pdf-41.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-4-pdf-41.png).
- PDF 42 (printed 35), crop points [0.00, 50.00, 595.32, 168.81]: [section-4-4-pdf-42.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-4-pdf-42.png).
- PDF 41: 4 grid columns, 5 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).
- PDF 42: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: complications like liver abscess identified).

### 4.5 Appendicitis

- PDF 42 (printed 35), crop points [0.00, 168.81, 595.32, 471.26]: [section-4-5-pdf-42.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-5-pdf-42.png).
- PDF 42: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and Duration) dosage and Duration).

### 4.6 Diverticulitis

- PDF 42 (printed 35), crop points [0.00, 471.26, 595.32, 791.92]: [section-4-6-pdf-42.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-6-pdf-42.png).
- PDF 42: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with dosage Comments Dosage and and Duration) Duration).

### 4.7 Peritonitis – Primary / Secondary

- PDF 43 (printed 36), crop points [0.00, 73.27, 595.32, 373.68]: [section-4-7-pdf-43.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-7-pdf-43.png).
- PDF 43: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and dosage and Duration) Duration).

### 4.8 Splenic Abscess

- PDF 43 (printed 36), crop points [0.00, 373.68, 595.32, 791.92]: [section-4-8-pdf-43.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-8-pdf-43.png).
- PDF 44 (printed 37), crop points [0.00, 50.00, 595.32, 132.81]: [section-4-8-pdf-44.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-8-pdf-44.png).
- PDF 43: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 4.9 Pancreatitis

- PDF 44 (printed 37), crop points [0.00, 132.81, 595.32, 791.92]: [section-4-9-pdf-44.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-9-pdf-44.png).
- PDF 45 (printed 38), crop points [0.00, 50.00, 595.32, 791.92]: [section-4-9-pdf-45.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-4-9-pdf-45.png).
- PDF 44: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and dosage and Duration) Duration).

### 5.1 Cystitis

- PDF 46 (printed 39), crop points [0.00, 107.61, 595.32, 326.88]: [section-5-1-pdf-46.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-5-1-pdf-46.png).
- PDF 46: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage and Alternative (with dosage Comments Infection Duration) and Duration).

### 5.2 Pyelonephritis

- PDF 46 (printed 39), crop points [0.00, 326.88, 595.32, 791.92]: [section-5-2-pdf-46.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-5-2-pdf-46.png).
- PDF 46: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and dosage and Duration) Duration).

### 6.1 Genital Ulcers

- PDF 47 (printed 40), crop points [0.00, 133.89, 595.32, 476.54]: [section-6-1-pdf-47.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-1-pdf-47.png).

### 6.2 Anogenital Warts

- PDF 47 (printed 40), crop points [0.00, 476.54, 595.32, 791.92]: [section-6-2-pdf-47.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-2-pdf-47.png).

### 6.3 Septic abortion

- PDF 48 (printed 41), crop points [0.00, 73.27, 595.32, 563.54]: [section-6-3-pdf-48.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-3-pdf-48.png).
- PDF 48: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with dosage Comments Dosage and Duration) and Duration).

### 6.4 Vaginal Discharge Syndrome

- PDF 48 (printed 41), crop points [0.00, 563.54, 595.32, 791.92]: [section-6-4-pdf-48.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-4-pdf-48.png).

### 6.5 Epididymo-Orchitis

- PDF 49 (printed 42), crop points [0.00, 73.27, 595.32, 535.22]: [section-6-5-pdf-49.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-5-pdf-49.png).
- PDF 49: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 6.6 Pelvic Inflammatory Disease syndrome

- PDF 49 (printed 42), crop points [0.00, 535.22, 595.32, 791.92]: [section-6-6-pdf-49.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-6-pdf-49.png).

### 6.7 Prostatitis

- PDF 50 (printed 43), crop points [0.00, 73.27, 595.32, 442.92]: [section-6-7-pdf-50.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-7-pdf-50.png).
- PDF 50: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 6.8 Puerperal sepsis

- PDF 50 (printed 43), crop points [0.00, 442.92, 595.32, 791.92]: [section-6-8-pdf-50.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-8-pdf-50.png).
- PDF 51 (printed 44), crop points [0.00, 50.00, 595.32, 169.41]: [section-6-8-pdf-51.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-8-pdf-51.png).
- PDF 50: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with dosage Comments and Duration) and Duration).

### 6.9 Urethral discharge syndrome

- PDF 51 (printed 44), crop points [0.00, 169.41, 595.32, 291.00]: [section-6-9-pdf-51.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-9-pdf-51.png).

### 6.10 Chorio-amnionitis

- PDF 51 (printed 44), crop points [0.00, 291.00, 595.32, 791.92]: [section-6-10-pdf-51.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-10-pdf-51.png).
- PDF 52 (printed 45), crop points [0.00, 50.00, 595.32, 791.92]: [section-6-10-pdf-52.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-6-10-pdf-52.png).
- PDF 51: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Comments Duration) dosage and Duration).

### 7.1 Rhinitis/ Common cold

- PDF 53 (printed 46), crop points [0.00, 125.61, 595.32, 791.92]: [section-7-1-pdf-53.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-1-pdf-53.png).
- PDF 54 (printed 47), crop points [0.00, 50.00, 595.32, 124.77]: [section-7-1-pdf-54.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-1-pdf-54.png).
- PDF 53: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative Comments Dosage and (with dosage Duration) and Duration).

### 7.2 Laryngitis/Laryngopharyngitis/URTI

- PDF 54 (printed 47), crop points [0.00, 124.77, 595.32, 791.92]: [section-7-2-pdf-54.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-2-pdf-54.png).
- PDF 55 (printed 48), crop points [0.00, 50.00, 595.32, 553.94]: [section-7-2-pdf-55.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-2-pdf-55.png).
- PDF 54: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 54: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Condition Preferred drug Alternative Penicillin allergy.
- PDF 55: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: Penicillin G 50000 units/kg IV 12 hrly Diphtheria antitoxin: Horse serum < 48 hours: 20,000-40,000 units, Nasopharyngeal.
- PDF 55: 2 grid columns, 6 grid rows; original table retained in primary image/original source text; source header/context: Clinical variables Score.

### 7.3 Sinusitis

- PDF 55 (printed 48), crop points [0.00, 553.94, 595.32, 791.92]: [section-7-3-pdf-55.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-3-pdf-55.png).
- PDF 56 (printed 49), crop points [0.00, 50.00, 595.32, 426.48]: [section-7-3-pdf-56.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-3-pdf-56.png).
- PDF 55: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 56: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: treat like complicated sinusitis as mentioned below A. Signs/symptoms >10 days without improvement. B. fever>39[102], pu.

### 7.4 Otitis media

- PDF 56 (printed 49), crop points [0.00, 426.48, 595.32, 791.92]: [section-7-4-pdf-56.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-4-pdf-56.png).
- PDF 56: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with dosage and Comments Dosage and Duration) Duration).

### 7.5 Otitis externa

- PDF 57 (printed 50), crop points [0.00, 73.27, 595.32, 360.24]: [section-7-5-pdf-57.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-5-pdf-57.png).
- PDF 57: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative Comments Dosage and (with dosage Duration) and Duration).

### 7.6 Head and neck abscesses (peritonsillar/parapharyngeal and retropharyngeal abscess)

- PDF 57 (printed 50), crop points [0.00, 360.24, 595.32, 791.92]: [section-7-6-pdf-57.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-7-6-pdf-57.png).
- PDF 57: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Comments Duration) dosage and Duration).

### 8.1 Oropharyngeal Candidiasis

- PDF 58 (printed 51), crop points [0.00, 117.57, 595.32, 791.92]: [section-8-1-pdf-58.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-8-1-pdf-58.png).
- PDF 58: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) Dosage and Duration).

### 9.1 Paronychia

- PDF 59 (printed 52), crop points [0.00, 117.57, 595.32, 471.14]: [section-9-1-pdf-59.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-1-pdf-59.png).
- PDF 59: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 9.2 Impetigo

- PDF 59 (printed 52), crop points [0.00, 471.14, 595.32, 791.92]: [section-9-2-pdf-59.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-2-pdf-59.png).
- PDF 60 (printed 53), crop points [0.00, 50.00, 595.32, 155.25]: [section-9-2-pdf-60.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-2-pdf-60.png).
- PDF 59: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 9.3 Cellulitis

- PDF 60 (printed 53), crop points [0.00, 155.25, 595.32, 791.92]: [section-9-3-pdf-60.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-3-pdf-60.png).
- PDF 61 (printed 54), crop points [0.00, 50.00, 595.32, 363.96]: [section-9-3-pdf-61.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-3-pdf-61.png).
- PDF 60: 4 grid columns, 5 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).
- PDF 61: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: like bullae, skin sloughing or signs of systemic infection Vancomycin 15 to 20 mg/kg/dose every 8 to 12 hours along with.

### 9.4 Necrotizing fasciitis

- PDF 61 (printed 54), crop points [0.00, 363.96, 595.32, 791.92]: [section-9-4-pdf-61.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-4-pdf-61.png).
- PDF 62 (printed 55), crop points [0.00, 50.00, 595.32, 272.40]: [section-9-4-pdf-62.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-4-pdf-62.png).
- PDF 61: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with dosage and Comments and Duration) Duration).

### 9.5 Primary Pyomyositis

- PDF 62 (printed 55), crop points [0.00, 272.40, 595.32, 625.94]: [section-9-5-pdf-62.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-5-pdf-62.png).
- PDF 62: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 9.6 Folliculitis

- PDF 62 (printed 55), crop points [0.00, 625.94, 595.32, 791.92]: [section-9-6-pdf-62.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-6-pdf-62.png).
- PDF 63 (printed 56), crop points [0.00, 50.00, 595.32, 791.92]: [section-9-6-pdf-63.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-6-pdf-63.png).
- PDF 64 (printed 57), crop points [0.00, 50.00, 595.32, 791.92]: [section-9-6-pdf-64.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-6-pdf-64.png).
- PDF 62: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) Dosage and Duration).
- PDF 63: 4 grid columns, 5 grid rows; projected as source treatment columns; source header/context: • Cephalexin 250- 500mg QID (25–50 mg/kg/day) • Cefadroxil 500 mg q12h • Amoxicillin- clavulanate combination: 625mg TDS.
- PDF 64: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: Eosinophilic folliculitis Topical corticosteroids, antihistamines, phototherapy, and Itraconazole 100- 200mg/day for 3 w.

### 9.7 Diabetic foot infections (DFI)

- PDF 65 (printed 58), crop points [0.00, 73.27, 595.32, 791.92]: [section-9-7-pdf-65.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-7-pdf-65.png).
- PDF 66 (printed 59), crop points [0.00, 50.00, 595.32, 791.92]: [section-9-7-pdf-66.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-9-7-pdf-66.png).
- PDF 65: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 66: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: expected, or if the patient has severe peripheral arterial disease..

### 10.1 Acute Osteomyelitis

- PDF 67 (printed 60), crop points [0.00, 107.61, 595.32, 791.92]: [section-10-1-pdf-67.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-1-pdf-67.png).
- PDF 68 (printed 61), crop points [0.00, 50.00, 595.32, 147.21]: [section-10-1-pdf-68.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-1-pdf-68.png).
- PDF 67: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 10.2 Chronic Osteomyelitis

- PDF 68 (printed 61), crop points [0.00, 147.21, 595.32, 611.54]: [section-10-2-pdf-68.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-2-pdf-68.png).
- PDF 68: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) Dosage and Duration).

### 10.3 Gas gangrene

- PDF 68 (printed 61), crop points [0.00, 611.54, 595.32, 791.92]: [section-10-3-pdf-68.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-3-pdf-68.png).
- PDF 69 (printed 62), crop points [0.00, 50.00, 595.32, 401.16]: [section-10-3-pdf-69.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-3-pdf-69.png).
- PDF 68: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).
- PDF 69: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: arise in traumatized tissue. Spontaneous Gas gangrene Aggressive surgical debridement In spontaneous gas gangrene; Inj P.

### 10.4 Septic arthritis

- PDF 69 (printed 62), crop points [0.00, 401.16, 595.32, 791.92]: [section-10-4-pdf-69.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-4-pdf-69.png).
- PDF 70 (printed 63), crop points [0.00, 50.00, 595.32, 124.77]: [section-10-4-pdf-70.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-4-pdf-70.png).
- PDF 69: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Alternative (with First Line (with Type of Infection Dosage and Comments Dosage and Duration) Duration).

### 10.5 Skin and soft tissue injuries

- PDF 70 (printed 63), crop points [0.00, 124.77, 595.32, 791.92]: [section-10-5-pdf-70.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-5-pdf-70.png).
- PDF 70: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative Comments Dosage and (with dosage Duration) and Duration).

### 10.6 Orthopaedic implant associated infections

- PDF 71 (printed 64), crop points [0.00, 73.27, 595.32, 791.92]: [section-10-6-pdf-71.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-6-pdf-71.png).
- PDF 72 (printed 65), crop points [0.00, 50.00, 595.32, 330.48]: [section-10-6-pdf-72.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-6-pdf-72.png).
- PDF 71: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and Duration) dosage and Duration).

### 10.7 Surgical Prophylaxis

- PDF 72 (printed 65), crop points [0.00, 330.48, 595.32, 791.92]: [section-10-7-pdf-72.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-7-pdf-72.png).
- PDF 73 (printed 66), crop points [0.00, 50.00, 595.32, 791.92]: [section-10-7-pdf-73.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-7-pdf-73.png).
- PDF 74 (printed 67), crop points [0.00, 50.00, 595.32, 791.92]: [section-10-7-pdf-74.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-7-pdf-74.png).
- PDF 75 (printed 68), crop points [0.00, 50.00, 595.32, 791.92]: [section-10-7-pdf-75.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-10-7-pdf-75.png).
- PDF 72: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 73: 3 grid columns, 5 grid rows; original table retained in primary image/original source text; source header/context: Classification Criteria Risk (%).
- PDF 73: 4 grid columns, 5 grid rows; original table retained in primary image/original source text; source header/context: Specific operations Expected Antibiotic of choice Dosage in adults organism.
- PDF 74: 4 grid columns, 14 grid rows; original table retained in primary image/original source text; source header/context: Appendectomy for uncomplicated appendicitis Enteric gram- negative bacilli, anaerobes Cefuroxime 1-2 g IV.
- PDF 75: 3 grid columns, 18 grid rows; original table retained in primary image/original source text; source header/context: Drug Adult dose Paediatric dose.

### 11.1 Conjunctivitis & Keratitis

- PDF 76 (printed 69), crop points [0.00, 107.61, 595.32, 791.92]: [section-11-1-pdf-76.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-76.png).
- PDF 77 (printed 70), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-1-pdf-77.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-77.png).
- PDF 78 (printed 71), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-1-pdf-78.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-78.png).
- PDF 79 (printed 72), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-1-pdf-79.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-79.png).
- PDF 80 (printed 73), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-1-pdf-80.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-80.png).
- PDF 81 (printed 74), crop points [0.00, 50.00, 595.32, 286.32]: [section-11-1-pdf-81.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-1-pdf-81.png).
- PDF 76: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Dosage Comments Duration) and Duration).
- PDF 77: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: testing with cultures). Duration: 15 days. Steroid use with antibiotics is controversial as studies report mixed results.
- PDF 78: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Chlamydia and Gonococcus..
- PDF 79: 4 grid columns, 7 grid rows; projected as source treatment columns; source header/context: weeks to months, depending on resolution of signs and symptoms until ulcer heals..
- PDF 80: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: hours and no results coming on culture, decision to add another topical antifungal agent is to be taken. In resistant ca.

### 11.2 Endophthalmitis

- PDF 81 (printed 74), crop points [0.00, 286.32, 595.32, 791.92]: [section-11-2-pdf-81.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-2-pdf-81.png).
- PDF 82 (printed 75), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-2-pdf-82.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-2-pdf-82.png).
- PDF 83 (printed 76), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-2-pdf-83.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-2-pdf-83.png).
- PDF 84 (printed 77), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-2-pdf-84.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-2-pdf-84.png).
- PDF 81: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 82: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: retina, allows definitive treatment, reduces the load of infection, and reduces the severity of the disease, and acceler.
- PDF 83: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: testing before initiation of antibiotics..
- PDF 84: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: examinations to assess treatment response..

### 11.3 Periocular infections (Eyelid infections, Orbital cellulitis)

- PDF 85 (printed 78), crop points [0.00, 73.27, 595.32, 791.92]: [section-11-3-pdf-85.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-3-pdf-85.png).
- PDF 86 (printed 79), crop points [0.00, 50.00, 595.32, 791.92]: [section-11-3-pdf-86.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-3-pdf-86.png).
- PDF 85: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and Dosage and Duration) Duration).
- PDF 86: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and Dosage and Duration) Duration).

### 11.4 Retinitis

- PDF 87 (printed 80), crop points [0.00, 73.27, 595.32, 791.92]: [section-11-4-pdf-87.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-11-4-pdf-87.png).
- PDF 87: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with Comments Infection Dosage and dosage and Duration) Duration).

### 12.1 Bronchitis

- PDF 88 (printed 81), crop points [0.00, 117.57, 595.32, 260.61]: [section-12-1-pdf-88.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-1-pdf-88.png).
- PDF 88: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative (with Comments Infection (with Dosage dosage and and Duration) Duration).

### 12.2 Bronchiolitis

- PDF 88 (printed 81), crop points [0.00, 260.61, 595.32, 412.68]: [section-12-2-pdf-88.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-2-pdf-88.png).
- PDF 88: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Comments Duration) dosage and Duration).

### 12.3 Infective exacerbation of asthma/COPD

- PDF 88 (printed 81), crop points [0.00, 412.68, 595.32, 791.92]: [section-12-3-pdf-88.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-3-pdf-88.png).
- PDF 89 (printed 82), crop points [0.00, 50.00, 595.32, 309.36]: [section-12-3-pdf-89.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-3-pdf-89.png).
- PDF 88: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).

### 12.4 Infective Exacerbation of Bronchiectasis

- PDF 89 (printed 82), crop points [0.00, 309.36, 595.32, 791.92]: [section-12-4-pdf-89.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-4-pdf-89.png).
- PDF 89: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage Alternative (with Comments Infection and Duration) dosage and Duration).

### 12.5 Community Acquired Pneumonia

- PDF 90 (printed 83), crop points [0.00, 73.27, 595.32, 791.92]: [section-12-5-pdf-90.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-5-pdf-90.png).
- PDF 91 (printed 84), crop points [0.00, 50.00, 595.32, 371.52]: [section-12-5-pdf-91.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-5-pdf-91.png).
- PDF 90: 4 grid columns, 6 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).
- PDF 91: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: Doxycycline 100mg q12h Duration: 7 days Doxycycline 100mg q12h Duration: 7 days Necrotizing pneumonia preceding Influenz.

### 12.6 Lung Abscess

- PDF 91 (printed 84), crop points [0.00, 371.52, 595.32, 791.92]: [section-12-6-pdf-91.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-6-pdf-91.png).
- PDF 92 (printed 85), crop points [0.00, 50.00, 595.32, 242.25]: [section-12-6-pdf-92.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-6-pdf-92.png).
- PDF 91: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with dosage Comments and Duration) and Duration).

### 12.7 Para-pneumonic pleural effusion/empyema

- PDF 92 (printed 85), crop points [0.00, 242.25, 595.32, 791.92]: [section-12-7-pdf-92.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-7-pdf-92.png).
- PDF 93 (printed 86), crop points [0.00, 50.00, 595.32, 791.92]: [section-12-7-pdf-93.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-12-7-pdf-93.png).
- PDF 92: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: First Line (with Dosage Alternative (with Type of Infection Comments and Duration) dosage and Duration).
- PDF 93: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: open-thoracotomy is indicated..

### 13.1 Botulism

- PDF 94 (printed 87), crop points [0.00, 125.61, 595.32, 411.96]: [section-13-1-pdf-94.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-1-pdf-94.png).
- PDF 94: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative Comments Infection (with (with Dosage dosage and and Duration) Duration).

### 13.2 Diphtheria

- PDF 94 (printed 87), crop points [0.00, 411.96, 595.32, 791.92]: [section-13-2-pdf-94.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-2-pdf-94.png).
- PDF 95 (printed 88), crop points [0.00, 50.00, 595.32, 369.24]: [section-13-2-pdf-95.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-2-pdf-95.png).
- PDF 94: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage and Duration) Alternative (with Comments Infection dosage and Duration).
- PDF 95: 4 grid columns, 1 grid rows; projected as source treatment columns; source header/context: toxicity of the patient, site and size of membrane, and duration of illness Pharyngeal/laryngeal 20000- disease < 2days .
- PDF 95: 2 grid columns, 3 grid rows; original table retained in primary image/original source text; source header/context: Pharyngeal/laryngeal disease < 2days duration 20000- 40000 Units.

### 13.3 Tetanus

- PDF 95 (printed 88), crop points [0.00, 369.24, 595.32, 791.92]: [section-13-3-pdf-95.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-3-pdf-95.png).
- PDF 96 (printed 89), crop points [0.00, 50.00, 595.32, 138.21]: [section-13-3-pdf-96.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-3-pdf-96.png).
- PDF 95: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage Alternative (with Comments Infection and Duration) dosage and Duration).

### 13.4 Toxic shock syndrome

- PDF 96 (printed 89), crop points [0.00, 138.21, 595.32, 791.92]: [section-13-4-pdf-96.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-13-4-pdf-96.png).
- PDF 96: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative Comments Infection (with (with dosage Dosage and and Duration) Duration).

### 14.1 Animal (Dog/cat/monkey/Human)

- PDF 97 (printed 90), crop points [0.00, 107.61, 595.32, 791.92]: [section-14-1-pdf-97.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-14-1-pdf-97.png).
- PDF 97: 4 grid columns, 7 grid rows; projected as source treatment columns; source header/context: Animal Bite First Line (with Alternative (with dosage Comments Dosage and Duration) and Duration).

### 14.2 Insect Bites

- PDF 98 (printed 91), crop points [0.00, 73.27, 595.32, 791.92]: [section-14-2-pdf-98.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-14-2-pdf-98.png).
- PDF 98: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line Alternative Comments Infection (with (with Dosage and dosage and Duration) Duration).

### 15.1 Minor Burn Wounds

- PDF 99 (printed 92), crop points [0.00, 107.61, 595.32, 553.70]: [section-15-1-pdf-99.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-15-1-pdf-99.png).
- PDF 99: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Types of Burn First Line (with Dosage and Alternative (with dosage Comments Duration) and Duration).

### 15.2 Major burn wounds

- PDF 99 (printed 92), crop points [0.00, 553.70, 595.32, 791.92]: [section-15-2-pdf-99.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-15-2-pdf-99.png).
- PDF 100 (printed 93), crop points [0.00, 50.00, 595.32, 791.92]: [section-15-2-pdf-100.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-15-2-pdf-100.png).
- PDF 101 (printed 94), crop points [0.00, 50.00, 595.32, 791.92]: [section-15-2-pdf-101.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-15-2-pdf-101.png).
- PDF 99: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage Alternative (with dosage Comments Burn and Duration) and Duration).
- PDF 100: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: with occlusive dressings but does not penetrate eschar and it depletes electrolytes, and stains the local environment, b.

### 16.1 Odontogenic tooth infections

- PDF 102 (printed 95), crop points [0.00, 117.45, 595.32, 791.92]: [section-16-1-pdf-102.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-16-1-pdf-102.png).
- PDF 103 (printed 96), crop points [0.00, 50.00, 595.32, 791.92]: [section-16-1-pdf-103.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-16-1-pdf-103.png).
- PDF 102: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with dosage Comments Dosage and and Duration) Duration).

### 17.1 Febrile neutropenia syndrome

- PDF 104 (printed 97), crop points [0.00, 99.45, 595.32, 791.92]: [section-17-1-pdf-104.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-1-pdf-104.png).
- PDF 105 (printed 98), crop points [0.00, 50.00, 595.32, 456.38]: [section-17-1-pdf-105.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-1-pdf-105.png).
- PDF 104: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and Duration) dosage and Duration).

### 17.2 Infections in Solid Organ Transplant recipients

- PDF 105 (printed 98), crop points [0.00, 456.38, 595.32, 791.92]: [section-17-2-pdf-105.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-2-pdf-105.png).
- PDF 105: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).

### 17.3 Infections in Asplenia

- PDF 106 (printed 99), crop points [0.00, 65.11, 595.32, 494.54]: [section-17-3-pdf-106.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-3-pdf-106.png).
- PDF 106: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and dosage and Duration) Duration).

### 17.4 Invasive Fungal Infections

- PDF 106 (printed 99), crop points [0.00, 494.54, 595.32, 791.92]: [section-17-4-pdf-106.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-106.png).
- PDF 107 (printed 100), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-107.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-107.png).
- PDF 108 (printed 101), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-108.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-108.png).
- PDF 109 (printed 102), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-109.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-109.png).
- PDF 110 (printed 103), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-110.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-110.png).
- PDF 111 (printed 104), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-111.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-111.png).
- PDF 112 (printed 105), crop points [0.00, 50.00, 595.32, 791.92]: [section-17-4-pdf-112.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-17-4-pdf-112.png).
- PDF 106: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Alternative (with Comments Dosage and Duration) dosage and Duration).
- PDF 107: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: are clinically stable, and in whom repeat cultures while on antifungal therapy are negative..
- PDF 108: 3 grid columns, 4 grid rows; original table retained in primary image/original source text; source header/context: BMT pre-engraftment and post-engraftment prophylaxis.
- PDF 109: 3 grid columns, 4 grid rows; original table retained in primary image/original source text; source header/context: First CMV viral load at Day 28. If CMV viral load is negative then repeat viral loads are sent based on risk stratificat.
- PDF 110: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Clinical Empirical Alternate Antimicrobial Comments Condition Antimicrobial Agents Agents.
- PDF 111: 4 grid columns, 5 grid rows; projected as source treatment columns; source header/context: followed by 15mg/kg q 8-12h Duration: 5-7 days +/- Clindamycin 600- 900mg q8h.

### 18.1 Fever in ICU

- PDF 113 (printed 106), crop points [0.00, 99.45, 595.32, 470.78]: [section-18-1-pdf-113.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-1-pdf-113.png).
- PDF 113: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage and Alternative (with Comments Duration) dosage and Duration).

### 18.2 Invasive Candidiasis

- PDF 113 (printed 106), crop points [0.00, 470.78, 595.32, 791.92]: [section-18-2-pdf-113.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-2-pdf-113.png).
- PDF 114 (printed 107), crop points [0.00, 50.00, 595.32, 124.53]: [section-18-2-pdf-114.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-2-pdf-114.png).
- PDF 113: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Dosage and Duration) Alternative Comments Infection (with dosage and Duration).

### 18.3 Hospital-acquired pneumonia or Ventilator associated pneumonia

- PDF 114 (printed 107), crop points [0.00, 124.53, 595.32, 791.92]: [section-18-3-pdf-114.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-3-pdf-114.png).
- PDF 115 (printed 108), crop points [0.00, 50.00, 595.32, 428.88]: [section-18-3-pdf-115.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-3-pdf-115.png).
- PDF 114: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).

### 18.4 Central Line-Associated Bloodstream Infection (CLABSI)

- PDF 115 (printed 108), crop points [0.00, 428.88, 595.32, 791.92]: [section-18-4-pdf-115.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-4-pdf-115.png).
- PDF 116 (printed 109), crop points [0.00, 50.00, 595.32, 791.92]: [section-18-4-pdf-116.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-4-pdf-116.png).
- PDF 117 (printed 110), crop points [0.00, 50.00, 595.32, 544.82]: [section-18-4-pdf-117.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-4-pdf-117.png).
- PDF 115: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 116: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: obtained. If a blood sample cannot be drawn from a peripheral vein, it is recommended that 2 blood samples should be dra.

### 18.5 Antibiotic Associated Diarrhoea

- PDF 117 (printed 110), crop points [0.00, 544.82, 595.32, 791.92]: [section-18-5-pdf-117.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-5-pdf-117.png).
- PDF 118 (printed 111), crop points [0.00, 50.00, 595.32, 102.09]: [section-18-5-pdf-118.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-5-pdf-118.png).

### 18.6 Catheter associated urinary tract infection (CAUTI)

- PDF 118 (printed 111), crop points [0.00, 102.09, 595.32, 791.92]: [section-18-6-pdf-118.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-6-pdf-118.png).
- PDF 119 (printed 112), crop points [0.00, 50.00, 595.32, 160.05]: [section-18-6-pdf-119.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-6-pdf-119.png).
- PDF 118: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).

### 18.7 Intra-abdominal infection

- PDF 119 (printed 112), crop points [0.00, 160.05, 595.32, 791.92]: [section-18-7-pdf-119.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-18-7-pdf-119.png).
- PDF 119: 4 grid columns, 2 grid rows; projected as source treatment columns; source header/context: Type of First Line (with Alternative (with dosage and Comments Infection Dosage and Duration) Duration).

### 19.1 Neonatal Infections

- PDF 120 (printed 113), crop points [0.00, 99.45, 595.32, 791.92]: [section-19-1-pdf-120.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-120.png).
- PDF 121 (printed 114), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-121.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-121.png).
- PDF 122 (printed 115), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-122.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-122.png).
- PDF 123 (printed 116), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-123.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-123.png).
- PDF 124 (printed 117), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-124.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-124.png).
- PDF 125 (printed 118), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-125.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-125.png).
- PDF 126 (printed 119), crop points [0.00, 50.00, 595.32, 791.92]: [section-19-1-pdf-126.png](../../frontend/public/assets/infection-sources/ncdc-sections/section-19-1-pdf-126.png).
- PDF 120: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 121: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 122: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 123: 4 grid columns, 4 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
- PDF 124: 4 grid columns, 3 grid rows; projected as source treatment columns; source header/context: Type of Infection First Line (with Dosage Alternative (with Comments and Duration) dosage and Duration).
