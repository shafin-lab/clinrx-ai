# Exceptional-attempt audit

This separates the interrupted UI attempt and diagnostic preparation from the accepted same-value lifecycle. Attribution to browser/operator diagnostic is recorded from the original execution transcript; Origin alone is not treated as proof of client identity.

| Attempt | Events / evidence | Execution UUID | Inference / row | Outcome |
| --- | --- | --- | --- | --- |
| Initial interrupted browser preparation | State #7, OPTIONS #8; `original/same_value-preparation-failure-dom.txt` and PNG | Not observable in captured artifacts: the client-generated value was neither displayed nor captured in a completed POST. No identity is invented. | No corresponding additional persisted inference or receipt identified. | UI entered preparation_unknown; that page did not retry. Kept separate and excluded from acceptance counts. |
| Operator's direct HTTP diagnostic | POST #9 (Python urllib call recorded in the original task transcript); OPTIONS #10 is a later preflight | 72eb013d-3592-484e-9695-2afa36631459 | 50ad2422-3d2b-4183-bfda-d8054f4aaaa1; ingestion sequence 26; 2026-10-16T06:48:25.312652+00:00 | Successful preparation, never executed. No receipt for this UUID. |
| Fresh-browser same-value acceptance case | State #11; preparation #13; execution #15 | 48714dc1-8166-4dfe-b11e-fdf39b8a91ad | 66d040b6-e3a1-4566-9c43-c3dbeed60afb; ingestion sequence 27; 2026-10-16T06:49:30.791626+00:00 | One execution; withheld after support-only successor. Exactly one retained receipt. |

Both preparation request/response bodies and all inference rows are published. The inference table contains exactly the two rows listed above, not three. The interrupted attempt's unavailable UUID cannot be recovered from these artifacts; the audit states that limitation rather than assigning a diagnostic UUID to it. It is not used to establish acceptance of any executed lifecycle.
