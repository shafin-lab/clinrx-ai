# Assisted synthetic reassessment — MAP 63.0000

Local b419444 workspace, 127.0.0.1:5195. New separate note
00234d1d-b5ff-47da-a702-e6f50918056f/1 is confirmed at ingestion 167.
Its fictional case source time is 2026-10-08T09:30:00Z; provenance records
actual authoring time separately. Actor label is Synthetic demo operator (assisted),
not an authenticated clinician identity.

Exact selections: fs-CO-15/1, fs-N-CHANGE/1 and
fs-MAP-15/915ae2cb-99f9-47e6-883e-9fc51725a7f0.
The earlier 09:25 note 3583c95b-119c-4daf-9642-42845112602e/1 retains
fs-MAP-15/41675deb-aa68-444f-a5fe-6ed8770c2c0c (62.0000).

Actual before/after SQLite checkpoints pass integrity and all-12-table comparisons.
All 166 prior fact rows and both retained receipts are unchanged. Only one root
note and expected sequence counter are added; revision links do not change.
Validated review, saved DOM and viewport JPEG are retained. This is assisted normal
flow, not an uncoached user exercise, new build/test or container validation.
No raw API/network trace was captured. Screenshot is a viewport, not all fields.

The initial data-only verification assertion omitted the serialized null
longitudinal_context_id in its expected scope; the verifier now checks the complete
scope including that null. This was a verifier-shape correction, not an application
save failure or another write.

HPI remains optional. Production execution remains disabled; nothing merged,
deployed, externally hosted or published. No new source changes/additions.
