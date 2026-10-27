# Respiratory bedside workflow — approved scope

The user approved the populated respiratory demo and the longitudinal support workflow on 27 October 2026. Implement this in the existing patient workspace, preserving all previous capabilities and records. The approved visual reference is `clinrx-respiratory-abg-support-demo.html` in this chat's visualization directory.

## Bedside experience

- Four primary views: Overview, Support & ventilator, Blood gases & trends, Imaging & lung function.
- One ABG report per specimen, with pH, specimen-appropriate CO2/O2, bicarbonate, standard bicarbonate, base excess with its reported basis, total CO2, lactate, Na, K, chloride, glucose, ionised calcium, SO2c, THbc and any additional reported components. Retain exact units, method, source precision and measured/calculated distinctions. Never relabel calculated saturation as pulse oximetry or measured co-oximetry; never merge specimens.
- Display earlier sample values alongside the selected report. Select the latest usable sample automatically; retain deliberate selection. No reuse-by-reference action.
- Support entry distinguishes room air, nasal cannula, simple/Venturi/reservoir masks, HFNC, NIV, invasive ventilation, other device and unknown support. Only applicable settings are prominent. HFNC total gas flow and oxygen concentration are different measurements. Conventional oxygen flow does not establish an exact FiO2. Ventilator settings depend on the recorded mode; preserve manufacturer wording and an other-mode option.
- Every saved/imported support observation appears once in the chronological patient support history, including settings changes within one device. Procedures such as intubation remain distinct source events in the same history. Historical support and correction history remain inspectable after reload.
- New support entry explicitly distinguishes an ongoing episode from a point observation. Only an explicit, unambiguous episode or exact simultaneous source can establish sample-time support. Unknown, withdrawn, conflicting, superseded, future or ended evidence cannot silently provide current settings. A new support record bounds an earlier open episode; an explicit contradictory overlap is uncertain rather than silently resolved.
- Automatically show support at ABG collection from the same patient/encounter/repository/cutoff. Preserve direct ABG settings and flag conflicts rather than replacing them. Only calculations meeting the existing quality/unit/method prerequisites may use resolved source settings.
- Chest X-ray, CT chest, MRI chest and PFT reports remain linked original records; earlier PFTs are dated baseline context. No image pixels or PACS connection are invented. Preserve existing spirometry, chest examination, airway, liberation, specialist, physiology and saved-review capabilities through secondary details/actions.
- One respiratory assessment action with existing persistence and evidence-change protection. Prescription changes remain outside respiratory review.

## Implementation decisions

Extend the existing typed respiratory context with optional support-episode metadata, omitted when absent so legacy canonical payloads remain unchanged. Use the existing append-only respiratory endpoint and shared catalog; no new patient store or database migration. Build timeline/display components on that catalog and reuse them in patient overview. Keep advanced source/transcription/correction controls available below the routine form.

The user selected the existing demo approach. A separate module/store was rejected because it repeats entry; a new broad redesign is outside scope. The author will implement and a fresh reviewer will examine a frozen checkpoint.

## Preservation and validation

Do not change `sources/`, existing patient databases, or the running builds on ports 5246, 5247, 5249 and 5251. Record before/after hashes and integrity checks. Verify saves, reload, corrections and history in a separate database copy and serve the final candidate on a new local preview. Mobile verification is deferred by the user. Do not claim clinical validation or society endorsement.
