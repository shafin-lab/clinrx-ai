# Antibiotics module handoff for ClinRx main work

This handoff collects the completed antibiotics-module work from the `antibiotic clinical appropriate` chat so it can be integrated with the active M7/M8 ClinRx work in the `ClinRx main work` chat.

## Source workspace

`/Users/mohammedshafiqshajahan/.codex/.chatgpt-projects/g-p-6a7341f8cd3c8191b8bc642d3c0a06e6/clinrx-antibiotics-prototype/`

Local preview (while its dev server is running): http://127.0.0.1:4173/

## Completed work to carry forward

- Patient-context antibiotic review with a contextual evidence drawer, searchable library, drug catalogue and culture-oriented entry points.
- WHO ATC-based worldwide catalogue containing 382 medicine identities, with explicit scope/completeness limits and an unlisted-medicine review path.
- 26-source evidence library centered on Indian national guidance and official labels, with international sources identified by jurisdiction and version.
- Drug-specific national-guidance cards for all catalogue identities, including indication mentions, renal/CRRT status and monitoring where the source supports it.
- Supplemental renal/CRRT references and explicit gaps for 382 identities. The current generated coverage reports 67 medicines with a renal reference and 62 with a CRRT reference.
- Latest ICU-priority CRRT additions from a 2024 consensus: limited CVVH cefoperazone/sulbactam guidance, teicoplanin loading/maintenance with level targets, and an amikacin TDM strategy without a fixed maintenance schedule.
- Source cards expose provenance, jurisdiction, exact version, route/product scope, assumptions, locator and retained-capture checksum where present.

## Key implementation files

- `src/App.jsx` — antibiotic workflow and evidence-library integration.
- `src/AntibioticDosing.jsx` — patient-context review and evidence-drawer entry points.
- `src/EvidenceLibrary.jsx`, `src/LibraryReviewWorkspace.jsx` — library browsing and return-to-patient-review workflow.
- `src/AntibioticCatalogue.jsx`, `src/DrugGuidance.jsx`, `src/NationalDrugGuidance.jsx` — catalogue and guidance views.
- `src/SupplementalRenalGuidance.jsx` — supplemental renal/CRRT source cards.
- `src/data/antibiotic-catalogue.json` — medicine identities.
- `src/data/antibiotics-evidence.json` and `src/data/guidance-references.json` — evidence-library/source entry points.
- `src/data/drug-specific-guidance.json` — per-medicine national guidance coverage.
- `src/data/supplemental-renal-crrt.json` — supplementary renal/CRRT cards.
- `AGENTS.md` — durable prototype decisions and clinical boundaries.
- `evidence/` and sibling `clinrx-antibiotics-evidence-library-20261021/` — source captures and audit material.

## Required integration boundaries

All imported sources, summaries and dose references remain **Unreviewed**, clinically ineligible and non-executable. Keep them separate from dose calculation, treatment selection, patient/session decisions and prescribing. Do not transfer a native-renal or intermittent-HD schedule to CRRT; keep product/component units and each modality/flow assumption explicit. Do not treat a national or foreign institutional reference as the receiving hospital's approved policy or antibiogram. Preserve explicit unsupported/gap states and the source's jurisdiction, version and review state.

## Integration status

The work is complete in the prototype workspace; it has not yet been copied into or wired to the main ClinRx application. The main-work chat should inspect this source workspace and the current M7/M8 implementation, then integrate the antibiotic evidence feature using the main application's existing contracts and UI. Preserve in-progress M7/M8 changes. Do not push or publish without the user's instruction.
