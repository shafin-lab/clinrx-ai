# RF1-S1 focused specification correction

Documentation only. Application baseline: b4194447829f060387b816437694af9f6c0cb60e, tree eb6ed9d3f53727ccf186c1cb3ee5b5ba9f2677df.

Previous document commit: 1338ade349dd33c341dde6dfc8c6470beb151790. That revision and its artifacts remain preserved. It was NOT approved for implementation. This revision requests focused RF1-S1 closure, not retrospective approval of the original.

Read RENAL-FLUID-WORKFLOW-SPEC.md, One synthetic episode and test fixture. The sole specification change distinguishes supported generic ClinicalObservation/ClinicalValue examples from typed withdrawn/suspect-quality circulatory records. It prohibits inferring withdrawal from historical status, promoting retained source text into typed facts or extending the legacy contract. HEMODYNAMICS-COMPLETION.md is unchanged.

Retain all six Director implementation conditions:
1. Include bounded original observations, not only v1 projections that omit missing/unplaced records.
2. Share aggregate retrieval accounting and enforce combined response-size limits.
3. Fail closed on mismatched scope, cutoff, context, digest or references.
4. Preserve terminal/history semantics without successor substitution or resurrection of older values.
5. Demonstrate no fact/receipt writes during the real-API read-only journey.
6. Keep renal authoring, mixed-kind notes/handover and clinical calculations deferred.

SHA256SUMS covers these three Markdown documents. No application tests or walkthroughs were rerun for this wording correction. Existing evidence and acceptances retain their original scopes. Uncoached usability remains open.

Implementation remains unapproved pending Director's exact-revision verdict. Application code, configuration and PR #23's application branch remain unchanged. Keep execution disabled and additions frozen. No implementation, merge, deployment, external hosting or activation is authorized.
