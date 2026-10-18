# PR #23 — corrected 008034e reassessment walkthrough supplement

Application: **008034ea12275406d8f5aede8ceb3aa5142570b6**  
Tree: **f9e626c1e4f3a478644a079cba9cf1437c04b2d7**  
Parent: **fa8ce7dfba52af169c6f474dbd0826d747884945**

[Exact accepted source](https://github.com/shafin-lab/clinrx-ai/tree/008034ea12275406d8f5aede8ceb3aa5142570b6) · [Previous R1/walkthrough guide](https://github.com/shafin-lab/clinrx-ai/blob/9fc33d21b36d17fa0e5f89ec00e08ff94328a2eb/START-HERE.md)

## Scope and preserved verdicts

The user supplied Director's verdict accepting R1 at this source and the earlier **fa8ce7d** walkthrough. F1/F2 closure and bounded guided-form acceptance remain preserved. This supplement requests review of the **new normal-flow browser walkthrough on 008034e only**. It does not request another code review, collision test, duplicate suite, or new acceptance for previously closed findings.

No application changes were made for this publication. The earlier evidence at 9fc33d21 and 62cc60ab is unchanged. Those guides retain their historical attribution: the previously unestablished corrected-source browser run is supplied here as a later, separately captured supplement, not retroactively attributed to their artifacts.

## Start with the captured evidence

All **15 original manifest-listed artifacts** are copied byte-for-byte, plus their unchanged original manifest:

- [Original report](original/README.md), [original hashes](original/SHA256SUMS.json), [update/build/health metadata](original/update.json), [fresh authoring build/typecheck log](original/build.log).
- [Actual selected menu tuples and visible labels](original/selected-options.json), [form DOM](original/reassessment-form.txt), [validated review DOM](original/reassessment-review.txt), [saved DOM](original/reassessment-saved.txt), [actual saved viewport JPEG](original/saved-reassessment.jpg).
- [Stored reassessment](original/stored-reassessment.json), [local data-only verification result](original/verification.json), [browser-observed script paths](original/browser-script-paths.json).
- [Before SQLite](original/before.sqlite3), [after SQLite](original/after.sqlite3), [before rows](original/before-rows.json), [after rows](original/after-rows.json), [readable all-table row index](TABLES-INDEX.json).

### Local update boundary

The browser showed the previous note already saved at ingestion 171 before reload. The frontend was rebuilt from 008034e with the same synthetic patient/encounter/review configuration. The old fa8ce7d frontend was preserved, the local frontend directory replaced, and the page reloaded. The backend was not restarted; no database was reseeded. The implementation compared every table before/after the frontend replacement and reported no changes. The **before.sqlite3** checkpoint precedes that replacement; **after.sqlite3** follows the explicit reassessment append.

update.json records the disabled health response, build hashes and nine reviewed source-file hashes. Browser-observed script paths correspond to the new bundle. [Exact referenced build files](build-reference/index.html) supplement those hashes: the HTML, JavaScript and CSS are published only as raw verification artifacts, not deployed as an application. Their bytes match the captured build hashes. This correspondence is not a complete authenticated network trace or proof of every resource load.

## What was exercised

The operator selected these exact revision-1 sources through the corrected tuple-valued menus:

| Stage | Source | Recorded context |
| --- | --- | --- |
| Baseline | circulatory_cardiac / 98bda243-a9f5-494d-8733-8b575b75bf65 / 1 | CO 4.700 L/min at 09:25 UTC; suspect quality |
| Intervention | circulatory_vasoactive / 99a26724-026c-4ccc-ac63-c22ddada2664 / 1 | Documented dobutamine rate change at 09:30 UTC |
| Follow-up | circulatory_perfusion / 33b64610-60af-4c43-b9ee-393ff63d2e96 / 1 | Capillary refill 3.00 s at 09:35 UTC; unknown quality |

The authored fictional reassessment separates recorded findings, unconfirmed possibilities, confirmation gaps and an unscheduled review plan. Different measurements and source times do not establish a causal response, diagnosis, responder classification, physiological calculation or treatment recommendation.

The validated review and saved DOM identify note **b19580df-dfcb-4494-a076-9a806be2c187 / 1**, confirmed at ingestion **172**. Persisted payload SHA-256:

`7e91409555cf2fc9693c8baece95a1d5253b1df3b70697525ff7e55927d2948d`

All three DOM selection tuples match the stored exact associations, stage-labelled external references and narrative. Before/after captured databases contain 171 and 172 fact rows respectively. All prior 171 rows remain exactly equal; both retained receipt rows and every other table except the expected sequence counter remain equal. The newly inserted note is the only fact-row addition.

### Gate and refresh attribution

The review DOM shows “Clinical execution disabled.” The immediate saved DOM was captured during the post-save refresh boundary: it says “Execution gate not confirmed — new writes blocked,” while confirming ingestion 172. That is a blocked confirmation state, not evidence of execution activation. The later viewport JPEG shows the saved note and uncertainty; it does not include the header or independently prove completion of the refresh. Disabled health is reported in update.json. No additional final-state/API capture is substituted for these originals.

## Integrity and access without ZIP/Mac access

[Publication checksums](PUBLICATION-SHA256SUMS.json), [lossless mirrors](MIRRORS.json), [portable data-only verifier](verify_publication.py), [verifier output](PUBLICATION-VERIFICATION.txt).

The mirror index lists bounded base64 parts, lengths, SHA-256 and Git blob identities for binary/NUL/large artifacts. Concatenating and decoding those parts reconstructs exact SQLite, JPEG, bundle and large-export bytes through text tools. Readable row files supplement the original snapshots. All 15 original hashes can be recomputed; no originals or earlier reviewed artifacts are renamed, rewritten or replaced. No signing key, credential or signed read token is included. Earlier withheld-token limitations remain with their original publications.

## Limitations and validation attribution

This is implementation-operated live normal selection/review/save on the corrected source plus captured database correspondence. The three selected IDs are **noncolliding**. The slash-collision cases remain covered by the accepted 37-focused-frontend / 15-API-storage regression evidence in 9fc33d21, not by a live collision exercise here.

The fresh local authoring build/typecheck passed. No new full frontend/full backend suite, hosted CI, container validation, restart proof, complete request/response trace, browser delivery-fault injection, independent live witness or clinical validation is established. No tests were repeated solely to publish these artifacts. The prior 588-test result belongs to fa8ce7d. Prior timeout uncertainty remains disclosed. Actor/source identities are assertions. **Durable browser-session recovery remains deferred**; existing in-memory exact recovery is preserved.

PR #23 remains draft/open/unmerged at unchanged application head **17e2064c3f1a1761876e9a42c5c7a131646d465c**. Its CI does not cover this downstream source. A separate evidence tag links this supplement without changing that branch. The accepted read-only Docker demo remains separate and unchanged.

**Production connected execution stays disabled. No merge, deployment, external demo hosting, gate activation or clinical-readiness approval.**
