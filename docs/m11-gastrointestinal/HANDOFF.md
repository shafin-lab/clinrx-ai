# M11 GI/liver first increment — handoff

General GI/liver review is implemented in the existing ClinRx patient workspace. It is a local synthetic candidate, not a clinical deployment or a GitHub merge. The original preview and patient stores remain intact. See SPEC.md for the approved boundary and the implementation plan in docs/superpowers/plans/2026-11-04-m11-gi-liver.md.

## Clinician workflow

Open **Gastrointestinal & liver** in patient navigation. Overview shows source-recorded symptoms, examination, stool/output and feeding tolerance beside latest and earlier liver results. Results & trends includes explicitly mapped bilirubin fractions, AST, ALT, ALP, GGT, albumin, protein, amylase and lipase, plus shared coagulation results where supplied. Missing INR remains Not recorded in the fictional case. Distinct samples remain separate; corrections retain predecessors.

Imaging & procedures shows original abdominal reports, including earlier ultrasound/CT and their limitations. Source & history exposes exact source identity, timing, specimen, mapping, provenance, qualifiers and correction history. Record finding captures an original GI observation/report once; shared assays use the existing laboratory entry, not a separate GI lab store. Relevant findings appear automatically in Patient overview. Feeding tolerance remains one shared source for future Nutrition reuse. Medication, renal, fluid and circulation context is available through the established shared patient context.

Review & plan saves one clinician-authored assessment against exact evidence pins. Reload restores it in the same browser. Relevant source/revision/context change makes it historical, including same-value amendments. A newer unrelated global watermark alone does not force reassessment. Pending save lookup/retry keeps exact payload ownership; a second editor cannot overwrite it. Definite rejection permits editing and an unreadable journal is preserved while replacement writes remain blocked.

## Evidence and verification

Initial implementation checkpoint6046dad received independent read-only review. Six Important findings were corrected in one regression-led pass: pending owner races, pin validation, source metadata preservation, rejected-save/modal recovery, censored comparators and primary source qualifiers. No Critical findings. There was no second independent review after corrections; final assurance is the regression-led full verification and desktop walkthrough.

Final frontend:1784 passed /3 pre-existing skips; typecheck and normal/configured builds passed. Backend:4556 passed across four disjoint groups covering the complete collection, after updating explicit legacy schema-head/type-registry expectations. Existing warnings: large frontend chunks and Starlette httpx deprecation. Whitespace check passed. Dependencies were reused from the existing pinned workspace; no fresh dependency installation is claimed.

Seven protected databases match baseline SHA256 and pass integrity. Two protected original builds each retain all188 files unchanged. Additive m11_0012 migration was applied only to copied/test databases. The served demonstration uses a compact acceptance-fixture backup with fictional GI sources; the earlier larger respiratory copy hit the existing combined antibiotic response limit and is preserved as a failed fixture. Response limits were not widened.

Local evidence is preserved under review-evidence/m11-gi-liver-20261104 (ignored from version control): full test receipts, aggregate backend coverage, migration/copy checks, pre/post preservation, RED/GREEN regressions, desktop snapshots, independent review summary, launch/runtime information and final build/source manifest. The preview is on loopback port5293 using a separate database and static build. Existing5290/5291/5292 previews were not replaced.

## Limits and next work

This increment records/reviews evidence. It does not generate diagnoses, severity scores, treatment advice, dosing, orders or image interpretation; PACS/hospital integration is future work. Browser review storage is not an authenticated durable shared audit. Mobile, native multi-tab browser testing and actual browser response-loss injection remain unverified; controlled ownership/recovery and gateway tests cover the bounded cases. No specialist GI completeness or clinical readiness claim is made. No GitHub push/merge is included in this task.
