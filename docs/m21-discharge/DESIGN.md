# M21 Discharge and Transfer

Implement the approved populated design in the same patient workspace. Four views provide Summary, Medications, Care & follow-up, and Review & handover. A documented transition identifies ICU-to-ward transfer or home discharge, destination, receiving team, follow-up ownership, reconciliation decisions and actual handover status. The shared clinical record supplies evidence automatically.

Use typed transition source records in the existing revision/cutoff store. Keep separate transition identifiers so a transfer review never becomes a home-discharge review. Preserve exact revisions and prior reviews. Clinician reviews are append-only browser records using the existing Web Lock store. A relevant source change flags reassessment after reload. No synthetic example implies that a transition is completed, that a medicine should be prescribed, or that an assessment is a validated readiness decision.

The alternatives were a manually assembled handover or a shared-evidence transition workflow. The user approved the shared-evidence design. Reuse source drawers, medication records, device history and source-pinned review storage. Display unavailable evidence explicitly. Preserve all prior previews, stores and synced sources. Verification uses only disposable fictional copies.
