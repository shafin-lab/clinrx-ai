# M10 TEG ROTEM device coverage and evidence matrix

Companion to [M10 Blood and blood products, coagulation and transfusion](2026-10-23-m10-transfusion-design.md). Evidence checked 23 October 2026. This catalogue defines design coverage; it is not an assertion that connectors, clinical protocols or all manufacturer IFUs have already been implemented and validated.

## Coverage model

Name the commonly used product families explicitly and support manual/imported original report capture across them. Verify structured mapping and clinical interpretation separately, at the level of device, assay, cartridge, region and software/export version. Retain additional source outputs even when they are unmapped. Product availability and licensed uses differ by region; a catalogue entry is not a claim of worldwide availability.

The table identifies core configurations and representative outputs verified in the linked primary sources. It is not a universal mask of all outputs on all machines. An exact current IFU and representative export are required for any operational adapter. Retain the source identity even when a hospital uses an alternative display name.

## Core device and assay profiles

| Device family | Required configuration profiles | Output/mapping requirements and boundaries | Primary evidence |
|---|---|---|---|
| TEG 5000 | Kaolin; kaolin with heparinase; RapidTEG; functional fibrinogen; PlateletMapping ADP & AA, ADP-only and AA-only | Separate reagent/sample profiles. Preserve source-reported kinetic, strength, lysis, fibrinogen and platelet-function measures; do not assume a cartridge architecture for this cup-and-pin device. Native/recalcified or other reported assays have separate profiles. | [Haemonetics TEG 5000](https://hospital.haemonetics.com/hemostasis-management/teg-5000) lists kaolin, heparinase cups/pins, RapidTEG, functional fibrinogen and the three PlateletMapping reagent configurations. |
| TEG 6s Global Hemostasis | Citrated K, KH, RT, FF; US catalogue example 07-601-US | CK: R/K/angle/MA; CKH: R; CRT: MA; CFF: MA/FLEV in the cited submission. No lysis output is supplied by that cited output mask. Region/software-specific additional observations need their own source verification. | [Haemonetics catalogue](https://hospital.haemonetics.com/hemostasis-management/teg-6s); [manufacturer FDA submission K243858](https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243858.pdf), especially reported-parameter table, PDF p11. |
| TEG 6s Global Hemostasis with Lysis | Citrated K, RT, FF; US catalogue example 07-605-US | CK R and CK LY30, CRT MA and CFF MA in the cited configuration; no CKH channel. A pending CK LY30 is not a normal result. | [Manufacturer FDA submission K183160](https://www.accessdata.fda.gov/cdrh_docs/pdf18/K183160.pdf), indications/assays, PDF pp7–9; [UW Medicine original laboratory catalogue](https://dlmp.uw.edu/test-guide/view/LTEG6S) verifies a real reporting set. |
| TEG 6s Global Hemostasis–HN | Citrated K, KH, RTH, FFH; US catalogue example 07-604-US | Preserve CK, CKH, CRTH and CFFH distinctly. The cited assessment set includes CK R/MA, CKH R/LY30, CRTH MA and CFFH MA. HN does not mean every assay is identical to its non-HN namesake or neutralises every anticoagulant. | [Manufacturer FDA submission K232018](https://www.accessdata.fda.gov/cdrh_docs/pdf23/K232018.pdf), assessment list, PDF p29. |
| TEG 6s PlateletMapping | ADP & AA and ADP-only; US catalogue examples 07-614-US and 07-615-US | Capture exact source channel/control results, agonist responses and reported inhibition/aggregation; verify output masks and specimen requirements from the regional IFU. Do not attach AA outputs to an ADP-only profile. | [Haemonetics TEG 6s catalogue](https://hospital.haemonetics.com/hemostasis-management/teg-6s); [K160502](https://www.accessdata.fda.gov/cdrh_docs/pdf16/K160502.pdf) identifies PlateletMapping assay cartridges as a TEG 6s disposable family but does not supply a full modern parameter mask. |
| ROTEM delta | INTEM, EXTEM, FIBTEM, APTEM, HEPTEM, NATEM; preserve liquid versus single-use S reagent configuration | Register timed amplitudes, kinetic/strength/lysis measures per assay. Capture optional/derived parameters without assigning them to assays where they are not reported. | [Manufacturer comparison in FDA K201440](https://www.accessdata.fda.gov/cdrh_docs/pdf20/k201440.pdf), predicate-device assays and outputs, PDF pp6–7; [manufacturer delta manual 2.8.0.03.EN, 2020, hosted by Vietnam Ministry of Health](https://imda.moh.gov.vn/documents/10182/57924129/upload_00053884_1725101751240.pdf?fileId=57939148&version=1.0), reagent naming/lines, printed p3-11. |
| ROTEM sigma Complete | INTEM C, EXTEM C, FIBTEM C, APTEM C; catalogue example 000555501 | The fourth assay is APTEM C. Keep sigma C identities separate from delta assays. Verify parameter masks against the exact regional IFU; do not infer all delta parameters are available. | [Werfen document library](https://www.werfen.com/at/de/document-library/42) verifies the catalogue item; [Australian TGA manufacturer correction record](https://apps.tga.gov.au/PROD/DRAC/arn-detail.aspx?k=RC-2025-RN-00811-1) documents the APTEM versus HEPTEM cartridge distinction. |
| ROTEM sigma Complete + HEP | INTEM C, EXTEM C, FIBTEM C, HEPTEM C; catalogue example 000555502 | The fourth assay is HEPTEM C. The US cited profile reports CT, A5/A10/A20, MCF, LI60 and ML with assay-specific applicability; not every parameter applies to FIBTEM C or HEPTEM C. | [Manufacturer FDA K201440](https://www.accessdata.fda.gov/cdrh_docs/pdf20/k201440.pdf), parameter and reportable-range tables, PDF pp6 and 17; [Werfen document library](https://www.werfen.com/at/de/document-library/42). |

Each catalogue row requires capture/display, structured mapping and interpretation acceptance evidence. At design delivery, the core configuration inventory is specified and the citations substantiate it; current per-site IFUs, full export mappings and clinical rule activation are implementation/deployment deliverables. Do not describe that distinction as dropping support for the named configurations.

The [required first interpretation release](2026-10-23-m10-transfusion-design.md#required-first-interpretation-release) defines which clinical settings and output levels must accompany those mappings. It is a finite delivery target, not a claim that all possible device × setting × population combinations receive treatment guidance.

## Extended and legacy results

Capture source-labelled TEG native/recalcified assays and extended source-derived values, and ROTEM NATEM variants, other specialist assays and ROTEM platelet aggregation reports. Unknown model/reagent/assay identities remain original evidence with an explicit mapping gap. Do not guess that a third-party analyser labelled thromboelastography is a Haemonetics TEG device, or route Quantra, ClotPro or Sonoclot through a TEG/ROTEM rule profile. Adding those families would require their own profile work.

For ROTEM platelet, keep agonist-specific ARATEM/ADPTEM/TRAPTEM and any source-reported aggregation outputs in a separate measurement domain. Record ECATEM or other specialist outputs only under the exact source identity; research-use or region-limited status remains visible. A manufacturer-hosted [2019 clinical review](https://www.werfen.com/de/sites/default/files/2024-04/ROTEM-Pocket-Booklet-KJA.pdf) describes these specialist families, but it is not a current IFU or primary performance-validation study. Its catalogue is a discovery aid, not sufficient evidence to enable interpretation. In particular, older statements describing an assay as under development must not become a claim of present commercial availability.

## Parameter preservation requirements

The software vocabulary is intentionally broader than any single result mask. Capture each reported value with its assay/channel, original parameter name, exact unit, qualifier, quality, observation/run time, time origin, finality and source version. Values not produced on that cartridge are different from measurements still pending.

The fields accommodate:

- TEG kinetic and strength measurements; source-reported early amplitudes; assay-specific ACT; source-derived G/CI or other values; time-defined lysis metrics; functional-fibrinogen outputs and PlateletMapping responses.
- ROTEM kinetics, timed amplitudes, clot firmness and time-defined lysis/lysis-onset measures; source-derived elasticity/velocity outputs where actually reported; separate platelet-aggregation measurements.
- Original report text, imported numeric result stream and actual tracing/file references. Additional unmapped results remain visible without executable rules.

No software conversion equates TEG LY30 to ROTEM LI30, an early amplitude to maximum strength, TEG FLEV to Clauss fibrinogen, or PlateletMapping inhibition to platelet count. Exact assay documentation determines units and timing. Do not recompute proprietary instrument-derived values from an image or a handful of final numbers.

## Clinical interpretation evidence

| Source | What it supports | Design consequence |
|---|---|---|
| [British Society for Haematology guideline, 2018, The use of viscoelastic haemostatic assays in the management of major bleeding](https://onlinelibrary.wiley.com/doi/full/10.1111/bjh.15524) | Setting-specific use, clinically interpreted patterns and the need to validate algorithms locally; differing obstetric, liver, cardiac and trauma contexts. It is dated guidance, not proof of the latest recommendation for every condition. | Keep the pattern explanation separate from treatment triggers. Profiles specify setting and evidence. In liver disease, do not make an INR flag alone an automatic replacement decision; in bleeding, distinguish fibrin contribution from overall clot strength. A normal/pending lysis result cannot universally veto an independently indicated intervention. |
| [National Blood Authority adult critical-bleeding guideline landing page](https://www.blood.gov.au/patient-blood-management-guideline-adults-critical-bleeding) and [September 2025 guideline PDF](https://www.blood.gov.au/sites/default/files/documents/2025-09/Document%201%20-%20published_guideline_8641-2_0.pdf) | Adult critical bleeding, a major-haemorrhage-protocol framework, laboratory/physiological monitoring and consideration of viscoelastic evidence. Landing page confirms the 2025 GPS5 amendment and that the guideline is under review. | Include Hb, platelet count, PT/INR, APTT, fibrinogen, ionised calcium, temperature and acid-base context. Keep adult scope and evidence certainty with a protocol. VHA-based options belong within the relevant haemorrhage pathway; there is no implied universal numeric rule or direct PCC/plasma equivalence. |
| [Manufacturer TEG 6s K243858](https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243858.pdf), [K183160](https://www.accessdata.fda.gov/cdrh_docs/pdf18/K183160.pdf), [K232018](https://www.accessdata.fda.gov/cdrh_docs/pdf23/K232018.pdf) | Technical meaning and intended use of the named assays and their differing output sets. | Route evidence through exact assay profiles and preserve comparator/heparinase relationships. These submissions are not clinical dosing protocols or authorisation of ClinRx. |

No numerical treatment thresholds or doses are activated by this design document. The protocol contract in the main design requires the precise source section, population, assay, units, trigger, exclusions, calculation and clinical reviewer before such a rule becomes active. This is a complete specification of that boundary, not a claim that unverified thresholds provide clinical guidance.

## Blood products and traceability

- [Lifeblood red-cell information, updated March 2026](https://www.lifeblood.com.au/health-professionals/products/blood-components/red-cells) distinguishes leucodepleted red cells and modifications including washing and irradiation. It supports recording independent attributes; Australian supply practice is not a default for other hospitals.
- [ICCBBA FAQ](https://iccbba.org/faq/) explains the product/division structure for blood products and aliquots. Use the donation identifier with product/division identity, preserving the original barcode and local issuer. Do not claim an ISBT 128 decoder is certified or supplied with licensed terminology merely because the design includes its fields.
- [Canadian Blood Services uniform-labelling guidance](https://professionaleducation.blood.ca/en/transfusion/best-practices/uniform-labelling) explains original donation identifiers and process-control flag characters. Retaining raw and parsed representations prevents source identity from being lost during normalisation.

RDP/SDP shorthand, platelet pool size, cryoprecipitate pool composition, component volume and concentrate potency require explicit source data. A hospital's labels map to the catalogue without converting unlike quantities into a universal bag or adult dose.

## Version and source-quality safeguards

Two historical primary records illustrate why M10 retains software, IFU and cartridge identity:

- [FDA 2022 TEG 5000/TEG Manager PlateletMapping correction](https://www.accessdata.fda.gov/scripts/cdrh/cfRes/res.cfm?id=194215) concerned incorrect displayed inhibition/aggregation and a software update; the record is terminated. An import must retain whether the value came from the analyser or middleware and its software version.
- [TGA 2025 ROTEM sigma cartridge-label correction](https://apps.tga.gov.au/PROD/DRAC/arn-detail.aspx?k=RC-2025-RN-00811-1) concerned a Complete versus Complete + HEP label discrepancy; the record states closure in June 2026. Capture conflicting assay/cartridge assertions and hold dependent interpretation until reconciled. This is not a statement of an ongoing recall.

The manufacturer also directly documents the two sigma cartridge families and the need to adapt application-specific algorithms to local circumstances: [Werfen ROTEM sigma](https://www.werfen.com/de/de/rotem-sigma-ivdr). Use this as catalogue/context evidence; it is not a complete parameter specification or a dose protocol.

Do not turn this evidence list into an automatic recall-monitoring service. Future status checks need a defined source and separate current evidence. No public manufacturer catalogue establishes the patient's specimen quality, a local reference interval or the validity of a particular imported result.

## Evidence acquisition limits

Public manufacturer catalogues and regulator-hosted technical submissions were read for the core inventory. Full regional IFUs/exports are not uniformly public; the Werfen library gates some downloads. The government-hosted delta manual's indexed excerpt supplied reagent naming, while direct full-PDF retrieval timed out; the exact local liquid/S output mask still requires its current IFU. Primary hospital laboratory reporting demonstrates a real local output set, not a worldwide default. No prevalence survey was performed, so `commonly used` names the main families requested for design coverage rather than a quantified market-share ranking.

The deliverable preserves these limits in the profile verification states. At no point should a hospital-specific missing document be resolved by inventing a parameter, assuming all cartridges have the same capability or applying a different assay's clinical trigger.
