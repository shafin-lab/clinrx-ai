# M9 Respiratory and ABG

The user approved the complete respiratory scope in this conversation and explicitly requested implementation on 23 October 2026. Roadmap: M8 combines renal/CRRT/fluid balance/output; respiratory is M9, coagulation M10, devices M11, sedation M12, nutrition M13, infection control M14, neurology M15, endocrine M16, discharge M17. Older files retain historical numbering.

## Intent
One patient respiratory workspace reusing existing blood gases, bedside observations, chemistry, cultures, medications and source history. Capture and review acute, chronic and specialist respiratory evidence; distinguish recorded data, clinician reviews and calculated physiology. Preserve all pre-existing work and patient records.

## Approach
Extend the existing shared catalog with a typed append-only respiratory record owner. Use the current feature checkout, a source archive, immutable prior builds and an isolated database copy; preserve port 5238 and its original database. A disconnected respiratory demo would lose source reuse; importing every measurement into a generic untyped note would lose safe calculation boundaries. Implement the accepted connected approach using existing Python/Pydantic/SQLite and React/TypeScript, without new dependencies.

## Data contract
`RespiratoryRecord` extends RecordedFactV2, kind `respiratory_record`.
- category: bedside, support, blood_gas, mechanics, imaging, procedure, treatment, liberation, lung_function, sleep, extracorporeal, assessment.
- source_identity: LaboratorySourceIdentity; owner `resp-` + first 32 hex SHA256(issuer_namespace + NUL + source_report_id), revision = source_version.
- title: original source title; times: occurred, collected, reported, available (RecordedTime).
- context: sample_type (arterial, peripheral_venous, central_venous, mixed_venous, capillary, noninvasive, unknown), specimen_id, collection_site, oxygen_device, ventilator_mode, airway_id, position, population (adult, child, neonate, unknown), settings_confirmed_at_sample (bool|null), passive (bool|null), occlusion_confirmed (bool|null), reference_equation (str|null). Optional text fields default null.
- measurements: 0..128 items with unique concept, label (source display), result (LaboratoryResult), role (measured, set, reported, calculated_by_source, unknown), quality (usable, suspect, unknown), method (str|null). Concept is an explicit identifier, never inferred from label. Unknown concepts stay displayable without calculations.
- narrative: original report text, nullable; report_status: pending/preliminary/interim/final/corrected/withdrawn/cancelled/unknown; change_state: original/amended/corrected/superseded; record_status: recorded/withdrawn/invalid/unknown.
- linked_sources: exact Reference array (max32), validated against same patient repository at admission. Corrections preserve category, source identity and original exact evidence; no silent replacement.
- available/report time bounds visibility. If a correction is later than review_end, the last revision already available at review_end remains the visible source, with later correction history excluded at that historical view.

## Coverage
Bedside respiratory assessment; oxygen/HFNC/NIV/invasive support; airway/interface; measured and set ventilator parameters; ABG/VBG/capillary gas/co-oximetry; source-linked chemistry and other labs; oxygenation/ventilation/acid-base/mechanics/oxygen-transport calculations; radiology/ultrasound/bronchoscopy/pleural/pathology reports; existing microbiology and AST; treatment/procedure actual-vs-planned context; liberation readiness and actual trials/outcomes; spirometry/volumes/DLCO/muscle tests; sleep/home support; ECMO/ECCO2R and advanced respiratory measurements. Data-entry templates must support these categories and original narrative, not claim automatic interpretation of all specialist tests.

## Physiology boundary
Calculations are pure, versioned and input-explicit. Numeric unit conversion is restricted to supported exact units. No venous PO2 becomes PaO2, no oxygen-flow-to-FiO2 estimation, no later setting replaces sample-time context, no peak pressure becomes plateau, no actual weight becomes predicted body weight. Duplicate, censored, withdrawn, suspect, wrong-population or incompatible-unit inputs withhold affected outputs. Advanced tests preserve reported values and method/reference-equation details; absent protocols do not become adult defaults. Calculated explanations are not treatment orders or automatic disease diagnoses.

## Workflow
Respiratory view in main navigation and overview, tabs for respiratory course, blood gases/physiology, investigations/infection, airway/treatment/liberation, specialist function/support. Source cards open exact record/history. Add respiratory information enters structured original evidence or corrects a selected record; explicit review precedes append and exact request is retained for retry after uncertain response. Shared labs/cultures are displayed through their existing owners. Clinician M9 reviews reuse browser-local append-only Web Locks storage, with latest-render identity check at lock acquisition, and survive reload; this remains a same-browser synthetic preview store.

## Verification
Tests for persistence/retry/correction/scoping/cutoff/migration, no cross-domain assembly leakage; transport hash/schema validation; pure physiology numeric and withholding cases; all category entry/review/source-history paths; stale queued saves and reload; overview integration and preserved original DB hash. Build versioned assets and launch isolated copied-patient preview. Never modify sources/ or write synthetic test entries to the original database. Existing mobile and prior test qualifications are recorded, not falsely resolved.
