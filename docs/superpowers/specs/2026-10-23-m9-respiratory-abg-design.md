# ClinRx M9 respiratory and ABG

Design v0.2 · 23 October 2026 · Bedside interface approved, implemented and verified in the synthetic workspace; clinical validation remains open

Working label **M9 respiratory/ABG** corresponds to **original roadmap M10**.
Historical roadmap references retain original M10. Original M9 fluid balance is
consolidated into M8. This addendum does not renumber M11–M18 or migrate data.
The concurrently added `respiratory_record` owner and local M9 review domain must
be preserved; do not rewrite their IDs to match historical roadmap labels.

## Intent and inherited decisions

Build the next ClinRx bedside module on the shared patient workspace, with the
clinical detail of M6–M8 and a compact interface. A clinician should be able to
answer: what support was actually delivered, what the selected gas means in its
recorded context, whether mechanics can be trusted, and what needs review next.

Keep a single identity for each investigation, support observation and airway
episode. Fluid charting stays in M8. Link infection/antibiotics to M6, circulation
to M7, devices to original M12, sedation/awakening to original M13, metabolic
context to original M17 and transfer to original M18. These are references to
the original records, not parallel forms with copied values.

The handoff establishes the product direction and reuse constraints. The precise
contracts, initial delivery boundary and interface arrangement below are design
proposals. They have not been approved or implemented by this document.

The user subsequently required clinical accuracy against ACCP/CHEST, ERS and
**Indian Chest Society (ICS)** guidance, with an interface usable by intensivists,
pulmonologists, physicians and surgeons. Indian Chest Society was explicitly
confirmed; do not substitute the UK Intensive Care Society or ISCCM. ISCCM
guidance, when used as supplementary Indian critical-care evidence, needs its
own attribution. Society references establish evidence sources, not accreditation,
endorsement, certification or proof that a product meets every society standard.

## Approaches and recommendation

1. **Extend the existing shared workspace (recommended).** Reuse its scope checks,
   source/history inspection, exact revisions and local review mechanism. Add a
   respiratory read model, then additive source types for support and mechanics.
   This preserves one record per fact and matches the M7/M8 experience. It needs
   coordinated changes to the shared shell and the laboratory contract.
2. **Build a separate respiratory app.** It could be previewed independently but
   would duplicate patient selection, history, laboratory joins and review state.
   That conflicts with the inherited shared-record design.
3. **Put every new field in the existing circulatory oxygen family.** This would
   minimize initial wiring but would blur arterial, venous, support and device
   semantics and overload M7. Preserve that family for accepted historical facts;
   introduce neutral gas/support contracts for genuinely new capabilities.

The inherited architecture leaves approach 1 as the practical fit. The builder's
recommendation is not recorded as a user selection or clinical approval.

## Inspection baseline and concurrent update

**Concurrent update discovered during final checks:** the shared candidate now has
`frontend/src/respiratory/RespiratoryWorkspace.tsx`, entry/source/review components,
`respiratoryModel.ts`, `physiology.ts`, a typed `respiratory_record` contract and
respiratory tests. `PatientWorkspace.tsx` now mounts that workspace. Additional
design/standards/method documents from the concurrent work are under the same
`docs/superpowers/` tree. Preserve them; this document is a supplemental evidence,
safety and usability proposal, not authority to replace that implementation.

The existing source includes synthetic physiology arithmetic and broader lung
function/sleep/specialist tabs. It must not be described as having all arithmetic
disabled. Whether those calculations satisfy every input/protocol condition in
this addendum requires a separate implementation audit. The staged profile table
below describes proposed acceptance, not the current feature-flag state.

The initial inspection table below records the earlier baseline. Where the new
implementation supersedes it, the concurrent-update note takes precedence.

The inspected candidate has these features:

| Area | Observed implementation | Consequence |
|---|---|---|
| Patient shell | `PatientWorkspace.tsx` mounts M7, M8, antibiotics and overview; no respiratory workspace | Add one destination without replacing existing views |
| Source gas values | `OxygenTransport` admits pH, PaCO2, PaO2, bicarbonate, base excess, saturation and haemoglobin | Reference exact existing facts; do not recreate a panel |
| Sample context | Optional `BloodGasContext` retains collected time, FiO2, oxygen device, mode, PEEP and provenance | These are sample-time assertions, never assumed present support |
| Specimen semantics | Existing sample enum has arterial and several venous types but no capillary; `paco2` is arterial/unknown | New VBG/capillary needs a neutral, additive contract; do not relax old labels |
| Gas panel identity | Legacy facts carry individual specimen/source assertions; a complete shared panel cannot be presumed | Group only by explicit compatible identity, not equal timestamps |
| Laboratory work | New uncommitted `LaboratoryReport` and laboratory entry work exist; supported mappings are currently urea/BUN, sodium/potassium and urine findings | Coordinate an additive mapping/decoder extension; existence of the envelope does not admit gas mappings |
| Scope validation | `bedsideModel` checks patient, encounter, exact window, repository and watermark; execution must be disabled | Reuse and extend this boundary for all respiratory sources |
| Reviews | Browser storage currently supports M7/M8 and append-only, same-scope writes | Add original M10 domain explicitly, without rewriting existing keys |
| M8 | Daily chart and renal investigations already exist | Surface linked M8 context; do not recalculate fluid balance |

The worktree contains concurrent edits to the patient shell, laboratory contracts,
review components and transport files. No historical M8 test count establishes
the current candidate's status. Source hashes in the accompanying audit identify
the inspected versions; implementation must recheck them before integration.

## Delivery boundary and acceptance

These increments are acceptance boundaries for the proposal, not instructions
to rebuild the concurrently added module. Retain its specialist areas and apply
the compact bedside arrangement as an overview after approval. Do not remove
implemented features solely because they were outside the earlier R1 proposal.

**R1: usable source review.** Dedicated respiratory bedside screen consuming
existing accepted gas, SpO2, respiratory-rate, lactate and relevant shared sources.
Exact specimen selection and source inspection; sample-time support displayed
as supplied; missing support/mechanics/targets/trials explicitly shown. Manual
respiratory review saved with exact evidence pins using the existing browser
review store after its domain is extended. No clinical calculation or treatment
profile enabled. This is the first implementation increment proposed for approval.

**R2: typed source workflows.** Add timed support observations and change events,
neutral gas sample context and mechanics assessments through the canonical source
owners. Include validated transport, persistence, corrections/history, guarded
entry and explicit review-before-append. Connect devices, targets and trials only
through their agreed shared owners. Unsupported capabilities remain visible as
unconnected; no placeholder form claims durable clinical charting.

**R3: separately validated derivation profiles.** Implement arithmetic only after
its input contracts, unit conversions, measurement eligibility, primary formula
sources and validation vectors pass review. ARDS classification, target flags,
SBT screening and condition-specific treatment suggestions require separate
approved clinical profiles. A calculator release never enables them implicitly.

All increments are synthetic engineering previews until clinical release work is
complete. No ventilator/device command, medication order, production deployment,
automatic diagnosis, automatic alert integration or clinical migration is included.

R1 succeeds when the recorded gas can be opened beside its original respiratory
context in two actions, conflicting/unknown context is obvious, failed refresh
blocks current-source actions, and M7/M8/antibiotic workflows continue working.
R2/R3 completion must be reported separately; the R1 screen is not the full module.

## Record primitives and invariants

Every new persistent fact inherits canonical patient/encounter binding, repository,
kind, exact ID/revision/digest, ingestion sequence, source namespace/identifier,
author/issuer, availability, status, provenance and correction lineage. Reuse
`RecordedFactV2`, `RecordedTime`, `SourceCode`, `ExactQuantity` and existing
exact-reference protocols where their semantics fit. Do not invent new universal
source owners or a duplicate respiratory laboratory table.

The following are proposed typed shapes, not currently admitted transport types:

- `Known<T>` = `{state:'known', value:T, evidence:ExactPin[]}`.
- `Missing` = `{state:'not_recorded'|'not_measured'|'pending'|'unavailable'|
  'not_applicable'|'unknown', reason?:Text, evidence?:ExactPin[]}`.
- `Conflicted<T>` = `{state:'conflicting', alternatives:Known<T>[], reason:Text}`.
- `Field<T>` = `Known<T> | Missing | Conflicted<T>`. No value accompanies a missing state.
- `Quantity` retains decimal text, comparator and original unit/code. A separate
  normalized quantity names the conversion version and its original evidence.
  `NaN`, infinity, binary floating source input and booleans are inadmissible.
- `Time` retains source lexeme, offset, precision and known/approximate/bounded/
  unknown state. No conversion to an exact instant from a day or unplaced record.
- `Interval` has start/end assertions and end state open/closed/unknown. An open
  episode does not prove uninterrupted delivery. Cutoff and event time are distinct.
- `ExactPin` includes repository, kind, ID, version, expected digest and ingestion
  placement. For a panel component include exact component identity as well.
- `RecordedAssessment` records selected evidence, assessor, time, uncertainty and
  assessed scope. A negative finding requires an actual assessment; absence is unknown.

Required fields mean required keys with an explicit state, not a requirement to
fabricate a value or prevent admission of an incomplete external report. Required
identity keys must be present for a stored source. Incomplete/unidentified imports
stay at their source owner as held reports and do not enter calculations.

All field families below inherit these types. Numeric clinical reference ranges
are not data-validation ranges. Preserve unusual source values; prevent use only
when a specified structural, measurement or clinical eligibility rule fails.

## Field dictionary

### A. Respiratory baseline and scope

| Field/group | Type and required meaning | Owner / conditions |
|---|---|---|
| Patient eligibility | Age/DOB evidence, adult/paediatric/unknown scope; pregnancy context if relevant | Shared patient source; adult calculators require explicit eligible scope |
| Pulmonary baseline | Repeated coded/narrative conditions, onset, activity, baseline function, prior admissions | Shared history; retain COPD/asthma/ILD/bronchiectasis/OSA/OHS/neuromuscular/chest-wall distinctions |
| Home support | Device, mode, flow L/min, source FiO2, schedule, baseline oxygenation/CO2, source date | Refer to home support record; do not assume inpatient settings |
| Airway history | Difficult-airway assessment, prior intubation/tracheostomy, anatomical concerns, aspiration/swallow history | Original M12/history; each finding assessed/unknown |
| Symptoms and exam | Dyspnoea, cough, sputum, wheeze, chest pain; work of breathing, accessory use, pattern, auscultation, consciousness | Timed observations; source/reviewer recorded |
| Height | Exact source quantity cm or validated inches, measured/estimated method, time, uncertainty | Shared anthropometry; no height from weight/BMI back-calculation |
| PBW method category | Explicit clinician-selected ARDSNet formula category and rationale/source | Separate from demographic gender and dosing weight; no automatic inference |
| Care goals | Existing escalation/ceiling, intubation preferences, capacity/decision source, responsible clinician, validity period | Shared care plan; unknown does not mean full escalation or limitation |

### B. Respiratory support episode, actual observations and changes

| Field/group | Type, units and distinctions | Conditions |
|---|---|---|
| Episode links | Exact support episode, airway/device episode, source device model/software/interface, encounter | Reuse original M12 where present; unresolved remains explicit |
| Delivery state | Prescribed / prepared / started / running-observed / changed / paused / stopped / non-delivered / unknown | An order alone does not establish delivered support |
| Timing | Observed time, source availability, claimed effective interval, prior exact state and change-event reference | No carry-forward across undocumented gaps or changes |
| Modality | Room air / low-flow oxygen / fixed-performance mask / HFNC / NIV / invasive / tracheostomy collar / other / unknown | Recorded modality; no inference from FiO2 alone |
| Oxygen device | Source term plus curated mapping/version; nasal/mask/reservoir/interface; humidification and heater observations | Raw device labels retained even when mapping unsupported |
| Flow | Oxygen source flow, total mixed flow and delivered flow separately; L/min | HFNC blended flow is not low-flow oxygen input; oxygen bleed-in does not establish FiO2 |
| FiO2 | Raw decimal + `%` or fraction unit, set/measured/estimated basis, certainty, range if supplied, oxygen analyser evidence | No low-flow formula by default; room-air observation may explicitly supply 0.21, never infer it from blank device |
| Mode | Manufacturer raw mode and versioned mapping: volume/pressure assist-control, SIMV, pressure support, CPAP/BPAP, APRV, other | Unknown mapping blocks mode-dependent calculations, not source display |
| Rate | Set backup rate and total measured respiratory rate separately; breaths/min | Spontaneous rate is its own observation if supplied |
| Volume | Set, inspired and expired tidal volume separately; mL/L and measurement basis BTPS/STPD/unknown | Inspired/expired/leak-affected volumes are not interchangeable |
| Minute volume | Measured inspired/expired minute ventilation L/min; averaging interval | A ventilator value remains source-derived, distinct from a ClinRx multiplication |
| Pressure settings | Set PEEP/EPAP, IPAP, pressure support, inspiratory pressure, high/low pressure; cmH2O | Each pressure declares absolute airway pressure or pressure above PEEP; IPAP is not relabelled as pressure support |
| Timing settings | Inspiratory time s, I:E ratio as two positive decimals, inspiratory flow L/min and waveform | Retain source mode applicability; no numeric zero for not applicable |
| Trigger/cycling | Trigger type and value/unit, cycling setting, rise time/ramp | Source-specific codes; not one universal numeric unit |
| Interface and circuit | NIV interface type/fit/leak, humidification type/status, circuit connection, oxygen supply, alarms checked | Timed assessment, assessor and limitations |
| Changes | Intended plan ref, actual old/new exact observations, change time, reason, author, response assessment link | Proposed settings never overwrite actual observed settings |

### C. Bedside oxygenation and ventilation observations

SpO2 (%), RR (breaths/min), ETCO2 (mmHg/kPa), transcutaneous CO2 (mmHg/kPa),
temperature (°C), consciousness and work of breathing are distinct observations
with observed time, device/site, quality, averaging interval if supplied and support
link. SpO2 includes waveform/signal quality, motion/perfusion limitations and
source device limitations. ETCO2 includes waveform and sampling/interface context;
it is not substituted for PaCO2. Pulse oximetry is not measured co-oximetry.

Display existing accepted SpO2/RR sources immediately in R1. ETCO2 and transcutaneous
measurements require additive admitted types. A disconnected monitor is an explicit
source/assessment state; missing SpO2 is not proof of disconnection.

### D. Gas specimen, panel and component results

| Field/group | Proposed type / units | Rules |
|---|---|---|
| Panel identity | Exact issued report and component pins; source analyser run, accession, collection event and specimen identity | Unknown relationships do not become one sample by timestamp proximity |
| Specimen | Arterial / peripheral venous / central venous / mixed venous / capillary / circuit-pre-oxygenator / circuit-post-oxygenator / other / unknown | Explicit sampling site and line; circuit gases are not systemic arterial gases |
| Times | Ordered, collected, received, measured, reported, clinically available and imported | Each independent; sample trend uses collection time, knowledge cutoff uses availability |
| Collection conditions | Site, line/discard/flush contamination assertions, air bubble/clot/rejection flag, delay, temperature correction, patient temperature | Source documented or explicitly missing; do not manufacture sampling facts |
| Analyser | Issuer, analyser/method/version when available, quality flags, result status, correction lineage | Reject/invalid flags block arithmetic while preserving report |
| Core gases | pH dimensionless; neutral pCO2 and pO2 mmHg/kPa | UI prefixes Pa/Pv/Pc only when specimen identity supports them |
| Acid/base components | Actual bicarbonate, standard bicarbonate, total CO2 and base excess/deficit as separate coded results; mmol/L or mEq/L source units | Source measured/calculated/unknown plus calculation method; do not collapse analytes |
| Lactate and haemoglobin | Lactate mmol/L (mg/dL only under an analyte-specific conversion profile); haemoglobin g/dL or g/L | Link only the supplied specimen relationships; legacy lactate remains separate if unlinked |
| Co-oximetry | Functional saturation %, fractional oxyhaemoglobin %, COHb %, MetHb %, total Hb and other source fractions | Record fraction definition; calculated saturation is not measured saturation |
| Electrolytes on gas | Sodium/potassium/chloride/ionised calcium mmol/L, glucose source units | Gas and chemistry assays stay distinct; no automatic panel merge |
| Sample-time support | Exact source support assertion/observation refs, timing relation, FiO2 basis, mode, flow and PEEP; patient position and stability since last change | Preserve legacy BloodGasContext as source assertion; never substitute later support |
| Alignment review | Explicitly matched / uncertain / conflicting / unmatched, reviewer/source, match interval, intervening changes, clock/precision limitations | Proximity alone does not prove stable support or physiologic equilibration |

Legacy `paco2` remains arterial/unknown. New neutral `pco2` or venous concepts
must have a versioned mapping and end-to-end decoder before ingestion. Existing
PaO2 records with contradictory venous or unknown context are visible with an
integrity warning and ineligible for P/F; do not silently rewrite historical facts.

Do not require a new panel wrapper to display old individual facts. If source
identity supports grouping, show a source-labelled panel with per-component pins;
otherwise show separate observations. Corrections preserve original collection
identity and do not become evidence of physiological change.

### E. Ventilator mechanics assessment

Record one assessment identity, exact support observation(s), airway/circuit,
measurement time/interval, method, assessor and source quality. Required fields
have explicit missingness: measured inspired/expired VT and volume basis; peak,
plateau, set PEEP, **total PEEP** and mean airway pressure (cmH2O); inspiratory and
expiratory hold duration (s); zero-flow condition; passive/no-effort state;
spontaneous effort, leak and asynchrony findings; expiratory-flow return; auto-PEEP
source measurement and method; circuit integrity and measurement comparability.

Plateau recorded during effort remains visible but is ineligible for passive
driving-pressure/static-compliance profiles. Set PEEP cannot silently stand in
for total PEEP. Pressure-control amplitude and peak pressure are not plateau.
Inspiratory effort cannot be inferred absent because paralysis was ordered.
If source static compliance/resistance/auto-PEEP exists, display as source-derived
with units and method, separately from any ClinRx result.

Source airway resistance, elastance, P0.1, occlusion pressure, oesophageal pressure
and transpulmonary measurements need source codes, method/calibration, sampling
conditions and explicit units. They are recordable under a validated extended
contract, with no interpretation profile in the initial release.

### F. Imaging, airway care and cause assessment

Link exact imaging/ultrasound study/report, performed and available times, modality,
site/laterality, interpreter and version. Bilateral opacities, oedema, effusion,
consolidation, atelectasis and pneumothorax are source/reviewer findings with
assessed/unknown state. No diagnosis is extracted automatically from free text.

Airway position/depth/unit and landmark, cuff pressure cmH2O and measurement,
securement/skin assessment, patency, humidification, secretions (amount, character,
blood), cough strength, suction frequency/indication/response and complications
reference the original airway/care episode. Tracheostomy type/size/cuff/fenestration,
date and stoma care stay with original M12. Respiratory culture/specimen and actual
antimicrobial exposure link to M6; no new respiratory antibiotic list.

Cause assessment is clinician authored: hypoxaemic/hypercapnic/mixed/undifferentiated
pattern; suspected infection, cardiogenic contribution, obstruction, atelectasis,
pleural disease, embolic/pulmonary vascular concern, neuromuscular/central cause,
drug effect or mixed possibilities. Each retains supporting and opposing evidence,
uncertainty and alternatives. These labels are not generated diagnoses.

### G. Targets and review plan

One shared target record contains patient/encounter, target concept, low/high or
single bound with inclusive/exclusive comparator, unit, clinical rationale,
responsible clinician, applicable condition/support, effective interval, source,
status and review/expiry event. Concepts may include SpO2, PaO2, PaCO2, pH, VT/PBW,
plateau and pressure limits. Missing/conflicting/expired targets remain explicit.

R1 may record proposed targets only as labelled reviewer text; it does not chart
a clinical target. R2 structured target authoring requires the canonical target
owner and durable audit. Never introduce universal saturation or permissive
hypercapnia defaults. COPD/hypercapnic risk, brain injury, pregnancy, pulmonary
vascular/RV disease and other special populations require selected local profiles.

A review contains action, reviewer, rationale, next review plan, exact selected
evidence, uncertainty and optional working assessment. Maximum lengths and storage
guards follow the shared store. Browser reviews are locally saved synthetic notes,
not signed clinical records or scheduled reminders. Retained/historical reviews
never become current conclusions after evidence changes.

### H. Positioning, rescue and specialist interventions

Proning has a canonical procedure/position episode reference, indication and
reviewed protocol version, planned versus actual start/stop, interruptions,
contraindications/reason, team readiness, airway/line/security checks, monitoring
connection, haemodynamic tolerance, pressure/eye/skin care, complications and
timed response. Store assessor/time/unknown for each check; do not default checks
to complete. Incomplete monitoring prevents an 'operationally ready' conclusion.

Neuromuscular blockade, sedation and analgesia reference actual exposure in M13;
an order is insufficient. Inhaled pulmonary vasodilator, recruitment manoeuvre and
bronchoscopy records link agent/procedure, device, dose and unit if applicable,
actual delivery, start/stop, clinical indication, responsible specialist, safety
observations and response. No intervention is recommended from a P/F value alone.

ECMO uses an original M12/support episode and specialist record: VV/VA/other
configuration; cannula identities/sites; observed pump blood flow L/min; sweep gas
L/min; circuit delivered oxygen fraction explicitly distinguished from ventilator
FiO2; oxygenator pre/post pressure/site; source gas specimen sites; circuit
complications, specialist assessment and decisions. Anticoagulation remains
original M11. Respiratory bedside summaries do not implement ECMO management.

### I. Awakening, breathing trials and liberation

One canonical trial episode links M13 awakening/sedation assessment, support,
airway/device and observations. Fields: trial ID; responsible clinician; protocol
ID/version; screening time; assessed eligibility/contraindications/missing checks;
trial technique (T-piece/CPAP/PSV/other), exact settings and oxygen before/during;
actual start/stop and interruption; timed RR, SpO2, HR, BP, work of breathing,
mental state and gas where supplied; pass/fail/stopped/not completed/unknown,
clinician rationale and failure reason; return-support observation and response.

RSBI is an optional source/derived observation with spontaneous RR and VT units
and technique. It is not a mandatory screening gate. Record any FiO2 increase
during a trial rather than quietly carrying a 'pass' forward. A selected local
protocol owns trial criteria and timing. No SBT pass automatically selects extubation.

Extubation readiness is a separate assessment with airway protection, cough,
secretions/suction burden, consciousness and sedation, haemodynamic status,
airway obstruction risk, applicable cuff-leak assessment, reintubation risk,
responsible decision-maker and backup/escalation plan. Passing each item must be
recorded; absent means unassessed. An extubation procedure and actual support
transition reference original M12 and the support episode.

Post-extubation plan includes actual oxygen/HFNC/NIV if delivered, monitoring,
review time/event, deterioration/reintubation plan and clinician ownership.
Tracheostomy weaning/capping/decannulation and swallowing assessments retain
their separate shared procedure and specialist records, with explicit outcome.

## Bedside interface and interaction

### A common screen for several specialties

One shared bedside view serves all four audiences; the selected evidence, units,
limits and safety gates do not change with specialty. Intensivists and
pulmonologists can expand mechanics, waveform/measurement conditions, gas
comparability and acid-base detail. Physicians and surgeons see the same clinical
facts with familiar wording, visible uncertainty and short explanatory labels.
This is progressive disclosure, not a reduced-safety or different-authority mode.

The default view uses **Breathing support**, **Blood gas**, **Lung mechanics** and
**Review plan**. Retain recognised abbreviations after the clear label: oxygen
level (SpO2), inspired oxygen (FiO2), end-expiratory pressure (PEEP), carbon dioxide
(PaCO2 only for arterial samples). Define each abbreviation on demand; never
replace units with unexplained icons. Key uncertainty, changed support and
specimen type remain visible without opening advanced detail.

The top summary separates **Recorded facts**, **Your assessment** and **Plan**.
An empty assessment reads 'Not assessed'; the screen does not generate a clinical
headline from disconnected measurements. 'Review needed: sample settings differ'
may describe an established evidence mismatch; 'NIV failed' needs an actual
clinical assessment or an independently approved failure profile.

Additional fields open only for the selected recorded modality or workflow.
Preserve values when switching views, and make inapplicable fields explicit in
the record; hiding a control must not silently erase its evidence. Source entry
prefills references to existing facts rather than copying values into a second
chart. Searching/expanding advanced detail never changes which sample is selected.

### Surgical and postoperative context

Reference the original surgery/procedure episode: operation/time, thoracic/
abdominal/cardiac/other category, relevant anastomosis, aspiration concerns,
analgesia/sedation and residual neuromuscular-block assessment, secretions/cough,
airway protection, fluid/circulation context and source imaging. Surgical
complications are reviewer-assessed; the software does not diagnose anastomotic
leak, sepsis, embolism or residual paralysis from a gas.

Three separate workflow labels are mandatory: **Postoperative respiratory failure**,
**Prevention after planned extubation**, and **Deterioration after extubation**.
Prevention evidence must not be presented as rescue treatment evidence. A
clinician records the indication, contraindications/airway assessment, monitoring
and escalation readiness before any eventual decision-support profile applies.
Current R1 offers source review and links; no selectable treatment command is added.

### Proposed overview arrangement

| Position | Always visible | Expand on demand |
|---|---|---|
| Patient strip | Identity, encounter, review window, evidence confirmation and synthetic status | Repository/source diagnostics |
| Breathing support | Observed time, device/mode, known versus estimated oxygen, flow/PEEP if recorded | Actual settings, changes, interface, uncertainty |
| Selected blood gas | Specimen and collection time, pH, CO2/O2, bicarbonate; sample-time oxygen context | Full panel, co-oximetry, metabolic context, method/quality/history |
| Lung mechanics | Available assessment or explicit connection gap; set/measured distinction | VT/PBW, plateau/total PEEP, validity checks and source-derived values |
| Review plan | Clinician-entered concern, action, owner and next review; absent stays unassessed | Targets, working cause, condition/postoperative pathway, trials |
| Evidence timeline | Selected specimen and actual support-change ordering | Compare exact before/after sources |

Usability acceptance: each audience can identify the selected specimen, its
sample-time oxygen, later support changes, missing target and next reviewer action
without opening raw data. These are testable tasks, not a claim of completed
clinical usability testing. A surgeon's walkthrough must include a postoperative
case; a specialist's must include invalid plateau conditions and a mixed
acid-base possibility. Their findings must precede a clinical release claim.

Use the existing patient banner, compact typography, cards, source drawer and
manual-review pattern. The tab is **Respiratory & ABG**. Show **M9 · original M10**
in module help/export metadata rather than repeated technical identifiers in care
forms. Preserve the current `?workspace=respiratory` route and M9 review domain;
historical aliases are documentation, not a storage migration.

Four compact questions organize the screen:

1. **Support:** actual observation and time, device/mode, flow/FiO2 basis, PEEP;
   'not connected' or 'choose a source' when appropriate. Plan and delivery differ.
2. **Gas:** selected specimen/time, pH, specimen-specific CO2/O2 labels,
   bicarbonate/base excess and sample-time support. Lactate/Hb/co-oximetry expand.
3. **Mechanics:** selected assessment, set/measured VT, plateau/total PEEP and
   method limitations. PBW and derived indices show 'not enabled' in R1.
4. **Next step:** reviewer-authored action, uncertainties, targets and next review;
   links to positioning and liberation detail only when needed.

Below: a compact collection-time gas table beside actual support changes, with
explicit separate lanes for venous/capillary/circuit samples and uncertain times.
Never draw a continuous trend across incompatible methods, specimen types,
corrections or unsupported units. In R1, use a source list when panel grouping
is not established. Multiple samples require explicit selection; newest sorting
does not choose a clinical 'current' sample.

The drawer has Gases, Support, Mechanics, Airway/imaging, Trials and All sources.
Each exact result shows time, specimen, unit, measured/source-derived basis,
quality, limitations, source/history and its pinned support relation. Original
JSON belongs in a secondary technical-details disclosure, not the main care view.
Restore keyboard focus to the initiating control; Escape closes detail/drawer;
headings announce navigation, busy and errors. Tables scroll internally on mobile;
no page-wide horizontal overflow. Do not convey status by colour alone.

Record source entry and record review are different actions. Source entry lives
with its canonical owner and follows validate → review → confirm append → exact
readback. During an uncertain save, retain the guarded editor and request identity;
recover by exact command lookup before explicit retry. Never issue a fresh command
because the first timed out. Corrections append with a reason and exact predecessor.

## Assembly, chronology and conflict rules

1. Match patient, encounter, repository, review boundaries and cutoff across all
   supplied read models. Fail closed for wrong scope, digest mismatch, duplicate
   exact references, later ingestion or unconfirmed execution gate.
2. Sort events using exact source time precision/offset semantics. Day-only,
   bounded, conflicting or unknown time stays unplaced and cannot match a sample
   to a ventilator setting. Do not use JavaScript millisecond truncation to prove
   equality of higher-precision boundaries.
3. Use collection time for physiological placement and source availability plus
   repository cutoff for what was known. A result reported later cannot appear in
   an earlier knowledge snapshot merely because it was collected earlier.
4. Specimen grouping needs compatible explicit source identity and lineage. Equal
   times or equal values never deduplicate different records or prove a panel.
5. A documented sample-time assertion may be displayed as such. Conflicting
   contemporaneous settings block derived use pending resolution. Do not choose
   a source automatically by provenance rank or most recent import.
6. Sample-to-support matching needs an explicit relation or validated reviewed
   interval with no unresolved intervening changes, adequate clock precision and
   recorded equilibration/stability conditions required by the selected profile.
   There is no universal match window in R1. 'Within five minutes' is insufficient.
7. A later change is a separate event. Preserve the gas's original settings, the
   change and subsequent response; never recompute the old gas using new FiO2.
8. No carry-forward of open support episodes to prove present delivery. Separate
   'last recorded' from 'observed in this interval'; always show its age/time.
9. Corrected/withdrawn reports remain inspectable. Authoritative revision selection
   follows the source owner's lineage contract; unresolved branches remain conflicted.
   Never plot correction as physiological improvement.
10. Failed refresh invalidates current evidence/actions. Retained facts may be shown
    as unconfirmed historical context with exact-source actions disabled. Generation
    guards prevent late responses from replacing a new scope; hide/disable cross-
    patient saved reviews. Drafts pin snapshot signatures and become stale on change.
11. Missing is never zero, normal, stable, complete, negative or not indicated.
    Transport failure and 'feed not connected' are distinct from 'not measured'.

## Proposed versioned arithmetic and clinical profiles

Every result envelope must name profile ID/version, arithmetic/conversion version,
status eligible/withheld/not-enabled, reasons, exact input pins, support relation,
patient scope, knowledge cutoff, assumptions, unrounded decimal result, display
rounding and time. Do not persist rounded display values as future inputs.

These are **staged specifications**, not enabled algorithms. Constants/formula
sources marked pending must be verified against primary text before product code
uses them. Admission/scope gates can be implemented and tested independently.

| Stable proposed ID | Formula / definition | Mandatory eligibility and limits |
|---|---|---|
| M10-FIO2-NORMALIZE/v1 | Explicit `%` ÷100; fraction unchanged | Positive and ≤1 fraction after exact conversion; unknown unit/basis, flow-only, estimate or conflicting relation withheld from strict P/F |
| M10-PF-ARTERIAL/v1 | Systemic arterial PaO2 in mmHg ÷ eligible sample-time FiO2 fraction | Explicit arterial identity, valid quality/status, exact numeric values, reviewed support alignment, known concentration; no VBG/circuit gas, comparator or later FiO2; numeric ratio is not ARDS diagnosis |
| M10-PBW-ARDSNET-CM/v1 | Male-formula category: 50 + 0.91×(height cm−152.4); female-formula category: 45.5 + 0.91×(height cm−152.4), kg | Adult scope, validated height/method, explicit formula category, positive PBW; original protocol verification pending. Do not call cm and inch coefficients bit-for-bit identical |
| M10-VT-PBW/v1 | Selected VT mL ÷ selected PBW kg | Same eligible adult and referenced PBW version; explicit set/inspired/expired designation and time/support; actual weight cannot substitute; incompatible conditions withheld |
| M10-DRIVING-PASSIVE/v1 | Plateau−total PEEP, cmH2O | Same valid passive zero-flow assessment and pressure datum; present or unassessed spontaneous effort, unacceptable leak or invalid hold withholds; positive difference required; set PEEP/peak/IPAP cannot substitute |
| M10-CSTAT-PASSIVE/v1 | Eligible measured VT mL ÷ eligible passive driving pressure, mL/cmH2O | Same breath/assessment and volume basis, no material leak/effort, positive denominator; this is respiratory-system compliance, not isolated lung compliance |
| M10-MINUTE-VOLUME/v1 | Consistently measured VT mL × total RR /1000, L/min | Explicit matched observation interval and representative breaths; withhold irregular/incompatible averaging or absent measurement basis; source ventilator minute volume stays separate |
| M10-AG-NOK/v1 | Na−(Cl+HCO3), mmol/L | Compatible chemistry specimen, method and units with explicit panel links; no automatic substitution of gas-calculated bicarbonate or total CO2; selected laboratory interval needed for flagging |
| M10-WINTER/v1 | Expected PaCO2 =1.5×HCO3+8, interval ±2 mmHg | Clinician-assessed metabolic acidosis, eligible arterial CO2, explicitly selected compatible bicarbonate and timing, approximate steady-state assumptions; original formula primary evidence pending; never a complete acid-base diagnosis |

Required conversion profiles: explicit %↔fraction; mL↔L; g/L↔g/dL; inches↔cm;
and kPa↔mmHg with a named authoritative conversion constant and decimal precision
review before enabling gas arithmetic. Pressure in cmH2O is not gas partial
pressure in mmHg. Arbitrary raw unit text cannot trigger a conversion. Values
with `<`/`>` are displayed with comparator and withheld from point calculations
unless a separate interval-arithmetic profile has been approved.

Further clinical profiles remain **design-only**, each with an activation owner:

- ARDS definition: selected Berlin or Global 2024 version, onset/risk condition,
  bilateral imaging and alternative explanation assessment, actual modality/flow/
  PEEP context, eligible oxygenation evidence and missing-criterion reporting.
  Never combine partial criteria from different definitions. A P/F number alone
  never diagnoses ARDS; circuit-supported physiology needs specialist scope.
- Oxygen/ventilation targets: apply only an active, patient-specific target with
  validity and documented special-population scope. Exposure outside a target
  requires adequate observation coverage; no continuous-duration claim from sparse data.
- Lung-protection/proning/escalation: separate indication, evidence, contraindication,
  operational readiness and clinician decision. Unknown checks prevent readiness.
  No automatic ventilator settings, prone command, NMBA/steroid/vasodilator/ECMO order.
- Acid-base assessment: pH/CO2/bicarbonate identity, source intervals, expected
  compensation, possible mixed disorders and alternatives, metabolic context from
  M8/M17. Albumin correction, delta gap/ratio and acute/chronic respiratory
  compensation each need exact definitions, sources and population/steady-state
  constraints; no default normal AG or bicarbonate baseline. Stewart approaches,
  A–a gradient, oxygenation index and dead-space indices are deferred capabilities.
- NIV/HFNC/COPD/asthma and post-extubation pathways: indication, actual support,
  contraindication/airway protection, trajectory, tolerance and escalation owner.
  ROX/HACOR or similar scores are not activated by inclusion of their input fields.
- Liberation: selected adult SBT protocol, shared awakening assessment, exact trial
  technique and oxygen settings, assessed outcome, separate airway protection and
  post-extubation plan. RSBI is not an obligatory screening requirement.

## End-to-end workflows

| Workflow | Record and actions | Exit / unresolved state |
|---|---|---|
| First respiratory review | Confirm patient/scope; inspect baseline/home support, airway, goals and actual support; select gas/observations | Explicit missing baseline/targets; recorded assessment with pins |
| Routine patient–ventilator assessment | Review patient effort, support, measured settings, mechanics conditions, interface/airway and humidification | Method limitations visible; no automatic 'safe ventilation' verdict |
| New blood gas | Canonical lab owner records specimen/components, times, quality and sample-time support; validates, previews, appends and reads back | Pending/invalid/unmatched values stay visible but ineligible |
| Compare before/after change | Choose baseline sample, actual change event and follow-up sample explicitly; inspect timing, support and assay comparability | Show measured change and uncertainty; no causal claim from sequence alone |
| Acute deterioration | Reviewer records concern and assessment of patient, signal, airway/device, support, circulation and gas; links urgent clinician review | No generated alarm or guarantee of monitoring; next action owned by clinician |
| Hypoxaemia/ARDS review | Select definition/profile only when activated; assemble imaging, timing, support and oxygenation; inspect missing criteria | Classified only under approved complete profile; otherwise assessment incomplete |
| Hypercapnia/acid-base | Keep arterial/venous labels, inspect current and baseline CO2/pH, timing, metabolic sources and treatment changes | Compensation assumptions and mixed possibilities; no forced single label |
| Proning/rescue | Link indication and specialist plan; document readiness and actual positioning/procedure with response | Incomplete checks or monitoring stay unresolved; no automatic initiation |
| Liberation | Link original M13 awakening, record SBT technique/screen/outcome, then separate extubation assessment and actual transition | Pass alone insufficient; actual support and backup plan retained |
| Transport/handover | Pin selected gas and sample context, last actual support/time, targets/limitations, airway/trials/plan, oxygen supply/monitoring readiness | Original M18 handover owns signature; missing timing/supply is not readiness |

## Current primary-source review and remaining evidence work

Sources below were inspected on 23 October 2026 with ordinary web tools. This is a
focused design check, not a completed systematic evidence library or local protocol
approval. Source provenance and per-profile activation remain mandatory.

| Source | Design implication / limit |
|---|---|
| [AARC current guideline catalogue](https://www.aarc.org/resource/clinical-practice-guidelines/) | Lists patient–ventilator assessment and adult SBT guidance from 2024 and adult oxygen guidance from 2022. The blood-gas document remains labelled 2013, despite a 2025 hosting path. A file upload date does not update the guideline. |
| [AARC patient–ventilator assessment 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11298231/) | Supports patient assessment, VT/PBW documentation, plateau/driving-pressure review, humidification and airway/interface checks. Exact conditions remain part of the chosen calculation profile. |
| [AARC blood gas and hemoximetry 2013](https://www.aarc.org/wp-content/uploads/2025/03/davis-et-al-2013-aarc-clinical-practice-guideline-blood-gas-analysis-and-hemoximetry-2013.pdf) | Supports specimen/site, oxygen flow or concentration, ventilator context, measurement/derived distinction and collection-quality fields. Do not transfer its historical treatment context into present policy. |
| [AARC SBT 2024](https://www.aarc.org/wp-content/uploads/2023/11/CPG2024SpontaneousBreathingTrial.pdf) | Supports recording trial technique and oxygen conditions; RSBI is not necessary as a screening gate, and SBT may use or omit pressure support. Preserve clinician/local protocol decisions. |
| [AARC adult oxygen 2022](https://www.aarc.org/wp-content/uploads/2022/10/cpg-clinical-mangement-adult-o2-acute-settings.pdf) | Supports separate oxygen delivery, HFNC, humidification and patient-population context. This design imports no default oxygen target. |
| [ATS ARDS update 2024](https://escholarship.org/uc/item/5c98w95h) | Retains lung protection/proning context and adds conditional interventions. Record indication, selected guidance and specialist decisions; recommendations do not become automatic orders. |
| [Global ARDS definition 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC10870872/) | Supports definition versioning and nonintubated/resource-context fields. It is a definition consensus paper, not an automatic treatment protocol. |
| [FDA pulse oximeters](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters) | Supports signal and device limitations, including perfusion, motion/context and skin-pigmentation-related accuracy concerns; no race-based numerical correction. |
| [ELSO guidelines catalogue](https://www.elso.org/ecmo-resources/elso-ecmo-guidelines.aspx) | Adult VV respiratory guidance is listed as June 2021; specialist ECMO observation/decision links are in scope, an ECMO management algorithm is not. |

### CHEST, ERS and Indian Chest Society crosswalk

The companion `docs/m9-respiratory/SOCIETY-EVIDENCE-CROSSWALK.json` ties each
source to a proposed interface/workflow requirement and validation scenario.
It distinguishes original recommendation grading systems, current retrieval
limits and clinical profile activation. Do not convert ICS IA/IIA/UPP labels into
GRADE certainty or describe a narrative article as a formal society guideline.

| Source | Bounded implication for this design |
|---|---|
| [ATS/ACCP (CHEST) liberation executive summary, 2017](https://academic.oup.com/ajrccm/article/195/1/115/8498923) | Pair sedation and liberation assessment, record SBT technique, assess extubation risk and preventive support. Cuff-leak testing is indication-specific rather than a universal checkbox. |
| [Official ERS/ATS NIV guideline, 2017](https://www.thoracic.org/statements/resources/cc/niv-guidelines.pdf) | Separate COPD-related acidotic failure, cardiogenic oedema, postoperative failure and post-extubation scenarios. Postoperative assessment includes relevant surgical complications and airway protection. |
| [ERS HFNC guideline, 2022](https://publications.ersnet.org/content/erj/59/4/2101574) | Context and comparator determine the recommendation. Preserve hypoxaemic versus COPD/hypercapnic and postoperative/post-extubation risk groups. Conditional recommendations do not become universal device selection. |
| [Joint ICS/NCCP COPD guidance, 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3775210/) | Indian COPD context supports documented controlled oxygen targets, gas monitoring and NIV reassessment/escalation capacity. Its dated scope must remain visible, and acute targets must not become all-patient or stable home-oxygen eligibility rules. |
| [Indian Chest Society official update](https://www.indianchestsociety.com/messages-for-the-members.php) | Describes new NIV guidelines as ongoing work. The inspected official catalogue did not establish a finalized new NIV guideline; a draft/in-development announcement cannot supply executable recommendations. |
| [ATS NIRS guideline, 2026](https://academic.oup.com/ajrccm/article/212/9/2135/8721554) | Add current comparative evidence to reconciliation: indications and populations remain separate, prompt escalation and monitoring matter, and planned preventive support is distinct from rescue after deterioration. This is ATS guidance, not an ERS/ICS update or endorsement. |

Potential differences must be resolved explicitly before activation. ERS 2022's
conditional device comparisons and ATS 2026's comparison-specific recommendations
must not be combined into 'HFNC is always preferred'. CHEST 2017's initial SBT
pressure-augmentation recommendation and AARC 2024's technique flexibility must
remain attributable; the selected local protocol controls the implemented pathway.
Source recommendation text and figure captions may use different boundary wording;
exact comparison and inclusivity require verification before threshold code.

Every future recommendation entry must carry title/year/DOI/URL, society, document
type, PICO/population/comparator, source wording locator, strength and certainty in
the original system, exclusions, resource/monitoring requirements, update status,
local adaptation owner and rule/test version. The bedside 'Why?' panel shows a
short explanation with source/year; detailed evidence opens separately. A citation
alone never makes an ineligible patient's recommendation applicable.

The user requested Consensus and Firecrawl. Consensus returned its monthly search
limit and Firecrawl returned insufficient credits; neither supplied paper results
for this update. Ordinary web retrieval/search provided the primary sources above.
Full-page access to some ERS/OUP pages was blocked; indexed primary-page content
and accessible society PDFs supported this design review. Exact passages need
full-text reconciliation before enabling clinical thresholds.

Primary ARDSNet protocol retrieval was blocked by the site's robots policy. Do
not describe the PBW formula as newly primary-verified. Primary historical formula
verification for PBW/Winter, a definitive unit constant source, local target/SBT/
proning protocols and condition-specific escalation guidance remain activation
tasks. Published 2026 guidance may differ by society/population; do not silently
replace the selected local protocol with the first search result.

## Proposed implementation seams

Reuse the concurrently added `frontend/src/respiratory/RespiratoryWorkspace.tsx`,
`respiratoryModel.ts`, `respiratory.css`, `RespiratorySources.tsx`,
`RespiratoryEntry.tsx`, `RespiratoryReview.tsx` and focused tests. Do not create a
second respiratory workspace. Keep grouping and eligibility in pure model
functions, independently testable from presentation. Preserve original exact
source inspection/history checks. Extract common pieces only when necessary.

The patient-shell navigation and respiratory review domain have also been added
concurrently. Re-read current diffs before any amendment; do not restore files
wholesale, add another domain or replace another chat's version. No feature flag
should silently equate arithmetic with clinical inference.

R2 requires a contract proposal before transport work: additive models for actual
support observation/change and mechanics; agreed shared specimen/neutral gas
mapping; explicit collection/support relation. Extend source gateway, assembly,
decoder/schema export, exact history and persistence as one coherent feature.
Preserve historical omitted optional fields and old oxygen discriminants. Use a
versioned migration only after separate authorization; no migration is run by
this design. Unsupported incoming records are held with their originals intact.

API names/endpoints for new source types are deliberately not fabricated as
existing services. Their owner must be settled against the current laboratory
integration before R2 implementation. R1 source access continues through the
existing `CirculatoryClient` and shared confirmed state; no alternate patient feed.

## Validation specification

`ACCEPTANCE-CASES.json` is a machine-readable scenario inventory, not executed
product tests. Each case states setup, action and expected invariant. During
implementation turn each relevant case into meaningful model/transport/UI tests.
Arithmetic vectors below are independent expected examples; their correctness
does not validate a clinical indication or enable a profile.

| Case | Eligible synthetic inputs | Arithmetic oracle |
|---|---|---|
| P/F explicit percent | Arterial PaO2 80 mmHg, matched measured/known FiO2 40% | Fraction 0.40; P/F 200 mmHg |
| PBW cm profile | Adult, height 170 cm, explicitly selected male-formula category | 66.016 kg; with VT 396.096 mL, VT/PBW exactly 6 mL/kg |
| Passive mechanics | Valid matched VT 400 mL, plateau 25, total PEEP 10 cmH2O | Driving pressure 15; compliance 400/15 mL/cmH2O; repeating decimal retained to declared precision |
| Minute ventilation | Eligible representative measured VT 500 mL, total RR 12/min | 6 L/min |
| AG without K | Compatible chemistry Na 140, Cl 104, HCO3 20 mmol/L | 16 mmol/L; no high/normal flag without interval |
| Winter approximation | Explicit eligible metabolic-acidosis scenario, chosen HCO3 12 mmol/L | Centre 26, expected interval 24–28 mmHg; no complete diagnosis |

Required suites: source/panel identity and lineage; sample-time alignment; unit
and specimen admission; calculation eligibility/withholding; patient/repository/
cutoff and exact boundary correspondence; stale request/draft/save guards; browser
review persistence limits; accessibility/mobile; shared patient navigation and
M7/M8/antibiotic regression. R2 additionally needs real gateway→database→readback→
history and corrected-source replay tests, including uncertain-write recovery.

Inspect current suite baselines before changes, run focused suites and typecheck,
then appropriate complete shared frontend/backend checks. Separate pre-existing
failures with their baseline evidence; never call an unrun suite passing. Build
both ordinary and configured synthetic modes. Browser-check the actual assembled
synthetic patient screen at desktop/mobile, source/history and scope refresh.

Release claims must include inspected source identity, files changed, command exit
codes, actual counts, build modes, browser evidence and remaining unconnected or
staged features. A passed test count, a clickable mockup or a build alone does not
establish clinical readiness, durability or monitoring coverage.

## Decisions remaining and approval boundary

The proposed R1 follows the existing stack and requires no new dependency or
external service. It deliberately displays unconnected advanced workflows without
pretending they are implemented. R2 source ownership, deployment/migration and R3
clinical activation are separate decisions; they do not block the R1 source-review
screen after design approval.

The user approved this supplemental bedside layout and its safety/evidence requirements on 23 October 2026. The four-panel overview is integrated into the existing respiratory workspace, retaining its source, history and specialist flows. Clinical activation and production deployment remain separate work. Verification is recorded in docs/m9-respiratory/IMPLEMENTATION-VERIFICATION.json.

The user subsequently clarified the shared-workspace objective: enter or import once, inspect earlier values and trends, see renal, respiratory, circulatory and medication context, and complete a review without repeated entry or a reuse-for-assessment step. A combined screen and passing engineering tests do not by themselves satisfy that complete clinical workflow. M7-C remains gated; M9 remains in progress until the outstanding workflow and clinical validation gates are resolved.
