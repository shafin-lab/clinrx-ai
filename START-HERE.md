# Compact comparison walkthrough supplement

Application reference: `ebbab2955109884169ae7ceef4a87d0f12af4ebf`  
Application tree: `7ecf17aa1918d1267e2e00e91248b039e6632446`

Read-only implementation-operated viewing of the existing local 5191 compact comparison. Exactly three original captures are preserved: reference-table.jpg, expanded-notes.txt and final.txt. No app code, note, database, build or test was changed/run by this walkthrough or evidence publication.

## What to inspect

- original/reference-table.jpg: both columns are visible together, including note identities/revisions, source times, actors/status and retained baseline/intervention/follow-up references. It does not show both full narratives or the execution-disabled header; the top visible selector is partially clipped. The image has JPEG bytes and a matching .jpg extension.
- original/expanded-notes.txt and original/final.txt: complete DOM captures include both full authored narratives, expanded uncertainty/provenance and disabled-execution messaging. They are distinct captures; do not relabel them as a screenshot or independent live witness. The final browser view was returned to the table with disclosures left expanded below it.
- reference/persisted-notes.json: reused exact bytes from the earlier c967cc saved-note evidence's original/note-comparison.json, NOT a fresh DB/API response. SHA-256 9f2a68a88c2fa3609f0126b9c429ed2c4ee09f88c9d737c01d75098876e3d5fc.
- reference/source.json: reused exact bytes from the earlier compact comparison validation, NOT a new build/source authentication during this walkthrough.

## Exact correspondence

Note A is original reassessment circulatory_event / abae4ef7-74c4-48cc-bb50-f50e9fb151cd / 1, recorded 09:50 UTC. It retains follow-up ABG circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / 1. Its authored narrative records pH 7.3300.

Note B is new reassessment circulatory_event / 90c89b62-1f3a-4903-b10d-eb8c6711e921 / 1, recorded 09:55 UTC. It retains the same oxygen fact identity with correction revision aeaca128-a674-4dfa-859a-9ab11d2a9368. Its narrative records corrected pH 7.3500 and identifies a same-specimen transcription correction, not a new measurement or physiological improvement.

Baseline oxygen a02f88e1-db04-48a0-89e6-f236016a38a8/1 and documented intervention vasoactive 99a26724-026c-4ccc-ac63-c22ddada2664/1 remain exact in both. Clinical relationships remain unestablished; quality/clock uncertainty, synthetic source attribution and incomplete provenance remain visible in the expanded DOM. No treatment effect, diagnosis or recommendation is established by the comparison. The table does not newly load measurement values or substitute successors.

## Earlier evidence stays separate

Four-file implementation and validation: 08e7b16c72da2c65d2f88c0324e186b237a406cc
https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252470474

Actual saved-note/database exercise: c967cc2521131606e54cc90322154a7aa93e2f2e
https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252257278

The 602-test/full frontend result, final default/authoring builds, source-file hashes and prior CSS test-order qualification belong to 08e7b16. The actual 173→174 database checkpoints belong to c967cc. Neither is rerun or newly established by this viewing session. This supplement contains no fresh API/database checkpoint, complete network trace, signature authentication, resource-load proof, backend suite, hosted CI, container/restart validation or clinical-readiness claim. Application identity/configuration is inherited; the disabled header in the DOM is not an independent gate probe. No broad pointer/touch/device/accessibility certification follows.

Use ORIGINAL-SHA256SUMS.json, PUBLICATION-SHA256SUMS.json, MIRRORS.json and verify_publication.py for portable data-only integrity/correspondence checks. Large/binary captures have bounded lossless base64 parts; no ZIP or Mac access is required. Prior reviewed artifacts remain unchanged. Preserve R1/F1/F2 closure and accepted walkthroughs; the new UI increment and this supplement require their own bounded verdicts.

Durable browser-session recovery remains deferred. Production connected execution remains disabled. No merge, deployment, external hosting or gate activation is authorized or performed.
