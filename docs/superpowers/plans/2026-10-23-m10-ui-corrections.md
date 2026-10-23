# M10 product and assay presentation corrections

Execute the user's concrete corrections in the isolated M10 checkout, using Superpowers TDD and the user-authorized Superpower Review chat. Preserve existing patient sources, M9, immutable source owners and clinical thresholds.

The design adds seven obvious product shortcuts and a per-product known-subtotal table. PRBC processing attributes stay separate. Confirmed saves offer a fresh next administration; no source identity, quantity or processing attribute is copied. Reuse the existing source laboratory editor. Group report and entry fields by exact assay and selected cartridge, with missing parameters explicitly unreported. Keep unsupported source extensions intact.

A batch API was considered but is unnecessary: independently recoverable commands already allow any number of administrations. No atomic batch is claimed. UI changes, command payloads and the exact seven-product example will be tested.

- [x] Write and observe failing product, repeat-entry, lab-only and grouped-assay regressions.
- [x] Implement product shortcuts, known-subtotal table, separate modifications and clean repeated entry.
- [x] Implement cartridge-aware assay sections for capture and display; reuse manual source lab entry.
- [x] Resolve Superpower Review findings, including prevention of silent medicine-dose relabelling.
- [x] Run full frontend and relevant backend workflow tests, typecheck and build.
- [x] Obtain final review, refresh only preview5260, verify browser workflow and original data preservation, commit corrections.


## Completion evidence

Implementation checkpoints: `3bbb72c` (product/assay workflow), `9353f24` (original M9 haemoglobin owner), `3cd6903` (request/disposition unit coherence). Superpower Review independently inspected the cumulative source changes and closed both material follow-up findings; report: `review-evidence/m10/superpower-ui-corrections-final-review.md`.

The full interface suite passed 1,188 tests, with three opt-in live cases skipped, before the final SDP/Hb/source-unit follow-ups. After those narrow changes, all 55 focused M10 interface/client/integration cases passed. The relevant backend run passed 25 cases, including the user's exact seven-product quantities. The real M10 client passed validation/save/replay, two PRBC episodes totaling10, all seven simultaneous product subtotals, correction/restoration and three-revision history on a separate disposable database. Final TypeScript checking and production build passed (`preview-20261023T075135Z`). Existing chunk-size advisories remain. After the main/M9 run finished and the lane was released, the full final interface suite was rerun on the final source tree: **1,194 passed, three opt-in live cases skipped, zero failures**, in91.64seconds (`ui-corrections-full-final.log`). The final focused55 tests and build also remain green.

Browser verification confirmed plain PRBC with separate leukodepleted/irradiated assertions, the seven-product table with all supplied quantities, the source laboratory editor and shared results including original M9 haemoglobin10.2g/dL, and separately named CK/CRT/CFF report sections. TEG6s GH/Lysis/HN masks and ROTEM EXTEM/INTEM/FIBTEM/HEPTEM separation are also covered by focused tests. No clinical profile thresholds or backend accounting semantics changed.

Existing-patient preview: http://127.0.0.1:5260/?workspace=transfusion
Disposable synthetic seven-product example: http://127.0.0.1:5261/?workspace=transfusion
Screenshot: `review-evidence/m10/seven-products-preview.jpg`.

The original database hash still matches the captured baseline; all171 original fact rows and two links remain identical subsets of the intact M10 copy. The existing M10 copy still has180 facts/three links: this correction work did not seed the seven-product example into that patient. Original main/M9 sources, data and preview processes were untouched. Only this task's5260/5261 servers were refreshed. Source, tests and this plan are committed; runtime databases, keys, reports and screenshots stay local and ignored.
