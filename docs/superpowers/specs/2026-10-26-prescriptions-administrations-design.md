# Prescriptions and administrations

The user approved the interactive full-page design on 26 October 2026 and explicitly requested implementation. Build on the existing isolated candidate and existing validate/review/save/recovery commands. One patient workspace owns the evidence; reference content is not executable prescribing policy.

## Approved experience

One compact kidney summary automatically selects the latest eligible creatinine and measured weight at the selected clinical/repository cutoff. Age and the named Cockcroft–Gault coefficient come from explicit recorded patient dosing context, never inferred from names, respiratory coefficients or fictional examples. Missing inputs are shown honestly. A collapsed form can record missing patient context once using the existing shared RF2 note contract; a versioned, strictly parsed findings object supplies structured context without a new fact type, database or duplicated laboratory values. Each context note cites original evidence and survives reload through the repository.

Show a prescription table with dose, route, schedule and individual dose review. Preserve all medicine courses and all actual administrations/non-delivery records, including unlinked source records. Group only by explicit order identity or exact unlinked identity/product/route; never attach administrations by name to an arbitrary prescription. Multiple prescriptions may be entered without a small UI cap. History shows recorded event time, actual administered amount, given/held/missed/refused/not-given status, reason, exact source and correction history. Missing documentation never creates a missed dose or invented schedule.

Renal suggestions remain external source candidates. Reuse existing bounded dose profiles and exact clinical-context gates; introduce the approved anidulafungin maintenance reference as an explicitly supported profile. Teicoplanin and other concentration-dependent medicines remain individual review. Keep NCDC and supplementary library unchanged. No CRRT/HD recommendation is introduced on this page. Show an actionable candidate only when current sources and reviewed indication/route/phase/infusion/patient context match. Accepting creates an explicitly reviewed editable prescription correction or draft, not a save or administration. New evidence invalidates selections and never silently changes an order.

## Approach and implementation decisions

The selected approach is to compose the existing records and commands into the approved table. A new standalone medication store would duplicate sources; a cosmetic table over the existing manual calculator would not implement automatic calculation. Preserve legacy calculator/advisor code for existing integrations while removing its large always-visible panel from this page.

Freshness for this candidate is explicit: latest creatinine no older than 24 hours and measured weight no older than 7 days relative to review end; these are conservative preview limits, not universal clinical rules. Unusable latest results, tied contradictory results, unresolved identity, supersession, future availability, incompatible units and new creatinine rises withhold routine suggestions. Stable impairment is distinct from normal renal function and is clinician recorded, never derived from a low CrCl. Weight suitability is explicitly reviewed. Patient context is scoped and reviewed against source pins; a changed weight or creatinine trend requires appropriate re-review.

## Preservation and validation

Do not change `sources/`, existing reference datasets, original 5246 preview, or either patient database while implementing/verifying. Prior 5247 assets are archived under `review-evidence/prescriptions-20261026/previous-build`. Verification may write synthetic fixtures only in isolated temporary database copies. Desktop checks cover the full workflow and no-write browsing; mobile checks remain deferred. Finish with an independent review at a fixed source checkpoint and publish the candidate with rollback assets retained.
