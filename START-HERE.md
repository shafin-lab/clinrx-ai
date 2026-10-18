# Original and new reassessment notes — read-only comparison capture

Application reference: `008034ea12275406d8f5aede8ceb3aa5142570b6`  
Application tree: `f9e626c1e4f3a478644a079cba9cf1437c04b2d7`

This separate supplement contains exactly three unchanged capture originals from the implementation-operated local viewing at http://127.0.0.1:5191/: original-reference.jpg, corrected-reference.jpg and both-notes.txt. It introduces no application code or database change.

The workspace was filtered to Recorded circulatory events with search 1c1f16d9. Both note cards are present in the same filtered list. The narrow viewport has an internally scrollable list; the two screenshots show different scroll positions, NOT both complete notes simultaneously or a side-by-side application view. The complete DOM snapshot preserves both notes together as document text.

Original note: circulatory_event / abae4ef7-74c4-48cc-bb50-f50e9fb151cd / 1, recorded 09:50 UTC. Its followup is circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / 1, pH 7.3300. original-reference.jpg shows the ABG identity/version 1 and original pH text; its note ID/time are outside that internal-scroll viewport.

New note: circulatory_event / 90c89b62-1f3a-4903-b10d-eb8c6711e921 / 1, recorded 09:55 UTC. Its followup uses the same ABG identity with revision aeaca128-a674-4dfa-859a-9ab11d2a9368, pH 7.3500. corrected-reference.jpg shows the exact successor reference and beginning of narrative; full pH/context and note identity are established by the complete DOM and earlier stored-note evidence, not all simultaneously visible in that screenshot.

Both retain baseline circulatory_oxygen / a02f88e1-db04-48a0-89e6-f236016a38a8 / 1 and intervention circulatory_vasoactive / 99a26724-026c-4ccc-ac63-c22ddada2664 / 1. The new note explains the same-specimen transcription correction and makes no treatment-effect or physiological-improvement claim. Original note wording and reference are retained rather than silently substituted.

The earlier saved-note/database evidence is separate and remains unchanged:
https://github.com/shafin-lab/clinrx-ai/pull/23#issuecomment-6252257278
Evidence c967cc2521131606e54cc90322154a7aa93e2f2e contains actual 173-to-174 checkpoints, exact note payloads, preview and saved confirmation. Use it for persistence/preservation claims. This viewing supplement has NO new database checkpoint, raw API response, network trace, authentication proof, build identity or test run.

The captured DOM includes Clinical execution disabled and the saved confirmation for ingestion 174. The screenshot viewports do not show the header. Existing source identity and local service configuration are inherited from prior evidence, not freshly authenticated by this comparison. No live independent witness, pointer/touch certification, fault injection, hosted CI, container validation or clinical validation is claimed. Durable browser-session recovery remains deferred.

Review the two images and complete DOM with their original hashes. MIRRORS.json provides bounded lossless base64 parts with lengths, SHA-256 and Git blob identities. PUBLICATION-SHA256SUMS.json covers publication artifacts and verify_publication.py performs data-only checks. No ZIP or Mac access is needed. Prior R1/F1/F2 closure and accepted walkthrough scopes remain preserved.

Production execution stays disabled. No new record was saved during this viewing/publication; no merge, deployment, external hosting or execution-gate activation is authorized or performed.
