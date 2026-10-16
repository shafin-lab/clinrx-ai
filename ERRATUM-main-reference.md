# Erratum: local main reference versus GitHub main

Director correctly identified an ambiguity in the earlier hosting evidence.

- `46267e072be915c6b204fb0a127342032a2b88b1` is the **captured local `main` reference** in this Mac checkout.
- GitHub remote `main`, independently queried when writing this erratum, is **`0c0deed6d2d37135c0020de68958a24a4b45d131`**.
- The exact reviewed/tested application remains **`28496c46494dcafc5440b92712eab382cd3c80de`**, tree `00aa087cce492bd94d4c36c1e0d4299d79fa7d89`.
- PR #23 remains open/draft at **`17e2064c3f1a1761876e9a42c5c7a131646d465c`**.

Earlier evidence README/source-identity references to main must be read as the
captured local reference, not a claim about GitHub's current branch tip. Statements
that main was unchanged describe actions in this local task; they do not establish
that remote main had not advanced through other activity.

The remote query and local reference check are recorded in `main-reference-check.json`.
No fetch, local main update, merge, deployment or production gate activation was
performed to create this erratum. Application source/tree and validation results
are unaffected. Original evidence bytes and prior review tags are preserved.

The new local Linux ARM64 container build/startup/restart evidence is supplemental
to the earlier hosting review. It does not establish protected external HTTPS,
external visitor acceptance, other platform compatibility or deployment approval.
