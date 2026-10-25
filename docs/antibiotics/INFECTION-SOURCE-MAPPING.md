# Infection source mapping

Static educational reference. All entries are unreviewed, non-executable, and ineligible for clinical use; this is not local policy.

Coverage: 19 NCDC groups; 87/87 named NCDC TOC subsections; 105 total infection entries; 248 clinical-context records; 125 selectable source-treatment options; 148 contexts have no selectable regimen and an explicit review hold.

Heading coverage is not a claim that every treatment branch is fully transcribed. Conditional/ambiguous cells and missing field values remain visible as gaps. The neonatal section is present, but complex age/PMA/PNA dosing is held. Supplemental standard-dose tables are not attached to infections by inference. Source drug monographs, renal adjustments and dialysis references are deferred.

## Frozen sources

- NCDC / ICMR National Treatment Guidelines for Antimicrobial Use in Infectious Disease Syndromes — Version 2.0 — November 2025; SHA-256 `0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a`; [publisher PDF](https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf).
- JIPMER Antibiotic Policy — 2026 edition — Version 1.0 (202604061000), 15 April 2026; SHA-256 `c8b4078d80cf375a0503c2ca4e38e0ba869dca2ac44d08e107dc7b227565f4d4`; [publisher PDF](https://www.jipmer.edu.in/sites/default/files/JIPMER%20Antibiotic%20Policy%202026.pdf).

NCDC printed page = PDF page minus 7; JIPMER system therapy pages used here = PDF page minus 8. Locators refer to the frozen snapshots, not an assumed current web version.

## Precedence and JIPMER crosswalk

| JIPMER scope (printed pages / PDF pages) | Mapping decision |
| --- | --- |
| Sepsis 21–22 / 29–30; AUFI 26–29 / 34–37 | NCDC 3.1–3.4 owns overlapping empirical syndromes. JIPMER does not replace NCDC conditional/figure holds. |
| Bacteraemia principles 23 / 31 | Not a standalone fixed-dose infection entry. Pathogen-specific/definitive bacteremia context requires detailed source matching before any future addition. |
| CRBSI 24–25 / 32–33 | Maps to NCDC 18.4; NCDC precedence. Catheter/organism duration branches not merged. |
| CAP, HAP/VAP 30–35 / 38–43 | NCDC 12.5 and 18.3 own overlapping severity/acquisition contexts. No JIPMER CAP regimens exposed as peers. |
| Aspiration pneumonia RES-06, 36 / 44 | Added with community/hospital contexts: distinct named syndrome not supplied as NCDC pneumonia context. NCDC lung-abscess aspiration discussion is not aspiration-pneumonia treatment. Severe/MRSA branches held. |
| Lung abscess RES-07, 36 / 44 | NCDC 12.6 primary/secondary contexts take precedence. |
| Pharyngitis, sinusitis, otitis, bronchitis, AECOPD 37 / 45 | NCDC 7.2 (includes pharyngitis Centor rows), 7.3, 7.4, 12.1, 12.3 take precedence. |
| Cystitis UTI-01/02, pyelonephritis UTI-03/04, urosepsis UTI-05, CAUTI UTI-08, 40–41 / 48–49 | NCDC 5.1/5.2, 3.4 and 18.6 retained. JIPMER complicated-UTI and urosepsis fine-grained overlap needs further matching; these are not asserted to be uncovered simply because NCDC headings are broader. |
| Perinephric abscess UTI-06; renal abscess UTI-07, 41 / 49 | Added as precise separate names, each with pyelonephritis/bacteraemia source branches. JIPMER supplies cross-references, not standalone doses; no cross-source dose substitution. |
| Diarrhoea GIT-01–03 and pathogen-specific treatment, 42–45 / 50–53 | Empirical syndrome overlap with NCDC 4.2. Distinct pathogen-specific entries are searchable, mostly held pending branch review; amoebic dysentery remains NCDC-owned because NCDC 4.2 explicitly supplies a metronidazole adjunct. |
| SBP/secondary peritonitis, liver abscess, cholecystitis, cholangitis GIT-04–09, 46–48 / 54–56 | NCDC 4.4 and 4.7 context rows take precedence. |
| Intra-abdominal abscess GIT-10, 48 / 56 | Searchable source-match hold pending comparison with NCDC 4.5–4.8 and 18.7 acquisition/source-control contexts. |
| Cellulitis SSI-01–04; impetigo SSI-06/07; diabetic foot SSI-11; animal bites, 50–54 / 58–62 | NCDC 9.2, 9.3, 9.7 and 14.1 take precedence. Purulent/severity subgroups remain source-owned. |
| Carbuncle/furuncle/abscess SSI-05; Vibrio/Aeromonas injuries SSI-08–10; snake bite SSI-12, 51–54 / 59–62 | NCDC 9.6 supplies furuncle/carbuncle rows. Distinct Vibrio/Aeromonas and snake-bite contexts are searchable held additions; post-trauma overlap remains NCDC 10.5-owned. |
| Necrotizing fasciitis SSI-13–15, 55–56 / 63–64 | NCDC 9.4 owns syndrome. Distinct organism-specific type/exposure branches are searchable JIPMER held contexts. |
| Septic arthritis BJI-01–06, 57–58 / 65–66 | NCDC 10.4 owns empirical syndrome. Infant/organism/Gram-stain subgroups are not merged across sources; finer review deferred. |
| Meningitis CNS-01; brain abscess CNS-02, 59–60 / 67–68 | NCDC 2.1–2.5 precede overlapping contexts. |
| Subdural empyema CNS-03; epidural abscess CNS-04, 61 / 69 | Added as named intracranial infections not named NCDC treatment entries, with sinus/otitis and postoperative contexts separated. Ambiguous interval/optional agent branch held. |
| Endocarditis initial/definitive CVS-01–13, 62–65 / 70–73 | NCDC 1.1 empirical context takes precedence. Distinct organism/AST-specific definitive contexts are searchable JIPMER held cases in the same infection entry. |
| Duration appendix, dosing, surgical and endocarditis prophylaxis, 66–93 / 74–101 | Not used to backfill missing infection fields. NCDC 10.7 surgical-prophylaxis heading remains present; additional JIPMER prophylaxis contexts deferred. |

## JIPMER disease-row audit

| Source row | Named context(s) | PDF page(s) | Decision |
| --- | --- | --- | --- |
| SYS-01 | Sepsis (community acquired) | 30 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-02 | Septic shock (community acquired) | 30 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-03 | Septic shock (hospital acquired) | 30 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-04 | CRBSI | 33 | NCDC 18.4 precedence |
| SYS-05 | AUFI without sepsis/organ dysfunction | 36 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-06 | AUFI with sepsis/organ dysfunction | 36 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-07 | Suspected enteric fever | 37 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-08 | Suspected scrub typhus | 37 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| SYS-09 | Suspected leptospirosis — mild / moderate to severe | 37 | NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available |
| RES-01 | CAP — OPD | 41 | NCDC 12.5 precedes |
| RES-02 | CAP — inpatient non-ICU | 41 | NCDC 12.5 precedes |
| RES-03 | CAP — ICU | 41 | NCDC 12.5 precedes |
| RES-04 | VAP | 43 | NCDC 18.3 precedes |
| RES-05 | HAP without VAP | 43 | NCDC 18.3 precedes |
| RES-06 | Aspiration pneumonia — community / hospital | 44 | Added JIPMER aspiration contexts; severe/MRSA branches held |
| RES-07 | Lung abscess — primary / secondary | 44 | NCDC 12.6 precedence |
| RES-08 | Acute pharyngitis | 45 | NCDC 7.2 pharyngitis rows precede |
| RES-09 | Acute sinusitis | 45 | NCDC 7.3 precedes |
| RES-10 | Acute otitis media | 45 | NCDC 7.4 precedes |
| RES-11 | Acute bronchitis | 45 | NCDC 12.1 precedes |
| RES-12 | AECOPD | 45 | NCDC 12.3 precedes |
| UTI-01 | Uncomplicated cystitis | 48 | NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held |
| UTI-02 | Complicated cystitis | 48 | NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held |
| UTI-03 | Pyelonephritis | 48 | NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held |
| UTI-04 | Complicated pyelonephritis | 48 | NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held |
| UTI-05 | Urosepsis | 49 | NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held |
| UTI-06 | Perinephric abscess | 49 | Added precise JIPMER named source cross-reference contexts |
| UTI-07 | Renal abscess | 49 | Added precise JIPMER named source cross-reference contexts |
| UTI-08 | CAUTI | 49 | NCDC 18.6 precedes |
| GIT-01 | Non-bloody diarrhoea | 50 | NCDC 4.2 precedes empirical syndrome; distinct pathogen-specific extensions separately listed |
| GIT-02 | Bloody diarrhoea with fever | 50 | NCDC 4.2 precedes empirical syndrome; distinct pathogen-specific extensions separately listed |
| GIT-03 | Bloody diarrhoea without fever — E. histolytica / EHEC | 50 | NCDC 4.2 precedes empirical syndrome; distinct pathogen-specific extensions separately listed |
| GIT-04 | SBP (primary) | 54 | NCDC 4.4/4.7 precede |
| GIT-05 | Secondary bacterial peritonitis | 54 | NCDC 4.4/4.7 precede |
| GIT-06 | Liver abscess — amoebic | 55 | NCDC 4.4/4.7 precede |
| GIT-07 | Liver abscess — pyogenic | 55 | NCDC 4.4/4.7 precede |
| GIT-08 | Acute cholecystitis | 56 | NCDC 4.4/4.7 precede |
| GIT-09 | Cholangitis | 56 | NCDC 4.4/4.7 precede |
| GIT-10 | Intra-abdominal abscess | 56 | Searchable source-match hold against NCDC abscess/peritonitis contexts |
| SSI-01 | Mild non-purulent cellulitis | 58 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-02 | Moderate/severe non-purulent cellulitis | 58 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-03 | Mild purulent cellulitis | 58 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-04 | Moderate/severe purulent cellulitis | 58 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-05 | Carbuncle, furuncle and abscess | 59 | NCDC 9.6 furuncle/carbuncle rows precede; abscess cross-reference unresolved |
| SSI-06 | Impetigo — non-bullous | 59 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-07 | Impetigo — bullous | 59 | NCDC 9.2/9.3 precede; finer purulence/severity matching held |
| SSI-08 | Vibrio vulnificus cellulitis — sea water | 59 | Added held JIPMER pathogen/exposure context in NCDC cellulitis entry |
| SSI-09 | Aeromonas cellulitis — fresh water | 59 | Added held JIPMER pathogen/exposure context in NCDC cellulitis entry |
| SSI-10 | Infected post-traumatic wound — mild/moderate / severe | 59 | NCDC 10.5 precedes; finer severity source matching held |
| SSI-11 | Diabetic foot — noninfected / mild / moderate / severe | 61 | NCDC 9.7 precedes |
| SSI-12 | Snake bite cellulitis / animal and human bites | 62 | Snake-bite context added as hold; mammal/human bites NCDC 14.1 precedes |
| SSI-13 | Necrotizing fasciitis type I | 64 | Generic syndrome NCDC 9.4 precedes; distinct type I context added held |
| SSI-14 | Necrotizing fasciitis type II | 64 | Generic syndrome NCDC 9.4 precedes; distinct type II context added held |
| SSI-15 | Necrotizing fasciitis type III — Aeromonas / Vibrio | 64 | Generic syndrome NCDC 9.4 precedes; distinct organism/exposure contexts added held |
| BJI-01 | Septic arthritis — acute monoarthritis; infants / children-adults / melioidosis | 66 | NCDC 10.4 precedes; infant/Gram-stain/melioidosis finer match held |
| BJI-02 | Acute polyarticular arthritis | 66 | Added JIPMER named aetiology-dependent hold |
| BJI-03 | Chronic monoarthritis | 66 | Added JIPMER named no-dose hold |
| BJI-04 | Prosthetic joint infection | 66 | NCDC 10.6 implant infection context retained; definitive species matching held |
| BJI-05 | Extremity osteomyelitis | 66 | NCDC 10.1/10.2 precede |
| BJI-06 | Vertebral osteomyelitis +/- epidural abscess | 66 | Added JIPMER vertebral anatomical context hold |
| CNS-01 | Acute bacterial meningitis | 67 | NCDC 2.1–2.5 precedence |
| CNS-02 | Brain abscess | 68 | NCDC 2.1–2.5 precedence |
| CNS-03 | Subdural empyema | 69 | Added JIPMER named sinus/otitis and postoperative contexts; ambiguous interval/optional branch held |
| CNS-04 | Epidural abscess | 69 | Added JIPMER named sinus/otitis and postoperative contexts; ambiguous interval/optional branch held |
| CVS-01 | Native valve endocarditis — community acute | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-02 | Native valve endocarditis — community subacute | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-03 | Native valve endocarditis — healthcare associated | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-04 | Prosthetic valve endocarditis — early <1 year | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-05 | Prosthetic valve endocarditis — late >1 year | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-06 | Culture-negative endocarditis | 71 | NCDC 1.1 empirical precedence; finer acquisition/valve timing match held |
| CVS-07 | Definitive streptococcal penicillin-susceptible / S. gallolyticus | 72 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-08 | Definitive streptococcal relatively penicillin-resistant | 72 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-09 | Definitive streptococcal moderately penicillin-resistant / Granulicatella / Abiotrophia / Gemella | 72 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-10 | Definitive enterococci | 73 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-11 | Definitive MSSA / MRSA native valve | 73 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-12 | Definitive MSSA / MRSA prosthetic valve | 73 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |
| CVS-13 | Definitive HACEK | 73 | Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement |

Repeated source IDs preserve the named variants in this row audit (for example UTI-06 secondary to pyelonephritis/bacteraemia and SSI-12 snake/mammal bites); a repeated ID is not treated as a unique infection identifier.

Unnumbered JIPMER pathogen-specific diarrhoea tables PDF52–53: cholera, Shigella, NTS, Campylobacter, E. coli pathotypes, EHEC, Vibrio parahaemolyticus and Yersinia have searchable records; amoebic dysentery overlaps the explicit metronidazole adjunct in NCDC4.2 and remains NCDC-owned pending exact luminal-agent context review. Enteric fever remains NCDC3.2-owned.

## Extraction and curation

TOC names and section numbers are authoritative for navigation. Actual heading coordinates assign each four-column grid to a section; a section-number-like dose is rejected unless its page and name prefix match the TOC. Thin rectangle borders recover the table structure without duplicate backing rectangles. Separate continuation pages are retained in locators and held when source-cell continuity needs review.

Safe NCDC first-line cells are retained as source instructions. Unresolved OR/slash/conditional/cross-reference cells have zero selectable regimens and retain source text in notes. Alternative treatment columns are not promoted to primary peer regimens. CAP primary branch scope and page-91 continuation were explicitly curated into selectable full combinations. Routes absent for CAP oral agents remain absent. Source dose anomalies are not silently corrected.

TDD: five content/coverage tests failed against the missing catalogue before implementation. Critical numerical/source checks: CAP PDF90–91 (amoxicillin 1g q8h, ceftriaxone 2g OD IV, doxycycline 100mg q12h; 5–7 days or 7 days in pseudomonal-risk context); urinary NCDC PDF46; JIPMER UTI-06/07 PDF49 (source cross-references, at least 2–3 weeks); JIPMER aspiration PDF44; intracranial abscess PDF69. These checks do not constitute clinical validation.

## NCDC heading inventory and extraction holds

| Section | Infection | PDF page(s) | Contexts / options / held contexts |
| --- | --- | --- | --- |
| 1.1 | Infective Endocarditis | 21, 72, 73 | 12 / 0 / 12 |
| 1.2 | Acute Myocarditis | 23 | 1 / 1 / 0 |
| 1.3 | Pericarditis | 23 | 2 / 2 / 0 |
| 1.4 | Rheumatic fever | 24 | 1 / 0 / 1 |
| 2.1 | Brain Abscess | 25 | 2 / 0 / 2 |
| 2.2 | Encephalitis syndrome | 26 | 1 / 0 / 1 |
| 2.3 | Meningitis syndrome | 27 | 1 / 0 / 1 |
| 2.4 | CSF shunt infections | 28, 29 | 2 / 0 / 2 |
| 2.5 | Healthcare Associated Ventriculitis | 30 | 1 / 0 / 1 |
| 3.1 | Acute Undifferentiated Febrile illness | 33, 34 | 2 / 1 / 1 |
| 3.2 | Enteric fever | 35 | 2 / 0 / 2 |
| 3.3 | Pyrexia of unknown origin (PUO) | 36 | 1 / 1 / 0 |
| 3.4 | Sepsis syndrome- Community acquired and Hospital acquired | 36, 37 | 4 / 1 / 3 |
| 4.1 | Oesophagitis | 39 | 1 / 0 / 1 |
| 4.2 | Acute Gastroenteritis | 40 | 3 / 3 / 0 |
| 4.3 | Hepatitis Syndrome | 40 | 1 / 0 / 1 |
| 4.4 | Infections of Liver, Gall Bladder and Biliary tract | 41, 42 | 4 / 2 / 2 |
| 4.5 | Appendicitis | 42 | 2 / 3 / 0 |
| 4.6 | Diverticulitis | 42 | 2 / 2 / 1 |
| 4.7 | Peritonitis – Primary / Secondary | 43 | 2 / 4 / 0 |
| 4.8 | Splenic Abscess | 43 | 2 / 1 / 1 |
| 4.9 | Pancreatitis | 44 | 2 / 2 / 0 |
| 5.1 | Cystitis | 46 | 1 / 1 / 0 |
| 5.2 | Pyelonephritis | 46 | 1 / 1 / 0 |
| 6.1 | Genital Ulcers | 47 | 1 / 0 / 1 |
| 6.2 | Anogenital Warts | 47 | 1 / 0 / 1 |
| 6.3 | Septic abortion | 48 | 2 / 1 / 1 |
| 6.4 | Vaginal Discharge Syndrome | 48 | 1 / 0 / 1 |
| 6.5 | Epididymo-Orchitis | 49 | 2 / 2 / 0 |
| 6.6 | Pelvic Inflammatory Disease syndrome | 49 | 1 / 0 / 1 |
| 6.7 | Prostatitis | 50 | 2 / 2 / 1 |
| 6.8 | Puerperal sepsis | 50 | 2 / 1 / 1 |
| 6.9 | Urethral discharge syndrome | 51 | 1 / 0 / 1 |
| 6.10 | Chorio-amnionitis | 51 | 2 / 1 / 1 |
| 7.1 | Rhinitis/ Common cold | 53 | 2 / 1 / 1 |
| 7.2 | Laryngitis/Laryngopharyngitis/URTI | 54, 55 | 5 / 3 / 2 |
| 7.3 | Sinusitis | 55, 56 | 3 / 3 / 2 |
| 7.4 | Otitis media | 56 | 2 / 1 / 1 |
| 7.5 | Otitis externa | 57 | 2 / 2 / 1 |
| 7.6 | Head and neck abscesses (peritonsillar/parapharyngeal and retropharyngeal abscess) | 57 | 2 / 2 / 0 |
| 8.1 | Oropharyngeal Candidiasis | 58 | 2 / 1 / 1 |
| 9.1 | Paronychia | 59 | 1 / 0 / 1 |
| 9.2 | Impetigo | 59 | 2 / 1 / 1 |
| 9.3 | Cellulitis | 59, 60, 61 | 6 / 2 / 5 |
| 9.4 | Necrotizing fasciitis | 61, 64 | 5 / 0 / 5 |
| 9.5 | Primary Pyomyositis | 62 | 1 / 0 / 1 |
| 9.6 | Folliculitis | 62, 63, 64 | 6 / 4 / 3 |
| 9.7 | Diabetic foot infections (DFI) | 65, 66 | 3 / 0 / 3 |
| 10.1 | Acute Osteomyelitis | 67 | 3 / 2 / 1 |
| 10.2 | Chronic Osteomyelitis | 68 | 1 / 1 / 0 |
| 10.3 | Gas gangrene | 68, 69 | 2 / 0 / 2 |
| 10.4 | Septic arthritis | 69 | 1 / 0 / 1 |
| 10.5 | Skin and soft tissue injuries | 70 | 2 / 0 / 2 |
| 10.6 | Orthopaedic implant associated infections | 71 | 1 / 0 / 1 |
| 10.7 | Surgical Prophylaxis | 72, 73, 74 | 19 / 15 / 4 |
| 11.1 | Conjunctivitis & Keratitis | 76, 77, 78, 79 | 11 / 3 / 8 |
| 11.2 | Endophthalmitis | 81, 82, 83, 84 | 4 / 0 / 4 |
| 11.3 | Periocular infections (Eyelid infections, Orbital cellulitis) | 85, 86 | 3 / 0 / 3 |
| 11.4 | Retinitis | 87 | 2 / 0 / 2 |
| 12.1 | Bronchitis | 88 | 1 / 1 / 0 |
| 12.2 | Bronchiolitis | 88 | 1 / 1 / 0 |
| 12.3 | Infective exacerbation of asthma/COPD | 88 | 1 / 3 / 0 |
| 12.4 | Infective Exacerbation of Bronchiectasis | 89 | 2 / 3 / 0 |
| 12.5 | Community Acquired Pneumonia | 90, 91 | 5 / 9 / 0 |
| 12.6 | Lung Abscess | 91 | 2 / 4 / 0 |
| 12.7 | Para-pneumonic pleural effusion/empyema | 92, 93 | 1 / 2 / 0 |
| 13.1 | Botulism | 94 | 1 / 0 / 1 |
| 13.2 | Diphtheria | 94, 95 | 1 / 0 / 1 |
| 13.3 | Tetanus | 95 | 1 / 0 / 1 |
| 13.4 | Toxic shock syndrome | 96 | 1 / 1 / 0 |
| 14.1 | Animal (Dog/cat/monkey/Human) | 97 | 5 / 3 / 2 |
| 14.2 | Insect Bites | 98 | 1 / 0 / 1 |
| 15.1 | Minor Burn Wounds | 99 | 1 / 0 / 1 |
| 15.2 | Major burn wounds | 99, 100 | 2 / 0 / 2 |
| 16.1 | Odontogenic tooth infections | 102 | 3 / 3 / 0 |
| 17.1 | Febrile neutropenia syndrome | 104 | 2 / 2 / 1 |
| 17.2 | Infections in Solid Organ Transplant recipients | 105 | 2 / 1 / 1 |
| 17.3 | Infections in Asplenia | 106 | 2 / 1 / 1 |
| 17.4 | Invasive Fungal Infections | 106, 107, 108, 109, 110, 111 | 13 / 1 / 12 |
| 18.1 | Fever in ICU | 113 | 1 / 0 / 1 |
| 18.2 | Invasive Candidiasis | 113 | 1 / 0 / 1 |
| 18.3 | Hospital-acquired pneumonia or Ventilator associated pneumonia | 114 | 2 / 2 / 1 |
| 18.4 | Central Line-Associated Bloodstream Infection (CLABSI) | 115, 116 | 2 / 0 / 2 |
| 18.5 | Antibiotic Associated Diarrhoea | 117 | 1 / 1 / 0 |
| 18.6 | Catheter associated urinary tract infection (CAUTI) | 118 | 2 / 2 / 1 |
| 18.7 | Intra-abdominal infection | 119 | 1 / 2 / 0 |
| 19.1 | Neonatal Infections | 120, 121, 122, 123, 124 | 8 / 0 / 8 |

Every context below has zero selectable treatment options. Read its source locator and gap before extending the catalogue.

- Infective Endocarditis — Uncomplicated - Native valve* (NCDC section 1.1; printed p. 14; PDF p. 21): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infective Endocarditis — Uncomplicated - Prosthetic valve* (NCDC section 1.1; printed p. 14; PDF p. 21): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infective Endocarditis — Complicated (In Severe Sepsis) (NCDC section 1.1; printed p. 14; PDF p. 21): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infective Endocarditis — Definitive therapy: Streptococci-Penicillin Susceptible; S. gallolyticus (MIC ≤0.12 μg/mL) — CVS-07 (JIPMER; printed p. 64; PDF p. 72): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: Streptococci-Relatively Penicillin Resistant (MIC >0.12 and <0.5 μg/mL) — CVS-08 (JIPMER; printed p. 64; PDF p. 72): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: Streptococci-Moderately Penicillin Resistant (MIC ≥0.5 and <8 μg/mL); Granulicatella, Abiotrophia or Gemella — CVS-09 (JIPMER; printed p. 64; PDF p. 72): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: Enterococci — CVS-10 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: MSSA infecting native valves (no foreign devices) — CVS-11 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: MRSA infecting native valves (no foreign devices) — CVS-11 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: MSSA infecting prosthetic valves — CVS-12 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: MRSA infecting prosthetic valves — CVS-12 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Infective Endocarditis — Definitive therapy: HACEK organisms — CVS-13 (JIPMER; printed p. 65; PDF p. 73): Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.
- Rheumatic fever — Uncomplicated (NCDC section 1.4; printed p. 17; PDF p. 24): Source primary cell places weight-dependent benzathine penicillin and penicillin V without an explicit connector; branch scope requires review.
- Brain Abscess — Uncomplicated (abscess <2.5cm & pa�ent neurologically stable) (NCDC section 2.1; printed p. 18; PDF p. 25): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Brain Abscess — Complicated (Pa�ent neurologically unstable) (NCDC section 2.1; printed p. 18; PDF p. 25): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Encephalitis syndrome — Complicated (encephalitis with meningeal signs and features of sepsis) (NCDC section 2.2; printed p. 19; PDF p. 26): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Meningitis syndrome — Acute Meningitis (NCDC section 2.3; printed p. 20; PDF p. 27): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- CSF shunt infections — CNS device infections in stable patients (NCDC section 2.4; printed p. 21, 22; PDF p. 28, 29): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- CSF shunt infections — In sick patients (NCDC section 2.4; printed p. 22; PDF p. 29): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Healthcare Associated Ventriculitis — Complicated (Meningitis-Post- neurosurgery or Penetrating head trauma or with basilar skull fractures) (NCDC section 2.5; printed p. 23; PDF p. 30): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Acute Undifferentiated Febrile illness — Fever beyond day 2 / source flowchart (NCDC section 3.1; printed p. 26, 27; PDF p. 33, 34): Source review required: management algorithm is a figure; do not substitute an unconditional dose.
- Enteric fever — Uncomplicated - Can be treated at OPDs (if without complications such as severe dehydration, weakness, abdominal haemorrhage, encephalitis) (NCDC section 3.2; printed p. 28; PDF p. 35): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Enteric fever — Complicated - persistent high fever or any of the complications mentioned above (NCDC section 3.2; printed p. 28; PDF p. 35): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Sepsis syndrome- Community acquired and Hospital acquired — Septic shock- community acquired infection without localization (NCDC section 3.4; printed p. 29; PDF p. 36): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Sepsis syndrome- Community acquired and Hospital acquired — Hospital acquired sepsis (organ / device specific infection is dealt under HAI) (NCDC section 3.4; printed p. 29; PDF p. 36): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. Page-break condition/combination continuation held for source review; no isolated continuation dose selected.
- Sepsis syndrome- Community acquired and Hospital acquired — Septic Shock - with localisation (NCDC section 3.4; printed p. 30; PDF p. 37): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Oesophagitis — O esophagitis (NCDC section 4.1; printed p. 32; PDF p. 39): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Hepatitis Syndrome — External guideline referral in NCDC (NCDC section 4.3; printed p. 33; PDF p. 40): NCDC refers to National Guidelines on Diagnosis and Management of Viral Hepatitis; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Infections of Liver, Gall Bladder and Biliary tract — Liver abscess with no predisposing hepato-biliary tract abnormality or immunocompromised condition (NCDC section 4.4; printed p. 34; PDF p. 41): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infections of Liver, Gall Bladder and Biliary tract — Cholecystitis & Cholangitis (with sepsis) (NCDC section 4.4; printed p. 34, 35; PDF p. 41, 42): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Diverticulitis — Diverticulitis without features of sepsis (NCDC section 4.6; printed p. 35; PDF p. 42): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Splenic Abscess — Splenic Abscess, stable hemodyamics (NCDC section 4.8; printed p. 36; PDF p. 43): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Genital Ulcers — External guideline referral in NCDC (NCDC section 6.1; printed p. 40; PDF p. 47): NCDC refers to NACO STI/RTI 2024, pp. 52–55; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Anogenital Warts — External guideline referral in NCDC (NCDC section 6.2; printed p. 40; PDF p. 47): NCDC refers to NACO STI/RTI 2024, pp. 91–92; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Septic abortion — Septic Abortion – Fever, Vaginal discharge, pelvic/abdominal pain, etc (NCDC section 6.3; printed p. 41; PDF p. 48): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Vaginal Discharge Syndrome — External guideline referral in NCDC (NCDC section 6.4; printed p. 41; PDF p. 48): NCDC refers to NACO STI/RTI 2024, pp. 41–43; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Pelvic Inflammatory Disease syndrome — External guideline referral in NCDC (NCDC section 6.6; printed p. 42; PDF p. 49): NCDC refers to NACO STI/RTI 2024, pp. 47–50; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Prostatitis — Acute Prostatitis (seen in young, sexually active with no structural urinary tract abnormality) (NCDC section 6.7; printed p. 43; PDF p. 50): Source dose unit is missing for ceftriaxone or penicillin V; no unit is inferred.
- Puerperal sepsis — Puerperal sepsis in Septic Shock (NCDC section 6.8; printed p. 43; PDF p. 50): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Urethral discharge syndrome — External guideline referral in NCDC (NCDC section 6.9; printed p. 44; PDF p. 51): NCDC refers to NACO STI/RTI 2024, pp. 34–38; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.
- Chorio-amnionitis — Chorio-amnionitis (NCDC section 6.10; printed p. 44; PDF p. 51): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Rhinitis/ Common cold — Influenza-like symptoms (lab confirmed or outbreak situation or in high-risk persons) (NCDC section 7.1; printed p. 46; PDF p. 53): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Laryngitis/Laryngopharyngitis/URTI — Complicated - persistence and non-improvement of symptoms & new onset fever, headache etc. (NCDC section 7.2; printed p. 47; PDF p. 54): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Laryngitis/Laryngopharyngitis/URTI — Membranous pharyngitis (NCDC section 7.2; printed p. 47, 48; PDF p. 54, 55): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Sinusitis — Patient-haemodynamically stable (NCDC section 7.3; printed p. 48, 49; PDF p. 55, 56): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Sinusitis — Suspicion of Fungal sinusitis (NCDC section 7.3; printed p. 49; PDF p. 56): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Otitis media — Severe: Temperature 39 0C or higher OR severe otalgia OR otalgia persisting for more than 48 hours or bulging tympanic membrane or complication like mastoiditis or abscess (NCDC section 7.4; printed p. 49; PDF p. 56): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Otitis externa — Patient presents with painful ear and pain and tenderness on moving the pinna, itching of ear canal, ear discharge (NCDC section 7.5; printed p. 50; PDF p. 57): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Oropharyngeal Candidiasis — Mild (NCDC section 8.1; printed p. 51; PDF p. 58): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Paronychia — Acute paronychia - Lasting less than six weeks, painful and purulent condition; most frequently caused by a bacterial infection, especially Staphylococcus spp. (NCDC section 9.1; printed p. 52; PDF p. 59): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Impetigo — Impetigo – extensive skin involvement, bullous disease and/or lymphadenopathy (NCDC section 9.2; printed p. 52; PDF p. 59): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Cellulitis — Cellulitis – non purulent (NCDC section 9.3; printed p. 53; PDF p. 60): Source dose unit is missing for ceftriaxone or penicillin V; no unit is inferred.
- Cellulitis — Cellulitis with MRSA risk factors: Mild Moderate to Severe (NCDC section 9.3; printed p. 53; PDF p. 60): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Cellulitis — Cellulitis in patients with comorbidities, poor response to oral antibiotics, immunocompromised, signs of deeper infection like bullae, skin sloughing or signs of systemic infection (NCDC section 9.3; printed p. 53; PDF p. 60): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. Page-break condition/combination continuation held for source review; no isolated continuation dose selected.
- Cellulitis — Cellulitis (suspected Vibrio vulnificus infection) — sea water laceration — SSI-08 (JIPMER; printed p. 51; PDF p. 59): Distinct pathogen/exposure context absent from the NCDC cellulitis primary rows. JIPMER severity-dependent alternatives and optional combination require source review; no fixed regimen selected.
- Cellulitis — Cellulitis (suspected Aeromonas infection) — fresh water laceration — SSI-09 (JIPMER; printed p. 51; PDF p. 59): Distinct pathogen/exposure context absent from the NCDC cellulitis primary rows. JIPMER severity-dependent alternatives and optional combination require source review; no fixed regimen selected.
- Necrotizing fasciitis — Necrotizing Fasciitis (NCDC section 9.4; printed p. 54; PDF p. 61): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Necrotizing fasciitis — Organism-specific necrotizing fasciitis: Type I — polymicrobial — SSI-13 (JIPMER; printed p. 56; PDF p. 64): JIPMER organism-specific context extends the generic NCDC syndrome row. Combination scope, route choices or Q8H/Q6H intervals are unresolved; source review required.
- Necrotizing fasciitis — Organism-specific necrotizing fasciitis: Type II — Group A Streptococcus — SSI-14 (JIPMER; printed p. 56; PDF p. 64): JIPMER organism-specific context extends the generic NCDC syndrome row. Combination scope, route choices or Q8H/Q6H intervals are unresolved; source review required.
- Necrotizing fasciitis — Organism-specific necrotizing fasciitis: Type III — Aeromonas hydrophila / fresh water — SSI-15 (JIPMER; printed p. 56; PDF p. 64): JIPMER organism-specific context extends the generic NCDC syndrome row. Combination scope, route choices or Q8H/Q6H intervals are unresolved; source review required.
- Necrotizing fasciitis — Organism-specific necrotizing fasciitis: Type III — Vibrio vulnificus / sea water — SSI-15 (JIPMER; printed p. 56; PDF p. 64): JIPMER organism-specific context extends the generic NCDC syndrome row. Combination scope, route choices or Q8H/Q6H intervals are unresolved; source review required.
- Primary Pyomyositis — Primary Pyomyositis (NCDC section 9.5; printed p. 55; PDF p. 62): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Folliculitis — Folliculitis – uncomplicated superficial (NCDC section 9.6; printed p. 55, 56; PDF p. 62, 63): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Folliculitis — Furuncle and carbuncle (NCDC section 9.6; printed p. 56; PDF p. 63): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Folliculitis — Demodex Folliculitis (NCDC section 9.6; printed p. 56; PDF p. 63): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Diabetic foot infections (DFI) — Mild: local infection with 0.5cm to < 2cm erythema (NCDC section 9.7; printed p. 58; PDF p. 65): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Diabetic foot infections (DFI) — Moderate: local infection with > 2cm erythema or involving deeper structures (such as abscess, osteomyelitis, septic arthritis or fasciitis) (NCDC section 9.7; printed p. 58; PDF p. 65): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Diabetic foot infections (DFI) — Severe: local infection with signs of a systemic inflammatory response. (NCDC section 9.7; printed p. 58, 59; PDF p. 65, 66): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Acute Osteomyelitis — Complicated osteomyelitis (diabetic foot infection or any other reason for diminished blood supply to the bones) (NCDC section 10.1; printed p. 60; PDF p. 67): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Gas gangrene — Traumatic gas gangrene: lethal infection of soft tissue and is synonymous with myonecrosis usually (NCDC section 10.3; printed p. 61; PDF p. 68): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. Traumatic/spontaneous source condition spans pages 68–69; exact branch attachment held for source review.
- Gas gangrene — Spontaneous gas gangrene — source row continues traumatic-gangrene text (NCDC section 10.3; printed p. 62; PDF p. 69): Traumatic/spontaneous source condition spans pages 68–69; exact branch attachment held for source review.
- Septic arthritis — Septic Arthritis (NCDC section 10.4; printed p. 62; PDF p. 69): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Skin and soft tissue injuries — Clean incised wounds/stroke cuts/sharp cuts involving only skin (NCDC section 10.5; printed p. 63; PDF p. 70): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Skin and soft tissue injuries — Contused lacerated wounds/Contaminated wounds (farmyard wounds roadside wounds) *Contamination from anaerobic organisms is a possibility (NCDC section 10.5; printed p. 63; PDF p. 70): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Orthopaedic implant associated infections — Orthopedic implant associated infections (NCDC section 10.6; printed p. 64; PDF p. 71): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Surgical Prophylaxis — Urology-Clean with entry into urinary tract — adult surgical prophylaxis (NCDC section 10.7; printed p. 67; PDF p. 74): Source adult dosage is missing or incomplete; conditional prophylaxis guidance requires source review. No dose is inferred.
- Surgical Prophylaxis — Urology-Clean without entry into urinary tract — adult surgical prophylaxis (NCDC section 10.7; printed p. 67; PDF p. 74): Source adult dosage is missing or incomplete; conditional prophylaxis guidance requires source review. No dose is inferred.
- Surgical Prophylaxis — Genitourinary Lower tract instrumentation with risk factors for infection (includes transrectal prostate biopsy] — adult surgical prophylaxis (NCDC section 10.7; printed p. 67; PDF p. 74): Source adult dosage is missing or incomplete; conditional prophylaxis guidance requires source review. No dose is inferred.
- Surgical Prophylaxis — Small Intestine- Non obstructed — adult surgical prophylaxis (NCDC section 10.7; printed p. 67; PDF p. 74): Ambiguous source dose: the additional 500 mg has no identified agent; source clarification is required.
- Conjunctivitis & Keratitis — Allergic (reaction is secondary to allergens such as pollen) (NCDC section 11.1; printed p. 69; PDF p. 76): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Bacterial Conjunctivitis: starts commonly with one eye then both eyes stick with mucopurulent discharge (NCDC section 11.1; printed p. 69, 70; PDF p. 76, 77): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Trachoma (NCDC section 11.1; printed p. 70, 71; PDF p. 77, 78): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Viral Conjunctivitis (commonly both eyes together with watery discharge) (NCDC section 11.1; printed p. 71; PDF p. 78): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Bacterial Keratitis (NCDC section 11.1; printed p. 71, 72; PDF p. 78, 79): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Viral Keratitis — Stromal (NCDC section 11.1; printed p. 72; PDF p. 79): Source mixes pediatric age/weight and adult acyclovir doses; select only after source review.
- Conjunctivitis & Keratitis — VZV (Varicella Zoster Ophthalmicus/Her pes zoster ophthalmicus) (NCDC section 11.1; printed p. 72; PDF p. 79): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Conjunctivitis & Keratitis — Fungal Keratitis: Aspergillus, Fusarium, Candida species (NCDC section 11.1; printed p. 72; PDF p. 79): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Endophthalmitis — Acute postoperative endophthalmitis (within 6 weeks of surgery) (NCDC section 11.2; printed p. 74, 75; PDF p. 81, 82): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Endophthalmitis — Chronic post-cataract surgery endophthalmitis (after 6-week of surgery) (NCDC section 11.2; printed p. 75; PDF p. 82): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Endophthalmitis — Endogenous/ Hematogenous (bacteraemia any source) (NCDC section 11.2; printed p. 75, 76; PDF p. 82, 83): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Endophthalmitis — Fungal Endophthalmitis (Usually endogenous) (NCDC section 11.2; printed p. 76, 77; PDF p. 83, 84): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Periocular infections (Eyelid infections, Orbital cellulitis) — Periorbital/preseptal cellulitis (NCDC section 11.3; printed p. 78; PDF p. 85): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Periocular infections (Eyelid infections, Orbital cellulitis) — Uncomplicated orbital cellulitis (NCDC section 11.3; printed p. 78, 79; PDF p. 85, 86): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Periocular infections (Eyelid infections, Orbital cellulitis) — Complicated (With intracranial extension) (NCDC section 11.3; printed p. 79; PDF p. 86): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Retinitis — CMV (NCDC section 11.4; printed p. 80; PDF p. 87): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Retinitis — Acute retinal necrosis (NCDC section 11.4; printed p. 80; PDF p. 87): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Botulism — Botulism (NCDC section 13.1; printed p. 87; PDF p. 94): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Diphtheria — Diphtheria (NCDC section 13.2; printed p. 87, 88; PDF p. 94, 95): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Tetanus — Tetanus (NCDC section 13.3; printed p. 88; PDF p. 95): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Animal (Dog/cat/monkey/Human) — Animal bite – breach in skin/open wound (NCDC section 14.1; printed p. 90; PDF p. 97): Primary treatment cell not supplied or not reliably extracted; source review required.
- Animal (Dog/cat/monkey/Human) — Monkey (NCDC section 14.1; printed p. 90; PDF p. 97): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Insect Bites — Insect bite with possible subsequent secondary infection (NCDC section 14.2; printed p. 91; PDF p. 98): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Minor Burn Wounds — First-degree burns (NCDC section 15.1; printed p. 92; PDF p. 99): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Major burn wounds — Second- degree burns (NCDC section 15.2; printed p. 92, 93; PDF p. 99, 100): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Major burn wounds — Third- degree burns: It can be life- threatening (NCDC section 15.2; printed p. 93; PDF p. 100): Primary treatment cell not supplied or not reliably extracted; source review required.
- Febrile neutropenia syndrome — Hemodynamically unstable (NCDC section 17.1; printed p. 97; PDF p. 104): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infections in Solid Organ Transplant recipients — Surgical site infection (NCDC section 17.2; printed p. 98; PDF p. 105): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Infections in Asplenia — Community acquired sepsis (NCDC section 17.3; printed p. 99; PDF p. 106): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Invasive Fungal Infections — Invasive Candidiasis (NCDC section 17.4; printed p. 99, 100; PDF p. 106, 107): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Invasive Fungal Infections — Invasive aspergillosis (NCDC section 17.4; printed p. 100; PDF p. 107): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Invasive Fungal Infections — BMT / HSCT setting — Community acquired pneumonia (CAP) (NCDC section 17.4; printed p. 103; PDF p. 110): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT / HSCT setting — Skin and soft tissue infection (NCDC section 17.4; printed p. 103, 104; PDF p. 110, 111): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT / HSCT setting — Herpes simplex (NCDC section 17.4; printed p. 104; PDF p. 111): BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT / HSCT setting — Varicella or disseminate d zoster or localized zoster (NCDC section 17.4; printed p. 104; PDF p. 111): BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT / HSCT setting — CMV reactivation or disease (colitis, pneumonitis , hepatitis, retinitis, encephalitis) (NCDC section 17.4; printed p. 104; PDF p. 111): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen. BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT / HSCT setting — Pneumocysti s jirovecii pneumonia (NCDC section 17.4; printed p. 104; PDF p. 111): BMT/HSCT-specific source context; population/timing matching requires review.
- Invasive Fungal Infections — BMT pre-engraftment and post-engraftment — antifungal prophylaxis (NCDC section 17.4; printed p. 101; PDF p. 108): Three-column BMT prophylaxis grid has transplant-specific timing/conditional branches. Source review required; no population or treatment dose inferred.
- Invasive Fungal Infections — BMT pre-engraftment and post-engraftment — antiviral prophylaxis (NCDC section 17.4; printed p. 101; PDF p. 108): Three-column BMT prophylaxis grid has transplant-specific timing/conditional branches. Source review required; no population or treatment dose inferred.
- Invasive Fungal Infections — BMT pre-engraftment and post-engraftment — CMV surveillance / pre-emptive treatment (NCDC section 17.4; printed p. 101, 102; PDF p. 108, 109): Three-column BMT prophylaxis grid has transplant-specific timing/conditional branches. Source review required; no population or treatment dose inferred.
- Invasive Fungal Infections — BMT / HSCT — Pneumocystis prophylaxis (NCDC section 17.4; printed p. 102; PDF p. 109): Three-column BMT prophylaxis grid has transplant-specific timing/conditional branches. Source review required; no population or treatment dose inferred.
- Fever in ICU — Fever in ICU can be due to infective or non-infective causes. Empiric therapy for HAI would depend upon the infectious syndrome, organism prevalent in the unit, local resistance pattern (NCDC section 18.1; printed p. 106; PDF p. 113): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Invasive Candidiasis — Invasive candidiasis (NCDC section 18.2; printed p. 106; PDF p. 113): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Hospital-acquired pneumonia or Ventilator associated pneumonia — VAP in patients with recent exposure to BL- BLI / Carbapenems (NCDC section 18.3; printed p. 107; PDF p. 114): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Central Line-Associated Bloodstream Infection (CLABSI) — CLABSI without previous antibiotic exposure and stable (NCDC section 18.4; printed p. 108, 109; PDF p. 115, 116): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Central Line-Associated Bloodstream Infection (CLABSI) — CLABSI with recent exposure to carbapenems or BL- BLIs exposure and / or unstable (NCDC section 18.4; printed p. 109; PDF p. 116): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Catheter associated urinary tract infection (CAUTI) — CAUTI- not severely ill (NCDC section 18.6; printed p. 111; PDF p. 118): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Possible serious bacterial infection, PSBI (community acquired) (NCDC section 19.1; printed p. 113; PDF p. 120): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Possible serious bacterial infection (possible hospital acquired/community with high AMR, e.g., >10% prevalence of ESBL), without meningitis (NCDC section 19.1; printed p. 113, 114; PDF p. 120, 121): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Meningitis (NCDC section 19.1; printed p. 114; PDF p. 121): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Conjunctivitis (NCDC section 19.1; printed p. 115; PDF p. 122): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Superficial infections (omphalitis, superficial abscesses) (NCDC section 19.1; printed p. 116; PDF p. 123): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Tetanus Neonatorum (NCDC section 19.1; printed p. 116; PDF p. 123): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Oro-cutaneous candidiasis (NCDC section 19.1; printed p. 116, 117; PDF p. 123, 124): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Neonatal Infections — Disseminated or CNS HSV infection (NCDC section 19.1; printed p. 117; PDF p. 124): Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.
- Subdural Empyema — Following sinusitis (JIPMER; printed p. 61; PDF p. 69): Source review required: metronidazole Q8H/6H and optional vancomycin are unresolved conditional choices. No fixed regimen selected.
- Epidural Abscess — Following sinusitis or otitis (JIPMER; printed p. 61; PDF p. 69): Source review required: metronidazole Q8H/6H and optional vancomycin are unresolved conditional choices. No fixed regimen selected.
- Cholera — Pathogen-specific watery / rice-water diarrhoea (JIPMER; printed p. 44; PDF p. 52): Duration scope of doxycycline/azithromycin versus ciprofloxacin is unresolved; source review required.
- Shigella gastroenteritis — Moderate or severe disease only (JIPMER; printed p. 44; PDF p. 52): Source-specific pathogen treatment choices and susceptibility conditions require review; no unconditional antibiotic selected.
- Non-typhoid Salmonella gastroenteritis — Severe/invasive disease or risk for invasion (JIPMER; printed p. 44; PDF p. 52): Treatment indications, AST-dependent alternatives, bacteraemia and duration branches require review.
- Campylobacter gastroenteritis — Severe illness or source-listed risk factors (JIPMER; printed p. 45; PDF p. 53): JIPMER supplies azithromycin 500mg PO OD x 1–3 days, but treatment is restricted to listed severity/risk conditions; source review required before selecting the branch.
- Enterotoxigenic / enteropathogenic / entero-invasive E. coli diarrhoea — Pathogen-specific or traveller’s diarrhoea (JIPMER; printed p. 45; PDF p. 53): Pathogen-specific choice and applicability require source review; EHEC must not inherit this guidance.
- Vibrio parahaemolyticus gastroenteritis — Severe illness; shellfish-associated (JIPMER; printed p. 45; PDF p. 53): Three source antibiotic alternatives require review; no unconditional treatment selected.
- Yersinia gastroenteritis — Immunocompromised host / bacteraemia / pseudo-appendicitis (JIPMER; printed p. 45; PDF p. 53): Source alternative branches differ for bacteraemia and AST; source review required.
- Intra-abdominal abscess — GIT-10 — source matching hold (JIPMER; printed p. 48; PDF p. 56): Source-match review required against NCDC appendicular/splenic abscess and secondary/tertiary peritonitis before determining a genuinely uncovered context. No JIPMER regimen displaces NCDC.
- Snake Bite Cellulitis — SSI-12 — snake bite cellulitis (JIPMER; printed p. 54; PDF p. 62): NCDC bite headings cover mammals and insects, not this named snake-bite context. JIPMER route and interval alternatives require source review; no fixed regimen selected.
- Arthritis-Acute polyarticular arthritis — BJI-02 — aetiology-dependent (JIPMER; printed p. 58; PDF p. 66): Source guidance depends on suspected aetiology; no broad empirical regimen inferred. Source mentions gonococcus and melioidosis separately.
- Chronic Monoarthritis — BJI-03 — tuberculosis / Brucella (JIPMER; printed p. 58; PDF p. 66): Pathogen-specific treatment is not supplied in this row; source review required.
- Vertebral Osteomyelitis +/- epidural abscess — BJI-06 — anatomical context (JIPMER; printed p. 58; PDF p. 66): Distinct vertebral context; source review required to confirm applicability and duration. Do not confuse spinal epidural extension with the cranial epidural abscess entry.

Rebuild: `python tools/build_infection_guidance.py --evidence-root /path/to/read-only/evidence`; verify determinism with `--check`. The builder only writes its owned JSON and this mapping file. All source material is opened read-only.
