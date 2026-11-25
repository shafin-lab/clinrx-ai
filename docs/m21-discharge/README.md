# Discharge and Transfer

M21 adds transition source records to the shared synthetic patient workspace. Build with VITE_SYNTHETIC_M21=true, VITE_SYNTHETIC_RF2=true and VITE_SYNTHETIC_HOSTED=true. The shared evidence loader also confirms microbiology and the blood/transfusion snapshot; device history is retrieved for the same patient and encounter.

Open workspace=discharge. Transition selection identifies a source-recorded ICU-to-ward or home-discharge plan and is retained in the URL. Summary, Medications, Care & follow-up and Review & handover bring original clinical records, reconciliation decisions, ownership and handover documentation together. Patient overview includes the latest available transition summary.

Transition documents are source records. Generic review notes remain separate from original orders, administrations and handover completion. There is no discharge execution or prescription publishing action. DischargeRecord is accepted by the repository and shared catalog; a dedicated hospital connector and transition-entry form are future work.

The existing browser store saves an append-only review per patient, repository and transition identifier. Saved context retains the device/procedure history reviewed. Source revision/digest changes, microbial evidence changes, transfusion evidence changes or device-history changes flag reassessment. Unavailable feeds, conflicting handover states or withdrawn transition evidence block new review saves. Historical transition reviews remain accessible. The shared review store caps a review at 500 source pins and 512 KiB. Shared authenticated server-side sign-off and audit storage remain future work.

An additive m21_0021 migration follows m20_0020 and preserves original rows, correction links and ingestion sequence. Existing preview databases are preserved. Only the disposable verification encounter is seeded or corrected.

Verification evidence is recorded locally under review-evidence/m21. The populated fictional encounter includes separate transfer-01 and home-01 transition plans, recorded medications, respiratory observations, laboratory results, precautions and an exact peripheral-IV episode. Both reviews were saved through the browser, reloaded, and flagged after an appended laboratory correction. Patient overview showed the reassessment flag. Independent review findings on handover identity, historical transitions, device evidence retention and conflicting handovers were corrected and covered by regression tests.
