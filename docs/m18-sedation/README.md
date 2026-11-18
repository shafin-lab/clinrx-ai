# M18 Pain, Sedation and Delirium

The approved 23 October 2026 M1–M21 roadmap defines M18. The earlier connected
delivery specification describes the detailed domain requirements under its
historical M13 Sedation / Analgesia / Delirium heading.

## First increment

The shared synthetic patient workspace exposes a read-only sedation review when
`VITE_SYNTHETIC_RF2=true` and `VITE_SYNTHETIC_M18=true`. It uses the existing RF2
catalog and neurological filtering for the same patient, encounter, review period
and repository cutoff. Each exam shows its recorded RASS observation when usable,
plus source time and status. The existing source drawer opens the exact revision
and its history. Neurological medication status observations retain their original
time and status in a separate list.

Loading, failed or mismatched snapshots withhold the evidence view. Superseded,
withdrawn and conflicting scores stay out of the structured observations.
An evidence refresh closes the source drawer as the review context changes.

The first increment displays explicit gaps for structured pain, sedation targets,
and delirium assessment and assessability. A later increment can add typed source
records for those observations and exact links to breathing, mobility and actual
analgesic and sedative administrations. The current increment uses the existing
execution-disabled synthetic gate and has no write or treatment execution path.
