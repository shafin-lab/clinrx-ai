# M9 Respiratory and ABG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Connect the agreed respiratory domain to the existing patient workspace with append-only source records, physiology, shared investigations and saved reviews.
**Architecture:** A new typed record owner extends the RF2 shared catalog; no original records are cloned. Existing observations, laboratory reports and microbiology remain owned by their current domains. Pure physiology consumes coherent, exact sample/measurement sets.
**Tech Stack:** Existing Python/Pydantic/SQLite, React/TypeScript/Vitest. No new dependencies.
**Spec:** docs/superpowers/specs/2026-10-23-m9-respiratory-design.md

## Global Constraints
- Preserve sources/, existing dirty changes, port5238, original SQLite DB and browser reviews.
- New migration is exercised only on disposable test DBs and copied candidate DB.
- Use user-approved revised numbering M8 combined renal/fluid, M9 respiratory.
- No production routes, deployment, clinical execution or automatic treatment orders.

## Review Focus
- Historical review before a correction must use the last already available revision.
- Unrelated/venous/censored/flagged gas results cannot yield arterial oxygenation calculations.
- An uncertain entry retry must submit identical bytes; refreshing evidence cannot silently rebase a correction.
- Navigation, patient identity, cutoff and queued storage locks cannot attach a review to different evidence.
- Broad report coverage must not imply unsupported advanced interpretation or planned treatment delivery.

### Task 1: Respiratory typed storage and shared catalog
Files: backend/app/models/clinical/respiratory.py; backend/app/services/respiratory_service.py; respiratory migration; existing persistence and RF2 owner/catalog; tests/test_respiratory_contract.py; tests/test_respiratory_gateway.py; tools/export_rf2_transport.py.
Interfaces: RespiratoryRecord per spec; `RF2Service.save_respiratory_record(repo, repository, record)`; RF2 `POST /respiratory` body `{repository, record}`; catalog `respiratory_records: Evidence[]` at same cutoff. Existing resolve/history accept exact respiratory pins.
- [ ] Write and run failing typed/persistence/API tests (invalid patient, exact source identity, replay, correction, future availability and historical cutoff).
- [ ] Implement bounded typed storage, migration and API; regenerate RF2 schema.
- [ ] Run focused tests and migration checks against isolated DBs. Expected PASS, no original DB write.

### Task 2: Respiratory physiology
Files: frontend/src/respiratory/physiology.ts; frontend/tests/respiratoryPhysiology.test.ts.
Interfaces: `calculateRespiratoryPhysiology(record: RespiratoryRecord): PhysiologyResult[]`; each result `{id,label,value:string|null,unit,formula,reason,inputs:string[]}`. Use shared respiratoryTypes.ts. Existing gas records are adapted to explicit sample sets by model, not by this function.
- [ ] Write failing numeric and withholding tests for oxygenation, ventilation, mechanics, acid-base and oxygen transport.
- [ ] Implement explicit methods and valid-input gates; include source URLs/version in exported method metadata.
- [ ] Run focused physiology tests. Expected PASS, unsupported inputs explain withholding.

### Task 3: Shared respiratory review and entry
Files: frontend/src/respiratory/{respiratoryTypes,respiratoryCatalog,respiratoryModel,RespiratoryWorkspace,RespiratoryEntry,RespiratorySources,RespiratoryReview,respiratory.css}; frontend/src/api/rf2Client.ts; savedReviewStore; PatientWorkspace; PatientOverview; frontend/tests/respiratoryWorkspace.test.tsx; frontend/tests/respiratoryTransport.test.ts.
Interfaces: optional catalog.respiratory_records for retained fixture compatibility, new responses always provide it; `RF2Client.importRespiratory(repository, record)` validates exact response; workspace consumes shared catalog/micro state and refresh callback, no parallel unbounded fetch.
- [ ] Write failing transport/model/UI tests for source reuse, all category entry, physiology display, stale state, current-vs-historical reviews, reload and queued locks.
- [ ] Add category templates, exact source/history view and guarded explicit entry confirmation/retry.
- [ ] Connect overview/navigation and M9 local review storage; preserve existing domain keys.
- [ ] Run affected frontend tests and typecheck. Expected PASS.

### Task 4: Verification and separate preview
Files: docs/consolidation/PLAN.md; review-evidence/m9-respiratory/ (ignored).
- [ ] Run maintained frontend/backend suites with controlled resource use; report named failures and fix new regressions.
- [ ] Fresh whole-change review; fix consequential findings with regression tests.
- [ ] Build unique assets; migrate a copy of the preserved patient DB; verify all171 source facts and existing antibiotic non-delivery survive.
- [ ] Populate only a second disposable verification DB with representative gas/support/imaging/culture/specialist records; verify UI and source correction/reload flows.
- [ ] Launch the unpopulated patient copy with M9 at a separate loopback port; keep original5238 running.
- [ ] Check original DB SHA256/integrity and source-manifest preservation; update handoff and deliver preview link and actual verification limits.
