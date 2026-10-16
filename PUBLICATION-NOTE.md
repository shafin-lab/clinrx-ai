# Publication manifest correction

The first evidence tag `clinrx-patient-summary-evidence-a9e72c5` is preserved.
Its outer SHA-256 index excluded both files named SHA256SUMS.json, unintentionally
omitting original/SHA256SUMS.json as well as the outer manifest itself. GitHub blob
verification still matched all published bytes, and the verifier checked the
original manifest's listed files, but the outer file count was understated.

The v2 evidence tag includes the original manifest in the outer manifest, fixes
the verifier's exact-file-set check to exclude only the root manifest, and indexes
all originals. No application source, test log, original capture, original
manifest, database or exported data changed. The first evidence reference is
superseded for this handoff; it was not linked as the completed PR handoff.
