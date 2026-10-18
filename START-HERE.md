# Accepted db56f7e build — local workspace update and comparison evidence

Application reference: `db56f7e8164a7a3c46c6c8e17a56c0d9088c2de5`  
Tree: `a60dedfbb8e4f7ecfb82ad8467e3895cde36372b`

Scope: implementation-operated installation of the previously accepted authoring frontend on local 5191, followed by normal read-only note comparison. No source change, fresh build/test, inference execution or stored-evidence append. Preserve Director C1 closure and prior bounded walkthrough/R1/F1/F2 acceptance; this supplement requests bounded runtime-update/capture correspondence review only.

## Original artifacts

All eight original files plus their original SHA256SUMS.json are unchanged under original/:
- update.json: source/tree, exact three build hashes and preserved prior frontend path.
- browser-resources.json: script and stylesheet paths observed in browser DOM after reload.
- comparison.jpg: exact note/reference table columns together; matching JPEG extension.
- comparison.txt: complete DOM with explicit A/B selections and Clinical execution disabled.
- before-rows.json / after-rows.json: actual read-only all-table exports around the frontend update/viewing.
- verification.json / README.md: implementation-produced checks and capture attribution.

The previous ebbab29 frontend was preserved at the path named in update.json. Corrected frontend bytes were copied from the accepted C1 authoring build into the existing service's frontend directory, then the browser was reloaded. Backend/service/database were reused without restart or migration. Prior-build preservation and installation are implementation-reported actions, not an independently witnessed filesystem trace.

## Build correspondence

reference/accepted-build contains exact reused HTML/JS/CSS bytes from the previously accepted C1 evidence, e9c06894f28664c45776b83c5efaf5e896ed0887. These are NOT a new build or freshly fetched browser resource bodies. Their hashes match update.json. HTML and observed script path identify /assets/index-mUqGSKu2.js; stylesheet is /assets/index-CVDetElB.css. This supports build-byte/path correspondence, not complete authenticated resource-load or browser-to-DB proof. Installed-file equality was checked during the walkthrough; no separate installed-directory binary snapshot was captured.

Earlier C1 source/validation: https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252626356

## Captured comparison

Note A: circulatory_event / abae4ef7-74c4-48cc-bb50-f50e9fb151cd / 1 at 09:50 UTC; exact follow-up circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / 1.

Note B: circulatory_event / 90c89b62-1f3a-4903-b10d-eb8c6711e921 / 1 at 09:55 UTC; same oxygen fact ID, revision aeaca128-a674-4dfa-859a-9ab11d2a9368.

Baseline a02f88e1-db04-48a0-89e6-f236016a38a8/1 and intervention 99a26724-026c-4ccc-ac63-c22ddada2664/1 remain exact in both. The table preserves references, not newly loaded measurement values. Full narratives/provenance remain collapsed in this new capture. Earlier expanded-note captures retain their original source and cannot be relabelled as db56f7e browser evidence.

Screenshot shows both table columns, not full authored narratives or the disabled header; top selector is partly clipped. Disabled execution is visible in the complete DOM, not established by a fresh independent health/gate probe. No live duplicate-member injection/adversarial browser case or broad device/touch/accessibility certification is demonstrated by this normal flow. C1's regression execution stays attributed to the prior accepted package.

## Data preservation and access

Before/after raw exports are byte-identical across 12 tables: 174 fact revisions, two receipts and prior notes/references unchanged. They also match the earlier c967cc after-export. No fresh SQLite binary checkpoint was saved. A final SQLite integrity check is implementation-reported in the original README, without a separate raw integrity log. TABLES-INDEX.json links readable per-row mirrors; column labels come from the earlier preserved SQLite schema, not a newly captured schema/checkpoint.

Original/publication manifests, bounded lossless base64 mirrors in MIRRORS.json and stdlib data-only verify_publication.py permit direct review without ZIP or Mac access. The verifier does not execute application/tests. No new suite, hosted CI, backend run, container/restart acceptance, authenticated network trace or clinical readiness is claimed. Original capture-time no-publication wording is superseded only by this separate evidence publication.

Production connected execution remains disabled. PR #23 application head is unchanged, draft/open/unmerged. No merge, deployment, external hosting or gate activation. Durable browser-session recovery remains deferred.
