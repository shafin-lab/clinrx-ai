# Connected antibiotic patient workflow candidate

Reference: local prototype at http://127.0.0.1:4173. Implemented in the existing
connected-overview candidate; original accepted checkout and live app remain unchanged.
New preview: http://127.0.0.1:5236/?workspace=antibiotics.

## Connected behavior

- One shared RF2/M7/M8/M6 composition uses the exact same repository cutoff and review
  period. The overview includes the patient's antimicrobial and susceptibility sources.
- Manual prescriptions record the exact product, dose, unit, component/basis, route,
  source schedule, indication, time, actor and original prescription/MAR identifier.
  Actual administrations are separate completed assertions. Held/missed/refused/not-given
  events have no administered amount; optional exact prescription links are checked.
- Validate and review precede an explicit save. Source records append through existing M6
  typed contracts and repository transactions. Same-command retries are idempotent;
  duplicate source identifiers within a source kind are rejected across stable identities.
- Corrections append an owned successor with exact predecessor/digest and reason;
  stale predecessors conflict. Full original revisions remain available in source history.
- Pending writes are saved before dispatch in versioned repository-scoped local storage.
  Reload requires exact lookup before any retry. A confirmed save and a failed overview
  refresh are distinct states. Corrupt or concurrent recovery bytes are preserved.
- Cockcroft–Gault calculation requires explicit adult age, equation sex coefficient,
  selected/manual weight, weight basis and serum creatinine (mg/dL). Source choices come
  from this patient's catalog. Inputs are blank until selected. Changing renal function,
  unknown assessment or kidney support limits applicability; this is not CRRT clearance.
  Evidence refresh invalidates the displayed calculation.
- The same antibiotic module has a separate, opt-in adult renal-dose suggestion review.
  It requires exact medicine, supported indication, route/infusion, initiation/maintenance
  stage, routine body-size applicability, hepatic and safety review, and either a selected
  final source AST for that same medicine or explicit empiric-choice review. A supported
  non-dialysis row requires a fresh calculated Cockcroft–Gault estimate and clinician-
  assessed stable function. HD/CRRT rows are selected by their own support settings; CrCl
  is not used to derive a dialysis dose.
- The first source-matched candidate set is limited to cefepime, meropenem,
  piperacillin/tazobactam, ceftriaxone, cefazolin, ampicillin/sulbactam and ciprofloxacin.
  The recommendation shows its source and scope. Available external guidance is not local
  policy, and the included candidates do not cover every product, indication or regimen.
  SLED/PIRRT, peritoneal dialysis, CVVH, CVVHDF, unsupported flows, interruptions, unstable
  kidney function, uncertain context and profile gaps return a hold. The candidate CVVHD
  set matches only its source's 2 L/h and residual native GFR <10 mL/min assumptions.
  Ceftriaxone CRRT has no loaded match and is held.
- “Use in a prescription draft” is a separate explicit action. It copies the source-based
  amount/route/schedule to the editable prescription form but leaves product/formulation
  blank and does not validate, save, administer or transmit a medication order.
- Culture review displays final source-reported S results with exact isolate/specimen links
  as options for clinician review. R and I are not offered as susceptible options. Missing
  standard/edition, unresolved drug mapping, preliminary/incomplete results, missing
  parents, conflicting reports and positive resistance markers withhold an option.
  This neither diagnoses infection nor selects/ranks a regimen.

## Boundaries

The imported numerical source library remains Unreviewed and non-executable. The separate
candidate profiles are a small direct transcription of current UCSF IDMP adult dosing
pages, not a reuse of that library and not a local hospital protocol. Profiles are versioned
in `renalDoseModel.ts`; sources and links are visible with each result. No hard-coded
prototype patient demographics, cultures or administration history were imported into the
patient workflow. The independent test database has explicitly fictional p1/e1 cultures
and MAR records to exercise the workflow.

The full candidate test backend uses SyntheticAntibioticGateway on loopback with a fixed
synthetic database, exact origin checks, no-store responses and clinical execution disabled.
The current preview uses `review-evidence/antibiotic-workflow/static_preview.py`, a
read-only fixture fallback that serves only the fixed synthetic evidence bundle and rejects
POST writes. Normal production routes do not expose either candidate server. Neither path
physically administers a drug or sends a prescription to a hospital system. Exact
product/formulation, component basis, patient-specific pharmacology, local policy,
allergy/interaction checks, therapeutic drug monitoring and clinician/pharmacist validation
remain required before recording an actual prescription.

Equation reference: https://www.hepatitisc.uw.edu/page/clinical-calculators/crcl.
