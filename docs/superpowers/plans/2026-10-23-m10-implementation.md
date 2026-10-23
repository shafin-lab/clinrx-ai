# M10 implementation plan

> **For agentic workers:** Use superpowers:executing-plans for integration and superpowers:dispatching-parallel-agents for independent files. Steps use checkbox syntax.

**Goal:** Implement the approved M10 transfusion, coagulation and viscoelastic design in the connected ClinRx app and verify the full synthetic workflow.
**Architecture:** Isolated clone of the current candidate plus its uncommitted M9 source snapshot; dedicated M10 typed records, repository transactions and gateway; shared patient evidence and independent assay/protocol registry. Root owns integration; workers own separate backend, interpretation and UI files.
**Tech Stack:** Existing Python/Pydantic/FastAPI/SQLite, React/TypeScript/Vite/Vitest. No new dependency required.
**Spec:** ../specs/2026-10-23-m10-transfusion-design.md and its device/evidence companion.

## Global constraints
- Never write to connected-overview-candidate, its databases, previews or M9/director-review work. All edits use clinrx-m10.
- Baseline 4f601a3 preserves candidate a26ac43 plus active M9 changes. Source manifest: review-evidence/m10/baseline-source.json.
- Native worktree creation returned 'Not a git repository' because the chat root contains the nested candidate. Use the isolated local clone; no shared index or branch with M9.
- Original sources are read-only. Synthetic isolated databases only. Dedicated preview port 5260, checked free before launch. No process restart outside this task.
- Original reports/assays, unavailable values, product attributes and dose/count bases remain explicit. No unreviewed clinical threshold gets represented as clinically approved.
- User authorised implementation and full verification; proceed without repeating design or execution approval questions.

## Review focus
- Aggregate and individual-unit overlap must never create a false received total.
- Corrected/late results and partial VET updates must preserve historical knowledge cutoffs.
- Factor concentrates are medication exposures; dose, vials and volume are independent.
- Foreign scope, uncertain response retry and stale corrections must never create another delivery.
- Device/cartridge mismatch, unfinished lysis and absent clinical context must not generate plausible unsupported advice.

### Task 1: Source isolation and baseline
- [x] Capture source snapshot and independent branch.
- [x] Run existing affected M9/frontend and backend baseline tests; preserve results and documented existing failures.
- [x] Read-only backup original synthetic database and preserve row/hash evidence; do not migrate original.

### Task 2: Typed M10 storage, lifecycle and accounting
Files: backend/app/models/clinical/transfusion.py, backend/app/services/transfusion_service.py, backend/app/demo/transfusion_gateway.py, explicit existing persistence registries/migrations, tests/test_m10_*.py.
Interfaces: dedicated M10 gateway exports M10 base path and SyntheticM10Gateway; GET catalog gives repository/patient/encounter/cutoff, typed evidence items, totals and completeness; POST validate/lookup/save binds request ID and payload; POST history resolves bounded immutable sources. Publish exact request/response contract to frontend workers before integration.
- [x] Write red tests: product modifications/quantities, partial/not-given, duplicate replay, source correction, foreign patient, historical eligibility, aggregate overlap, fluid link, VET progression.
- [x] Implement typed source owners with append-only persistence and command recovery; reference existing labs/medications/fluid sources.
- [x] Run green focused tests and migration preservation checks on disposable databases.

### Task 3: Device and clinical interpretation registries
Files: backend/app/services/m10_interpretation.py, backend/app/services/m10_profiles.py, tests/test_m10_interpretation.py, knowledge/m10/.
Interface: device_profiles() returns JSON-safe inventory; interpret(payload: dict) -> dict with findings/options/withheld, exact source/profile references, input-context decisions. Registry independent of source persistence. Root routes HTTP evaluation.
- [x] Write red tests for every core device configuration, assay/channel masks and no cross-device substitution; pending/invalid/comparator/unknown results withhold affected outputs.
- [x] Research exact primary sources without Firecrawl, implement deterministic sourced pattern/option profiles and explicit verification/activation states. Coverage targets follow design section 8.
- [x] Verify positive, no-option, boundary and missing/conflicting context cases. Retain clinical activation limitations accurately.

### Task 4: M10 workspace and editors
Files: frontend/src/transfusion/*, frontend/tests/transfusion*.test.tsx.
Interface: TransfusionWorkspace props {catalog, requested, current, loading, error, onRefresh, onGuardChange}; a dedicated M10 transport injected or defaulted, shared existing catalog used for labs and source references.
- [x] Write red interaction tests: enter and review product, quantities/modifications, reload/recovery, inspect/correct/history, VET form all profile outputs, interpret and save assessment, source-linked lab/calcium.
- [x] Implement five views in the existing visual system: products, labs/calcium, TEG/ROTEM, interpretation/plan, bleeding/reactions/reassessment. Label synthetic state, incomplete totals and unsupported profile states truthfully.
- [x] Green tests; current-context and navigation guards preserve drafts and block stale saves.

### Task 5: Shared app integration and isolated preview
Root owns frontend/src/demo/PatientWorkspace.tsx, PatientOverview.tsx and API integration, shared schemas as necessary, tools/m10-preview scripts and browser verification.
- [x] Add M10 navigation and summary using shared patient/review controls; preserve all M9 components and hooks.
- [x] Bind typed transport and server evaluation; verify full source roundtrip and immutable original history.
- [x] Build versioned M10 assets; launch dedicated preview against copied synthetic patient DB.
- [x] Verify browser workflow from overview to product entry, VET and interpretation, correction/reload/history and reassessment; inspect rendering.

### Task 6: Regression, review and handoff
- [x] Run whole frontend and backend suites against isolated code. Record named failures and distinguish baseline from introduced failures.
- [x] Independent whole-change review; resolve material findings with regressions.
- [x] Confirm original data hashes/rows and original running preview untouched. Check M9 source changes read-only; produce explicit merge/integration notes instead of overwriting active work.
- [x] Commit M10 source, report tested coverage/remaining clinical activation requirements and isolated preview URL.
