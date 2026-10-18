# Corrected-ABG reassessment walkthrough — captured evidence

Application reference: `008034ea12275406d8f5aede8ceb3aa5142570b6`  
Application tree: `f9e626c1e4f3a478644a079cba9cf1437c04b2d7`

Review this separate normal-flow reassessment using an explicitly corrected ABG. Preserve earlier R1/F1/F2 closure and corrected-source reassessment acceptance at evidence `7a2f10dc6a9ae96eff9d52d9b90969d5a6d95c63`. This package does not revise application code or earlier evidence.

## Readable starting points

- `original/README.md` describes the actual actions, attribution and limits.
- `original/form.txt` retains the three selected exact option identities and authored fields.
- `original/review.txt` is the pending validation boundary; `original/review-ready.txt` is the completed validated preview. Do not conflate them.
- `original/saved.txt` and `original/final.txt` retain the saved confirmation at ingestion **174**. They are byte-identical.
- `original/saved.jpg` shows the saved status, digest and uncertainty text; it does not show all selectors, both notes or the disabled header simultaneously. `original/review.jpg` is a separate earlier viewport.
- `original/note-comparison.json` contains the original and new note records, including exact context associations, stage-labelled external evidence and narratives.
- `original/before.sqlite3`, `original/after.sqlite3` and both raw row exports are actual captured checkpoints, not reconstructed replacements.
- `TABLES-INDEX.json` links individual readable rows for all 12 tables in both checkpoints.
- `MIRRORS.json` links bounded lossless base64 parts for binary or large artifacts; no ZIP or local Mac access is required.
- `PUBLICATION-SHA256SUMS.json` and `verify_publication.py` support data-only checks. The verifier does not execute the application.

## New note and preservation

Original ABG reassessment: `circulatory_event / abae4ef7-74c4-48cc-bb50-f50e9fb151cd / 1` remains unchanged and explicitly references original ABG revision `1` (pH **7.3300**).

New reassessment: `circulatory_event / 90c89b62-1f3a-4903-b10d-eb8c6711e921 / 1`, ingestion **174**, payload SHA-256 `b0073215bcb9e38a35a8b24d5d3b50bbb7e7b9ce2aea114f6c185dd2d5ec3b87`. It is a new entry with no predecessor, not a correction or replacement of the original note.

Exact new selections:

1. Baseline: `circulatory_oxygen / a02f88e1-db04-48a0-89e6-f236016a38a8 / 1` (pH 7.3400 at 09:20:00.123456 UTC).
2. Documented intervention: `circulatory_vasoactive / 99a26724-026c-4ccc-ac63-c22ddada2664 / 1` (recorded rate-change event at 09:30 UTC).
3. Follow-up: `circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / aeaca128-a674-4dfa-859a-9ab11d2a9368` (corrected pH 7.3500 at 09:45 UTC).

The new authored note is timed 09:55 UTC. It distinguishes recorded findings, unconfirmed possibilities, confirmation gaps and an unscheduled review plan. It explicitly describes the 7.3300→7.3500 same-specimen transcription correction, not a new measurement, physiological improvement, diagnosis or infusion response. Arterial specimen walkthrough-arterial-0945 retains its own FiO2 40% and PEEP 5; source quality and clock verification remain unknown.

The database grows from **173 to 174 fact rows**. Every prior stored fact row remains exact, including both ABG revisions and earlier notes. All other tables, including revision links and both retained receipts, remain unchanged except the expected sequence counter. The before snapshot is byte-identical to the preceding correction/history after snapshot, connecting the checkpoints without rewriting it.

Related correction/history package: https://github.com/shafin-lab/clinrx-ai/tree/457144d01832ddaef0f8b5338bad5097f16bc741

## Boundaries

Implementation-operated normal-flow captures and implementation-produced data checks, not an independent live exercise or complete authenticated browser/network trace. Exact application reference is inherited; no new source build identity, resource-load trace or signature authentication was captured here. Initial getByLabel targeting failed without changing the form; the observed combobox-role selector succeeded. Validation and saving completed asynchronously; keyboard Enter confirmed the reviewed append. No fault injection or recovery behavior is tested by this successful normal flow.

No application changes, new builds/tests, hosted CI, container validation, restart or clinical-readiness claim. The capture-time README statement that no publication occurred applies to the walkthrough only; this separate publication now makes those unchanged captures accessible. Durable browser-session recovery remains deferred.

Production connected execution remains disabled. No merge, deployment, external hosting or gate activation is authorized or performed.
