# M10 Blood and blood products, coagulation and transfusion

Design for ClinRx AI. Written 23 October 2026. Status: complete design proposal for review; product implementation is a separate step. The user requested coverage across hospitals, including commonly used TEG and ROTEM machines and cartridges. M10 is the current number; older documents calling this M11 are historical.

## 1. Clinical purpose and intended experience

A physician, surgeon, anaesthetist or other treating doctor must be able to answer five questions without reconstructing the record from separate charts:

1. What blood components and haemostatic products did this patient actually receive?
2. How many units, pools, bags or vials, what dose, and what volume were administered, and when?
3. What did the blood count, coagulation tests, calcium and viscoelastic tests show at that point?
4. What do those findings suggest, which product options does the selected clinical protocol support, and what information is missing?
5. What was given after that assessment, and what subsequent evidence is available?

Use expanded product names and short explanations alongside abbreviations. The default summary should be understandable to a doctor without specialist transfusion training. Exact tests, cartridges, source reports and traceability details remain readily accessible. Unknown processing, quantity or clinical context is shown as unknown; it does not become a negative finding or a zero.

The design includes interpretation and product decision support. It does not reduce M10 to a passive ledger. It separates recorded facts, software interpretation, a clinician's decision, a prescription, blood-bank issue and administration so each remains intelligible and auditable.

### Approaches and design decision

| Approach | Benefit | Cost or limitation |
|---|---|---|
| Add blood totals and a generic TEG/ROTEM form to the overview | Smallest initial change | Cannot safely represent product identity, cartridge differences, repeated administrations, partial bags or interpretation history |
| Separate transfusion application | Independent delivery | Fragments the shared patient, laboratory, medication and fluid records and increases reconciliation work |
| Connected M10 workspace with typed transfusion records and versioned assay/protocol registries | Preserves source ownership and supports clear summaries plus specialist interpretation across hospitals | Requires explicit contracts, accounting rules and profile verification |

Use the connected approach. This is the author's architecture decision, consistent with the existing ClinRx workspace and the user's request for the complete cross-hospital design. Broad evidence capture is available independently of whether a particular interpretation profile is enabled. No further choice of the user's own hospital or machine is needed to define the design.

Within this approach, use a shared clinical concept catalogue with separate device/cartridge profiles. A universal converted TEG/ROTEM panel would obscure assay differences; independent applications per manufacturer would fragment the patient workflow. Preserve original values and permit comparison or interpretation only through an explicit verified mapping.

## 2. Coverage and completion criteria

The complete module covers product and modification records; pre-transfusion testing and blood-bank assertions; requests and prescriptions; issue and disposition; administration and quantities; reactions and haemorrhage episodes; laboratory evidence; complete reported TEG/ROTEM results; transparent interpretation and protocol-linked product options; reassessment; shared overview, fluid and handover integration.

Adult, obstetric, paediatric and neonatal records are representable. Interpretation and dose rules require a matching population and setting profile. Adult settings never become a fallback for children, neonates, pregnancy or an unknown population. The profile catalogue must be able to represent trauma, cardiac surgery, liver disease/transplantation, obstetric haemorrhage, general surgery and medical/ICU bleeding separately.

M10 is functionally complete when a synthetic patient can be followed from existing evidence, through a documented clinical decision, to a separately entered product administration and subsequent assessment, using each supported device family; corrections and historical views must reproduce the evidence available at the chosen cutoff. Clinical deployment additionally requires verified site integrations, approved intended use and clinical validation. Software tests alone do not establish those conditions.

This design does not include automatic device control, donor recruitment, blood-bank stock allocation or release, hospital order transmission, autonomous prescribing, or a claim that every hospital interface is already connected. Record a blood-bank compatibility conclusion; do not recreate the blood bank's compatibility workflow from ABO/RhD alone.

## 3. Product catalogue and traceability

### Required families

| Family | Required distinctions | Quantity dimensions retained |
|---|---|---|
| Packed red blood cells (PRBC/RBC) | Exact label; allogeneic/autologous; modification assertions | Component bags/units, measured amount administered in mL, documented partial fraction if supplied |
| Plasma | FFP, thawed plasma and other exact preparations; solvent-detergent or other processing where documented | Bags/units and actual mL; preparation-specific totals |
| Platelets | Whole-blood-derived/random donor platelets (RDP); pooled platelets; single donor/apheresis platelets (SDP); splits/aliquots | Individual components, pools or apheresis units; pool composition; actual mL; documented platelet content if supplied |
| Cryoprecipitate | Single components, pools and apheresis-derived preparations where used | Units and pools, explicit units per pool when known, actual mL and labelled fibrinogen content when supplied |
| Prothrombin complex concentrate (PCC) | Exact product; three-factor/four-factor/activated/unknown as explicitly identified | Administered IU with labelled factor basis, vials, vial strength and actual reconstituted volume if known |
| Human fibrinogen concentrate | Exact product, vial strength and batch | Administered grams, vials and actual mL if known |
| Other haemostatic products | Exact factor concentrates, antifibrinolytics, protamine, calcium and other recorded adjuncts | Original medication dose and unit, route, preparation, time and batch as relevant |
| Additional blood exposures | Whole blood, cell-salvaged/autologous blood, exchange procedures and other source-labelled components | Separate product/procedure identities and actual delivered quantities; no conversion into PRBC units |

Albumin, immunoglobulin and other plasma-derived medicines can appear as linked medication exposures. They do not enter coagulation-replacement totals or inherit a transfusion recommendation merely because they are plasma-derived.

### Product attributes

Represent processing as independent assertions: leukodepleted/leukoreduced, irradiated, washed, CMV-seronegative, pathogen-reduced, antigen-selected, phenotype/genotype-matched, HLA/HPA-selected, volume-reduced, frozen/deglycerolised, and other original label text. Each assertion has value `yes`, `no`, `unknown` or `not_applicable`, its source and verification status. A label can assert both leukodepletion and irradiation. Do not infer either from product family, country or an institution's usual practice. Source facts about red-cell modifications are documented in the [evidence companion](2026-10-23-m10-device-and-evidence-matrix.md#blood-products-and-traceability).

Keep the patient's special product requirements separate from the actual component's attributes. A comparison can identify a recorded mismatch or missing confirmation; it cannot certify the component as safe to administer. Patient ABO/RhD, donor ABO/RhD, antibody screen/identification, compatibility result, specimen validity, emergency-release status and blood-bank authorisation remain separately sourced assertions with times and status. Expiry rules are site policy, not a universal hard-coded interval.

### Identity

Retain hospital/issuer, original product code and description, donation identification number where present, full product/division code, aliquot/split identity, pool identifier and constituent links when available, collection/expiry times, supplier, lot/batch and local blood-bank component identifier. Preserve raw barcode text and parser version separately from parsed fields. An ISBT 128 donation number alone does not distinguish all components and splits from that donation; see the [ICCBBA references](2026-10-23-m10-device-and-evidence-matrix.md#blood-products-and-traceability).

Missing component identifiers must not prevent historical aggregate entry. Such an entry is explicitly an aggregate assertion with limited traceability; it is not silently expanded into invented individual units. Manual duplicate warnings do not replace source identity checks. No patient/donor identifiers are sent to external web services for product or interpretation lookup.

## 4. Transfusion lifecycle and data grain

Do not use a single changing status field to stand for the entire lifecycle. Store separate source facts, linked where the source establishes a relationship:

| Record | What it asserts |
|---|---|
| `TransfusionRequest` | A request/clinical intention, indication, priority, desired product and quantity, requested modifications and linked evidence |
| `TransfusionPrescription` | A documented prescription and its author, intended product, dose/rate, timing and source identifier; no administration implied |
| `BloodProductDisposition` | Blood-bank allocation/issue/return/wastage/release assertions for identified products or a documented aggregate |
| `TransfusionAdministration` | Actual administration episode or explicitly reported historical aggregate, including delivered quantities and clinical times |
| `TransfusionReaction` | Symptoms, observation times, implicated administrations, interruption, investigation and source-reported classification/outcome |
| `HaemorrhageEpisode` | Clinician/source-reported bleeding context, location, procedure phase, estimated blood loss and major-haemorrhage-protocol activation/deactivation assertions |
| `M10Assessment` | Clinician findings, interpretation reviewed, decisions, rationale, evidence pins and reassessment plan |

All source facts use append-only revision histories. A later source correction supersedes the corresponding fact; it does not replace a different clinical event. For a continuing administration, chronological updates to its cumulative delivered amount belong to the same administration chain; distinct additional bags or administration episodes have distinct identities. A stop/restart remains one episode only when the source supplies that identity; otherwise preserve the separate episodes and exact product links.

### Administration fields

Require patient/encounter binding, record origin, source identity/version, administration identity and grain (`component_episode` or `reported_aggregate`), product identity or exact source product description, activity status, explicitly recorded quantities or their missing reasons, clinical times or their missing status, and provenance. Product details can be incomplete without manufacturing data.

Activity status: `in_progress`, `completed`, `stopped`, `not_given`, `unknown`. Outcome and reasons are separate. Preserve requested, issued, intended and delivered quantities as different assertions. `not_given` has no positive delivered amount. `completed` may retain unknown volume; completion does not supply the label volume. For `stopped`, record delivered amount if known, reason and reaction links. Source contradictions are preserved as conflicts and excluded from affected calculations.

Retain start, pause/resume observations when available, completion/stop, source reported/available, local recorded/ingested times, route/access, administered by/documented by, indication and source record identifiers. A selected request/order link is optional for emergency or retrospective records; missing orders remain visible. Collect bedside checks/consent/authorisations as documented assertions without presenting a local preview as a clinical sign-off system.

### Medication ownership

PCC, fibrinogen concentrate, calcium and other haemostatic medicines remain medication administrations/orders. The existing `MedicationAdministration` contract represents a completed delivery with a positive known total and an exact administration time. Reuse it for source records that satisfy that meaning; attach a typed `M10MedicationDetail` pinned to its exact revision for product/batch/vial/dose-basis details. Do not weaken that existing contract or create an antimicrobial record for a non-antibiotic.

Add `HaemostaticMedicationCourse`, a typed `RecordedFactV2` source owner, for in-progress, stopped, not-given, uncertain-time or unknown-total concentrate/adjunct records that cannot truthfully fit the completed-delivery contract. It uses the administration status, exact quantities/missing reasons and clinical-time semantics above. Its delivery identity is stable across updates. If completion later produces a valid generic medication administration, admit that fact and the course successor linking `completed_as` atomically. The linked course becomes historical/context evidence for that delivery, not an additional dose. When a source still lacks a required generic-contract field at completion, the course remains the canonical medication exposure with the limitation visible. Existing generic administrations are not migrated into new courses.

One canonical medication delivery contributes to the shared medication chart and the M10 exposure summary. Add a shared medication-exposure read projection accepting these two owners; do not copy the new course into a transfusion administration or antibiotic record. Ambiguous cross-owner identity is reconciled explicitly before a combined dose total is certified. Orders, non-delivery and administrations remain distinct. Medicine concentration, prescribed dose, delivered dose, vial count and actual volume are separate quantities.

## 5. Counting and fluid accounting

### Summary rules

- Show completed products, in-progress delivery, stopped administrations and not-given products separately. Display known administered portions of stopped episodes in the received total.
- Group counts by exact clinically meaningful product family/preparation and count basis. Show RDP components, platelet pools and SDP units separately; likewise cryoprecipitate units and pools. Do not impose an RDP-to-SDP or pool-to-unit conversion across hospitals.
- Maintain bag/component exposure count independently from amount. A bag touched is not necessarily one full unit delivered. Display, for example, `1 component started; delivered volume unknown`, rather than `1 full unit given`.
- Sum compatible, non-overlapping cumulative administration chains once at the selected revision. Resumed segments and prior cumulative updates are not additional full doses.
- Known labelled pool composition permits a secondary derived constituent count with its evidence. It does not imply a measured dose or donor count. Count missing composition separately.
- PCC remains IU with its exact factor basis; fibrinogen concentrate remains grams. Do not convert either into FFP or cryoprecipitate units. Preserve source-reported replacement rationale as a clinician assertion, never infer clinical equivalence.
- Compute actual mL only from source-recorded administered volume or an explicitly supported calculation with known actual concentration/reconstitution inputs. Never assume a standard bag volume, full vial administration or labelled constituent content as actual delivered dose.
- For incomplete records, display a known subtotal and the number/type of records with missing amount, uncertain time or unresolved duplication. No available record is different from a documented zero exposure.

### Aggregate and constituent reconciliation

`TransfusionCoverageLink` is a separate append-only assertion usable across imported and manually entered records. It pins exact aggregate and constituent revisions, patient/encounter, covered period and product/count/dose basis, author/source, relationship, and any explicitly known residual. A matching amount or a close timestamp alone cannot create the relationship. The server validates that a constituent is not allocated twice within the same accounting selection and that the relationship graph has no cycles; descendants of an already-counted covering record cannot also contribute.

Relationships are `included_in_aggregate`, `fully_explained_by_constituents`, `same_delivery`, or `possible_overlap`. An aggregate stays as original evidence when linked; it is never edited to invent bag-level records. `fully_explained_by_constituents` selects constituent detail as the accounting representation only when their compatible quantities agree and coverage is explicitly complete. Partial `included_in_aggregate` coverage leaves the aggregate as the counting representation and displays known constituent detail within it; the residual count/dose can be shown only if it follows exactly from the same explicitly established coverage and count basis. A new correction invalidates dependent reconciliation until reviewed.

Example using fictional records: a confirmed aggregate of four PRBC units with two bag records explicitly included in it still totals four, with two units not individually identified. If four complete constituent records later account for it exactly, the total remains four and the traceability improves. If the two bags merely may overlap that aggregate, show `4 units reported in aggregate; 2 additional records with unresolved overlap`, not six confirmed units. The combined amount is indeterminate; a separate confirmed non-overlapping subtotal is permitted. Different product bases, approximate coverage or contradictory quantities never permit subtraction to manufacture a residual. Periods/amounts that are explicitly outside the aggregate's coverage can be counted separately.

### Review periods

Offer a selected interval, calendar day in the displayed hospital timezone, haemorrhage/procedure episode and current admission. Cross-encounter/lifetime summaries require explicit authorised patient linkage and complete retrieval; they are not implicit in the initial preview.

Use `[start, end)` boundaries for events so adjacent periods do not double-count. Preserve source offsets and precision. For an infusion spanning the window, use timestamped delivered increments if present. If only a final cumulative amount is known, show it as a spanning exposure with unallocated interval volume; do not prorate by time. A separate `episodes completed in period` view may report the full source amount but must use that label, not imply amount delivered within the period. Approximate/day-only times are shown as uncertain and are not forced into exact before/after relationships.

### Reconciliation with M8 fluid balance

M10 owns the transfusion administration; the existing fluid owner owns fluid accounting. Link them through an exact `FluidAdministrationLink` assertion (`same_delivery`, `included_in_aggregate`, `unresolved`) with author/source and revisions. Existing `input_blood` facts remain unchanged. A link is not a second fluid entry.

In a combined volume view, prefer the explicitly selected canonical accounting entry for that delivery, suppress its linked mirror and disclose both sources. The choice must agree with amounts or retain the discrepancy; it must not hide a disagreement. A reported fluid total containing several products cannot be added to its known constituents. Unresolved overlaps show separate subtotals and an incomplete combined total. New clinical products never generate guessed fluid volumes. Future automatic projection must use the same administration identity and a transactionally enforced unique delivery link.

## 6. Laboratory and calcium evidence

Reuse exact existing `LaboratoryReport` components and earlier observations; extend the explicit mapping catalogue rather than cloning their values into M10. Provide Hb, haematocrit, platelet count, PT in seconds with laboratory control/reference where supplied, INR, APTT in seconds/ratio as reported, and fibrinogen with assay/method. Keep Clauss fibrinogen, derived fibrinogen and viscoelastic estimated functional fibrinogen distinct.

Show ionised calcium and total calcium as different tests. Retain pH-corrected versus measured ionised calcium and the original method/reference information. Link M9 blood-gas ionised calcium, pH, lactate and base excess when present; do not create another measurement. If the same assay also arrives through the LIS, an explicit source-reconciliation link is required before collapsing it. Add core temperature and relevant potassium/acid-base evidence as contextual observations, not new M10-owned measurements.

Every result shows sample collection time, available/reported time, units, reference interval/source flags, status and correction history. No lab is described as contemporaneous just because it is the newest result. Display its age and intervening documented products. A protocol defines permissible evidence age and timing per input; there is no universal freshness duration in this design. No automatic albumin correction of calcium or substitution of total calcium for ionised calcium is specified.

The [National Blood Authority source](2026-10-23-m10-device-and-evidence-matrix.md#clinical-interpretation-evidence) supports the critical-bleeding monitoring set; its adult scope does not supply paediatric limits or authorise one threshold set for all contexts.

## 7. TEG and ROTEM coverage

The [device and evidence matrix](2026-10-23-m10-device-and-evidence-matrix.md) is part of this design. Named core families are TEG 5000 and TEG 6s, and ROTEM delta and ROTEM sigma. Include TEG 5000 kaolin/heparinase, RapidTEG, functional fibrinogen and PlateletMapping; TEG 6s Global Hemostasis, Global Hemostasis with Lysis, Global Hemostasis–HN, and ADP/AA PlateletMapping configurations; ROTEM delta core assays and both sigma Complete configurations. Also preserve native/specialist assays and ROTEM platelet results when reported, with their own verification state. Do not describe every experimental or legacy assay as commonly used or clinically enabled.

`Support` has three independently visible dimensions: capture/display, verified structured mapping, and protocol interpretation. A named profile is required in the catalogue even while a site-specific IFU/export mapping is being verified. The final product must not advertise a broad device as fully interpreted when only its generic report capture works.

### Viscoelastic report contract

`ViscoelasticReport` extends the source-preserving recorded-fact model, with:

- Source institution/issuer, report/accession identity, exact source revision and run identity; specimen identity, sample type, anticoagulant, collection site and line-draw/contamination comments as reported.
- Manufacturer, device family/model/serial identifier if available, instrument software and middleware/export software versions, cartridge/reagent name and catalogue identifier, reagent form/lot/expiry where supplied, jurisdiction and profile identifiers/versions.
- Source collection, receipt, run start, each result's observation/available time, report availability and completion times; machine run time and time-origin definitions. Store missing values explicitly.
- An ordered set of channel observations identified by exact assay/reagent, channel and parameter. A test can legitimately contain repeated parameter observations during a run; each has a unique source observation ID and elapsed time/status. Do not reject all repetition or flatten early values into a final result.
- For every observation: raw name/code, explicit mapped identity or unmapped status, typed original result (numeric with comparator, qualitative, narrative or unavailable), original units, reporting limit, laboratory reference/flags, quality and preliminary/final/not-yet-measurable/aborted status. No zero-fill for pending lysis or clot-not-formed values.
- Original report text and checksum; original trace/file attachments by immutable hash, media type, size and access-controlled local reference. Only render actual waveform points when available; never reconstruct a clinical trace from R/MA or CT/MCF alone. Scanned-image extraction is an unverified draft until checked against the source.
- External evidence pins for related laboratory, anticoagulant and product records, plus source-reported interpretation as distinct text. Manual transcription, import and machine-reported results remain distinguishable.

Set initial contract bounds to 32 channels, 512 observations per revision, 64 KiB report text and 32 external evidence pins. Larger reports/waveforms use immutable referenced attachments and paginated run observations; no silent truncation. These are design limits to prove against repository and transport budgets before implementation. Reject an over-budget write before committing any of its records.

### Report progression and correction semantics

Persist every `ViscoelasticReport` revision as a complete resolved snapshot for one source report/run. It includes the current observation set and invalidation/removal markers, with exact source-message provenance. Historical interpretation selects a snapshot, not a loose combination of whichever values are newest across reports. Retain raw source report version separately from the internal snapshot revision and from each source update/message identity; repeated source report labels do not permit conflicting bytes under one message identity.

Adapters must declare `authoritative_snapshot` or `explicit_patch` in their verified mapping. Manual entry and a complete replacement report use `authoritative_snapshot`: the supplied set is complete as reported, and previously present observations omitted from it are marked no longer reported in the new snapshot; they are not automatically carried forward. An explicit patch identifies its exact base snapshot reference/digest and update/message ID and contains bounded `upsert`/`invalidate`/`remove` operations on stable observation keys. It is applied atomically to produce a new complete snapshot, retaining unchanged observations and raw patch bytes with assembler version. No implied base, partial commit or heuristic carry-forward is allowed. Out-of-order updates require exact replay/reconciliation; a stale patch cannot overwrite a later snapshot.

Observation keys use the verified source item identifier where supplied. Otherwise the profile must define a deterministic key from run, assay/channel, parameter and measurement time/elapsed point; ambiguous identities are preserved but excluded from dependent interpretation. Updating a result replaces that observation's state in the resolved snapshot and preserves its earlier value in history. A distinct timed observation is a new key. Invalidate/remove records retain source reason or an explicit reason-not-reported state. The evaluator chooses only the observation required by a rule, with the correct timing/finality; it cannot use a removed value or treat an early estimate as a completed measurement.

Thus an explicit `A10 now available` patch retains earlier CT/A5, while a corrected report that retracts a prior result removes that result from current interpretation. An adapter unable to distinguish snapshots from patches can preserve source messages for review but cannot assemble an interpretable report. Source availability and local ingestion of both base and update bound the resulting snapshot's historical eligibility.

### Parameter dictionary

The dictionary accommodates R, K, alpha angle, MA, early amplitudes, ACT where assay-specific, G/CI and other source-derived TEG metrics, LY30/LY60 and source-specific lysis metrics, functional-fibrinogen MA/FLEV, and PlateletMapping channel MAs and ADP/AA responses. ROTEM accommodates CT, CFT, alpha angle, A5/A10/A20 and other timed amplitudes, MCF, LI30/LI60 and other time-defined indices, ML, LOT and source-derived elasticity/velocity measures. ROTEM platelet aggregation metrics occupy a separate assay/measurement domain.

This is a capture vocabulary, not a declaration that every model outputs all parameters. Each profile enumerates allowed channels, parameters, units, timing origin, result status and interpretive use. Newly encountered outputs remain visible with their raw names; they do not gain rules from a similar label. `not_on_cartridge`, `not_reported`, `pending`, `not_measurable`, `invalid` and `unknown` remain distinct.

### Registry identity

Key profiles by manufacturer + model + market/jurisdiction + reagent/cartridge identifier/revision + supported instrument/middleware software + sample preparation. Include IFU/reference version, permitted specimen, assay output mask, analytic limits, heparin-neutralisation claims/limits when verified, reference-interval provenance and linked interpretation profiles. Country availability and device clearance are metadata; neither is an approval of ClinRx.

Do not merge CKH with CRTH, CFF with CFFH, sigma C assays with delta S/liquid assays, PlateletMapping with routine MA, or TEG with ROTEM. Assay display aliases can be hospital-specific; canonical mappings require explicit verification. Profiles have `draft`, `mapping_verified`, `interpretation_verified`, `retired` states and effective dates. Updating a profile creates a version; historical assessments keep their prior version.

## 8. Interpretation and product decision support

### Three outputs

1. **Observed finding:** exact measured result, source range/flag and whether the required observation is usable.
2. **Explained pattern:** a plain-language interpretation such as reduced fibrin contribution or delayed clot initiation, with supporting and conflicting evidence.
3. **Protocol option:** product or adjunct options from the selected, applicable protocol, including quantitative guidance only where its dose method is verified and all prerequisites are available.

An observed abnormality is not by itself an order or an assertion that the patient needs transfusion. Normal/unfinished/unavailable tests are never translated into an unrestricted `no bleeding risk` result. Unknown clinical context can still allow a descriptive finding; it withholds the dependent product option with a specific reason.

### Required clinical context

Record bleeding status (active/not active/uncertain), clinically significant bleeding as assessed by the clinician, site, procedure and phase, population/age, selected protocol/setting, relevant anticoagulant/antiplatelet exposures and last times, heparin/protamine context, recent transfusions/reversal/antifibrinolytics, source sample quality, temperature, pH and ionised calcium when the rule requires them. Weight is requested only for a rule that actually uses it. Do not burden simple administration entry with every decision-support prerequisite.

### Interpretation families to implement

| Pattern family | Evidence relationship | Explainable decision path |
|---|---|---|
| Reduced fibrin contribution | Matching FIBTEM or TEG functional-fibrinogen channel with current method-specific fibrinogen context | Show fibrinogen-replacement options allowed by the profile: cryoprecipitate and/or the exact fibrinogen concentrate; retain different doses/units and availability |
| Reduced overall clot strength | Appropriate whole-clot amplitude/strength considered with the paired fibrin channel and platelet count | Distinguish possible platelet contribution from fibrin contribution; do not equate a low MA/MCF with an isolated platelet defect |
| Delayed clot initiation | Assay-specific R/CT/ACT, corroborating laboratory results and anticoagulant context | Identify factor/anticoagulant possibilities and profile-supported further tests or replacement options; no automatic PCC-for-FFP substitution |
| Possible heparin effect | Verified paired non-heparinase/heparinase assays with compatible sample/run context | Explain the comparison and limitations; any protamine option requires its own exposure/dose protocol |
| Possible increased clot breakdown | Valid matured lysis observation and paired assay confirmation where required | Explain possible fibrinolysis and protocol-supported review; pending or non-detecting tests must not veto a time-sensitive protocol intervention |
| PlateletMapping or aggregation abnormality | Exact agonist, channel/controls, valid platelet-function profile and drug/clinical context | Explain the tested pathway and uncertainty; no generic platelet-transfusion instruction from inhibition percentage alone |
| No explanatory abnormality identified | Only the domains actually measured and interpretable | State the assessed domains and unresolved clinical bleeding; do not declare surgical haemostasis or absence of anticoagulant effect |
| Discordant or incomplete evidence | Different times, profiles, methods, invalid sample, conflicting results, missing paired channels | Show the disagreement and specific missing evidence; do not silently choose the result that yields a product recommendation |

These are software decision families, not universal clinical thresholds. The [evidence companion](2026-10-23-m10-device-and-evidence-matrix.md#clinical-interpretation-evidence) records primary technical and guideline sources. Each executable rule must name the exact applicable source and threshold. A literature reference range, analytic measuring range and treatment trigger are three different fields.

### Protocol object and rule contract

`M10ProtocolProfile` is immutable, versioned and content-hashed. It specifies title, source document/section/date, institution or reference scope, jurisdiction, intended population/setting, activation dates, status, reviewer approval, supported device/assay profile versions, prerequisites, exclusions, required evidence status/freshness, exact predicates and boundary inclusivity, priority/conflict rules, output text and product identities, source-linked dose methods, monitoring/retest guidance and fallback behaviour.

Numeric predicates carry units and basis. Dose methods carry formula, exact inputs, weight basis, product potency, dose cap, rounding, vial/pool policy and validation cases. The design does not invent a universal dose table or convert an existing research algorithm into an active hospital protocol. Candidate reference profiles may be browsed and tested in synthetic mode. An explicitly selected, clinically approved profile is required for actionable product/dose support. If none matches, the system still records all evidence and explains the pattern; its product panel states why quantitative guidance is unavailable. The initial record/interpretation design is complete without pretending that unreviewed numerical policies are already activated.

Profiles for adult critical bleeding, cardiac/post-bypass, liver transplantation, obstetrics, general surgery, medical bleeding and paediatric/neonatal contexts remain independently versioned. A hospital can adopt a verified reference profile or supply a verified local one; it is not required to use one vendor or the user's hospital. Two applicable but conflicting profiles must be presented for explicit selection or resolved by a documented precedence rule; never average thresholds.

### Required first interpretation release

The initial implementation must include usable, source-backed product-option paths as well as the registry. The following finite coverage target is the author's proposed release scope, not a claim that these clinical rules or device combinations are already validated. All core configurations in the evidence matrix require complete reported-result capture and verified mapping. The table specifies the additional minimum interpretation targets; it does not require the full Cartesian product of every device, setting and population.

| Required profile target | Population and setting | Required interpretation output |
|---|---|---|
| TEG 5000 kaolin plus functional fibrinogen, with heparinase comparison when available | Adult cardiac/perioperative bleeding, with phase-specific applicability | Clot initiation and fibrin/overall strength explanations; applicable plasma/factor, fibrinogen and platelet product options; heparin-context assessment |
| TEG 5000 RapidTEG plus functional fibrinogen | Adult trauma bleeding | Assay-specific initiation, strength and available lysis assessment; source-supported product options |
| TEG 6s Global Hemostasis | Adult cardiac/perioperative bleeding | Supported CK/CKH/CRT/CFF explanations and product-option paths; unavailable lysis remains explicit |
| TEG 6s Global Hemostasis with Lysis | Adult trauma bleeding | Supported CK/CRT/CFF findings and product options; lysis assessment with its actual timing and maturity |
| TEG 6s Global Hemostasis–HN | Adult cardiac/perioperative bleeding | Supported CK/CKH/CRTH/CFFH findings, paired heparin assessment and product options with the exact HN assay identities |
| ROTEM delta EXTEM/FIBTEM, with INTEM/HEPTEM/APTEM as required by a rule | Adult trauma or perioperative bleeding | Initiation, fibrin/overall strength and valid paired heparin/lysis explanations; applicable product options |
| ROTEM sigma Complete | Adult trauma or perioperative bleeding | Exact C-assay interpretations and product options, including APTEM C when required; no borrowed HEPTEM C result |
| ROTEM sigma Complete + HEP | Adult cardiac/perioperative bleeding | Exact C-assay interpretations and product options, including INTEM C/HEPTEM C comparison; no borrowed APTEM C result |
| Liver-transplant profile using ROTEM delta | Adults during liver transplantation | Separate phase/context-aware interpretation and product options under a verified transplant algorithm |
| Obstetric-haemorrhage profile using ROTEM delta | Adults with obstetric haemorrhage | Separate obstetric interpretation and product options under a verified obstetric algorithm |
| TEG 5000/6s PlateletMapping and ROTEM platelet | Only the population/settings supported by the exact assay documentation | Reported agonist/control values and plain-language pathway explanation; automatic platelet-transfusion or antiplatelet-reversal recommendations are outside the first release |

Each named treatment profile is a content-acquisition, clinical-review and software-verification work package. Before a target is marked delivered, acquire its exact source algorithm, establish that the stated device/reagent/sample and clinical context match, transcribe thresholds with units and inclusivity, and independently check the resulting decision branches. A missing or non-matching source leaves that target open; it never permits transplanting another device's threshold. Alternative supported reagent configurations within a family remain separately mapped and may reuse a rule only with explicit evidence of applicability.

Every treatment profile must demonstrate at least one supported positive product-option path, one valid assessment that produces no replacement option, and missing/discordant-evidence handling. Across the package, demonstrate distinct plasma, platelet and fibrinogen-replacement paths. Record PRBC, PCC, cryoprecipitate and fibrinogen concentrate throughout; a recommendation for PRBC additionally needs its own clinical/Hb protocol, and a PCC recommendation its exact indication/product protocol. Their presence in the product catalogue never establishes a VET-based recommendation. Quantitative doses remain conditional on a separately verified dose method and actual product information.

Paediatric/neonatal patients, adult medical bleeding outside these profiles, other liver/obstetric device combinations, and specialist/legacy assays receive full evidence capture and source-supported descriptive explanation in the first release. Patient-specific treatment options require subsequent matching profiles. This is an explicit interpretation limit, while the cross-hospital record remains available. The first complete implementation cannot be declared complete with an empty rule registry or only withholding messages; all required targets above need the specified delivery evidence. Clinical activation at a hospital remains separate from completion of the synthetic software release.

### Evaluation and explanation record

`M10Interpretation` retains evaluation ID, engine/profile versions and hashes, patient/encounter, review interval and both cutoffs, exact input pins and component/observation IDs, context assertions, input-quality decisions, conversions, evaluated rules, true/false/unknown status, findings, options, withheld reasons and generated time. No generative model chooses clinical thresholds or performs unverified dose arithmetic. Explanatory prose can be templated from the evaluated evidence.

Each option shows `why this appeared`, original evidence/time, applicable protocol, prerequisites and caveats, alternatives in that protocol, and reassessment needs. `Use in a draft` is a separate explicit action that copies an option into an editable request/prescription draft without saving, issuing or administering it. Editing any required input invalidates the prior result and draft linkage until re-evaluated. Reject stale queued saves after checking the current relevant evidence and profile identities at transaction/lock acquisition.

## 9. Clinical workflow and layout

One M10 navigation entry opens the current patient/encounter with the existing review-period controls. The overview has a compact blood-products summary linking to M10 and a clear completeness indicator. The five workspace views are:

1. **Products given:** intelligible received totals, product/processing breakdown and an administration timeline. Expand a row for donation/batch/issue/history details. Provide `Record product given`, with guided individual or aggregate entry and no false implication of administration by the application.
2. **Coagulation and calcium:** current selected results with ages, trends, status and product markers. Open exact reports and choose the evidence for an assessment.
3. **TEG and ROTEM:** device/cartridge selection or verified imported identity, channel-by-parameter results, actual trace/report, early versus matured results, serial same-profile comparison and source history.
4. **Interpretation and plan:** plain-language findings, selected clinical context/protocol, explained product options and missing prerequisites; clinician records accept/modify/defer with rationale and any linked draft. Acknowledge a finding without forcing an order.
5. **Bleeding, reactions and reassessment:** reported episode context, products around the episode, reaction events, subsequent test selections and clinician assessment. A later result is not labelled a treatment response unless that relationship is explicitly assessed.

Use the existing visual system and accessible form patterns. Product abbreviations have visible expansions/tooltips; processing status is textual as well as coloured. Totals display units adjacent to values; the interface does not present a single number labelled `blood given` across unlike products. Specialist detail is expandable, but missing data and clinically relevant product differences are visible in the default view. Keyboard, focus, error and screen-reader behaviour follow the current workspace.

Historical view has a persistent label and disables current-action drafts until returning to the current review. It can reproduce a prior saved assessment with its original profile and evidence. A current reassessment can reference historical evidence explicitly without rewriting the past.

## 10. ClinRx integration and proposed contracts

### Observed source baseline

Inspected candidate baseline: commit `a767c28` (`Checkpoint ClinRx candidate before M10`) on 23 October 2026. This design records code observations, not proof that the existing preview or M9 has passed a new audit. Existing source paths:

| Existing owner or boundary | Reuse and proposed M10 change |
|---|---|
| `backend/app/models/clinical/recorded_v2.py` and `facts.py` | Reuse patient binding, exact references, recorded time, provenance and correction structure; use a distinct clinician/derived assessment model for authored interpretations |
| `backend/app/models/clinical/laboratory.py` | Reuse report/components; add explicit blood/coagulation/calcium mappings and tested unit handling |
| `backend/app/models/clinical/respiratory.py` | Reuse exact gas/context evidence; do not change M9 facts into M10 reports |
| Existing medication contracts in `facts.py` | Reuse orders/administrations, prove missing detail and admission requirements before extension |
| `backend/app/services/renal_fluid_entry_service.py` and RF2 carrier rules | Reuse patient catalog/history and fluid references; move M10-specific admission into a dedicated service instead of expanding the RF2 class indefinitely |
| `frontend/src/api/rf2Client.ts`, generated schemas and `usePatientEvidenceState.ts` | Add bounded M10 data through shared snapshot/refresh orchestration and schema validation; preserve M9 arrays and existing decoders |
| `frontend/src/demo/PatientWorkspace.tsx` and `PatientOverview.tsx` | Add a lazy-loaded M10 view, summary and source navigation; preserve current view guards and handover selection |
| Existing append-only storage, gateways and migrations | Admit new typed kinds through explicit unions/registry/mapping/database migration; no catch-all JSON note as a substitute |

No original patient database, saved reviews, serving preview or `sources/` file is changed by this design. The M7 timestamp findings and ongoing director review retain their independently established status. M10 timestamp tests must cover their failure modes without claiming to close that review.

### New domain owners

Create typed transfusion records, viscoelastic reports, haemostatic medication courses/details, episode/reaction records and transfusion/fluid reconciliation assertions under a dedicated M10 package. Suggested ownership modules are `models/clinical/transfusion.py`, `models/clinical/viscoelastic.py`, `services/transfusion_service.py`, a read-only registry/rule evaluator and `frontend/src/transfusion/`. Names can be settled by the builder; the ownership boundaries above cannot be dropped.

All observed/reported records derive from `RecordedFactV2` with exact issuer/source ID/version. Clinician-authored assessments and generated interpretations must use appropriately separate authored/derived contracts, never relabel their origin as a laboratory source. Independent record kinds avoid a generic form with dozens of mutually inconsistent optional fields.

`EvidencePin` extends the existing repository/reference/digest/ingestion/cutoff pin with exact component/observation identity where needed. Quantity is an exact decimal string plus raw and mapped unit/basis. Count has a mandatory count basis. Time has explicit precision and source timezone. Patient identity, source issuer and profile identifiers never default from a free-text label.

### API and persistence behaviour

Proposed M10 routes: read catalog/snapshot, resolve exact source, bounded history, validate command, lookup command, save command, evaluate interpretation, and list/read versioned device/protocol profiles. Reuse the current synthetic loopback/origin/execution-disabled controls. Route spelling is an implementation choice; the command/recovery semantics are required.

Every write binds command ID, repository, patient/encounter, immutable canonical payload hash, source identity, operation type, actor and exact predecessor/digest/reason for corrections. Persist command outcome and record append atomically. Same command/same bytes returns the retained outcome; same command/different bytes conflicts. A replay of the same original source revision returns the exact retained record even after a later correction, with appropriate current/history disclosure. Conflicting source bytes require explicit correction. Recheck patient binding, relevant evidence and predecessor inside the transaction; no cross-patient links or stale predecessor replacement.

Before sending, retain pending command bytes in browser storage keyed by repository/patient/encounter and draft ID. On uncertain response/reload, lookup the exact command before retry. Confirmed save plus failed refresh is a distinct state. Concurrent tabs must not lose or silently overwrite pending bytes. Corrupt recovery data is retained and visibly isolated. Attachments are committed by digest before a referencing record is admitted, or the full command fails; unreachable/mismatched blobs cannot produce a successful report write.

Repository histories remain bounded and paginated. Server totals return completeness, input references, grouping basis, period and exclusions. Do not compute an admission total from a truncated first page. Hash/schema validation, strict booleans, decimal precision and explicit time parsing apply at transport boundaries.

## 11. Time, corrections and historical interpretation

Use both repository ingestion cutoff and clinical availability cutoff. For each source chain, choose the last revision admitted by the repository cutoff and available by the review end; filter availability before selecting the terminal revision. A report collected before the review end but first available later cannot inform that historical decision. Unknown availability can be displayed with uncertainty but cannot silently be counted as known-at-cutoff evidence in a protected interpretation.

Apply the same bounded cutoff to source resolution, terminal disclosure, history, attachments and derived inputs. A future correction must not leak through a history badge or modern terminal status in a historical view. Keep event time and knowledge time distinct: a late-entered transfusion can update the current historical-event account without rewriting a previously retained assessment.

Precision is part of eligibility. Day-only, bounded or approximate times cannot support exact `before`, `during` or `after` claims unless interval bounds establish them. Timestamp decimal/exponent inputs, null/malformed fields and mixed ISO/numeric representations require explicit validation; reject unsupported representations without rounding into a trusted relation. Versioned calculations retain input decimal text and arithmetic rules. Nothing automatically interpolates a missing lab, product volume or time.

## 12. Verification and acceptance scenarios

These are required implementation checks, not tests claimed to have run for this design.

| Area | Acceptance case and required result |
|---|---|
| Product clarity | Two PRBC records, one irradiated and leukodepleted and one with unknown irradiation, show separate documented attributes and totals without treating unknown as no |
| Platelet basis | RDP components, a pool and an SDP in one encounter remain separate; known constituent counts are secondary and unknown pool sizes do not gain an assumed conversion |
| Replacement choices | PCC and fibrinogen concentrate appear with original IU/g doses and recorded rationale; no invented FFP/cryo-equivalent quantities |
| Lifecycle | A request and issued bag do not count as administered; not-given has no positive dose; a partial stopped administration contributes only its known delivered portion |
| Cumulative updates | Start, pause, restart and completion of the same administration do not sum prior cumulative amounts as new delivery |
| Legacy entry | A source-reported aggregate without unit IDs remains an aggregate and does not create fictional donation/bag records |
| Aggregate coverage | Four PRBC units in an aggregate plus two explicitly included bags still totals four; possible overlap is indeterminate; complete constituents can replace the accounting representation without changing the exposure |
| Medication transition | An incomplete concentrate course stays a medication exposure; completion linked atomically to a generic administration counts once in both M10 and the shared medication view |
| Counting | Correction, replay, duplicate import, pool constituents and linked historical summary cannot duplicate the canonical exposure; uncertainty produces an incomplete total |
| Time windows | Adjacent periods, midnight/timezone boundaries, an ongoing infusion, day-only times and unknown end time behave according to section 5; no time proration |
| Fluid reconciliation | A matched `input_blood` record and administration contribute volume once; disagreement and partial aggregate overlap remain visible and block a falsely complete total |
| Laboratory | Hb, platelets, INR/PT, APTT, fibrinogen and both calcium types retain units, collection/availability, method and history; M9 gas calcium remains the same source |
| Assay mapping | At least one realistic original report fixture for every core device/cartridge configuration maps only its actual channels and parameters; no universal parameter mask |
| TEG cartridge | A Global Hemostasis result does not acquire LY30; the HN profile routes its lysis result to the verified assay, with CFFH/CRTH distinct from CFF/CRT |
| ROTEM cartridge | Sigma Complete and Complete + HEP differ correctly in APTEM C/HEPTEM C; delta S/liquid and sigma C profiles cannot borrow unverified ranges |
| Extended tests | PlateletMapping, ROTEM platelet, native/specialist/unmapped outputs preserve reported data without inheriting routine clot-strength rules |
| Run progression | Early A5 then an explicit A10 patch preserve CT/A5; an authoritative replacement cannot silently carry omitted observations forward; invalidated results cannot contribute; pending lysis and no-clot/aborted states never become zero or normal |
| Update recovery | Replayed/stale/out-of-order VET patches, changed base digests, missing observation IDs and partial failures cannot lose earlier results, duplicate a result or apply half an update |
| Source integrity | Wrong patient, wrong issuer, altered canonical bytes, stale correction, wrong attachment hash and cross-scope pins fail before any append |
| Interpretation | Each rule has boundary, true/false/unknown, wrong-device, wrong-unit, missing-context, stale-input, heparin, no-bleeding and conflicting-evidence cases |
| Clinical separation | A low whole-clot strength without a valid fibrin channel does not automatically select platelets; no VET result alone selects PRBC or PCC |
| Rule scope | Adult, obstetric, paediatric/neonatal and unknown-population cases cannot silently use another profile; unapproved/draft/retired profiles cannot produce active dose options |
| Minimum interpretation package | Every required treatment target in section 8 demonstrates positive product guidance, a supported no-option outcome and missing/conflicting-input handling; every specialist explanatory target has a verified example; an empty registry does not pass |
| Numeric correctness | Exact decimal unit conversion, comparator values, range limits, rounded display versus unrounded decision and any dose cap/rounding have independent expected values |
| Review saves | A queued save rechecks relevant evidence/profile identity after lock wait; later corrections invalidate current advice but preserve the prior saved assessment |
| Recovery | Lost response, refresh failure after confirmed save, reload, duplicate tab and corrupt storage preserve exact request recovery without duplicate delivery |
| Historical view | Later available result/correction/profile version is absent from the prior assessment and its source history; original assessment remains reproducible |
| Regression | Existing M7/M8/M9/laboratory/medication/source-history/handover paths continue to decode and function; migration preserves all existing rows and hashes in a disposable copy |
| Usability | A general physician can find products/modifications/counts, read a plain-language explanation, inspect the original report and distinguish an option from actual administration |
| Capacity | Maximal report, many administrations, paginated history and attachments stay within budgets or fail clearly before write; totals identify incomplete retrieval |

Use synthetic isolated data only. Capture pre-change source/build/database manifests, migrate a disposable database copy, preserve the existing preview and launch a separately versioned M10 preview. Verification evidence identifies exact source revision, active profiles and limitations. Device support claims require profile-by-profile evidence; clinical interpretation requires review by transfusion/haemostasis specialists before active clinical use.

## 13. Delivery sequence and builder decisions

This is design sequencing, not an approved implementation plan:

1. Product catalogue, typed lifecycle contracts, exact quantities, laboratory mapping and source/recovery behaviour.
2. Administration entry, received totals, reconciliation and connected overview/history on an isolated synthetic preview.
3. Core TEG/ROTEM profile registry, complete result entry/import, trace preservation and serial views for every named core configuration.
4. Deterministic pattern interpretation and explanation, protocol registry, profile-specific product options and independently verified dose methods where supported.
5. Reassessment/reactions, clinical expert review and full connected regression/acceptance evidence.

All five belong to the complete M10 scope. An interim release must state which profile and workflow capabilities are delivered; it cannot call record capture alone the completed module.

The builder may choose component names, API path spelling and file splits consistent with the current stack. The builder must inspect the current shared source before editing overlapping M9 files, keep existing migrations and contracts, and use explicit file ownership if implementation is delegated. No new platform or database is required by this design.

Remaining deployment-specific work is deliberately data-driven: current regional IFUs and export schemas, approved local/reference protocol thresholds, formulary/product potencies, population rules, clock/identity mappings and authorisation roles. None requires narrowing the user's requested cross-hospital scope. These items determine which profile can be activated at a hospital, not whether its source records can be represented.

## 14. Design review and approval boundary

The requested deliverable is this complete design plus its device/evidence companion. It specifies behaviour, ownership, interpretation eligibility and acceptance evidence. It does not claim implemented functionality, verified device connectivity, approved numerical protocol content or clinical validation.

An independent builder review identified ambiguity about the minimum interpretation package. Section 8 now specifies the initial targets, output levels and completion gates. The follow-up review found no important planning questions remaining. Product quantities, processing attributes, core device capture, laboratory/calcium scope and shared medication/fluid ownership are described for implementation planning. This is a software-design review, not a clinical validation of treatment rules.

Obtain design approval before writing product code. Then create the implementation plan using the repository's planning workflow. If the user requests a change to the design, amend this document and preserve the final accepted choices in the plan.
