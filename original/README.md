# ABG correction and revision-history walkthrough — 18 October 2026

Local authoring workspace: http://127.0.0.1:5191/; source 008034ea12275406d8f5aede8ceb3aa5142570b6. No application change/rebuild or new test suite was performed for this normal-flow demonstration.

Original selected record: circulatory_oxygen / 1c1f16d9-33d7-40fb-a94f-013a383c9bfc / 1. Arterial pH 7.3300 at 09:45 UTC; specimen walkthrough-arterial-0945, own FiO2 40% / PEEP 5 cmH2O; unknown source quality and clock verification. Before correction, exact bounded history displayed one retained revision.

The operator entered actor Synthetic correction walkthrough reviewer, selected Append correction, changed only the numeric shortcut to 7.3500 and entered an explicit fictional transcription-correction reason (same sample/time, not a new sample). The server-validated review displayed the original value, proposed value, actor/reason and unchanged sample context before append. The initial pointer action reported a browser-tool targeting failure; the UI remained in review. Keyboard Enter on the same reviewed confirmation completed the append. This does not establish general pointer/touch certification or a complete dispatch trace.

Saved correction: revision aeaca128-a674-4dfa-859a-9ab11d2a9368, ingestion 173, canonical payload SHA-256 ef4c7c9855eb53c874373a7e7472b1c0bb10b58c7465d56f4a08fb826d65eb09. It supersedes the exact revision 1; the selected predecessor remains identified in the UI.

After refresh, Load exact revision history returned two retained revisions. Expanding it exposed full structured source details. displayed-history-comparison.json was extracted read-only from that rendered DOM; it is not a saved raw HTTP response. It shows original 7.3300 / ingestion 170 and corrected 7.3500 / ingestion 173, both with the same source time, arterial specimen, FiO2 and PEEP. Actor and correction reason are visible. history-expanded.jpg shows the original value and expanded two-revision history heading; it does not show every field of both records simultaneously.

Actual before/after database snapshots and row exports verify that all prior 172 fact rows are unchanged, with one new fact revision and one revision link. Both retained receipts, prior authored notes and all other tables except the sequence counter remain unchanged. The earlier reassessment still retains its exact original ABG reference, not an automatically substituted successor. No protected inference or treatment recommendation was run.

This is implementation-operated normal correction/history browsing, not an independent live witness, complete network trace, error/retry fault injection, hosted CI, container validation or clinical validation. History is bounded by captured state contexts; no signature authentication is independently established here. Pending draft recovery across browser reload/closure remains deferred.

Production execution remained disabled; no source changes, push, merge, deployment, external hosting or new GitHub publication occurred. Previously reviewed evidence remains unchanged.
