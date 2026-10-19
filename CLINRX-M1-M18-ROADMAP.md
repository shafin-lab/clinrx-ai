# ClinRx M1–M18 roadmap and RF1 mapping

Recovered 19 October 2026. Existing module numbers are preserved. RF1 is a bounded implementation increment across the M8 and M9 scopes, not a new numbered module.

## Numbering and source basis

The original **ClinRx Development Director — Master Instructions** in [clinrx chat](https://chatgpt.com/c/6abcd0fa-f054-83ee-87dd-bbfecf5724fc?messageId=4ed11dc1-87ea-4d8f-91d2-b45b1976153a) explicitly lists M7–M18 and groups M1–M5 under current capabilities. The individual M1–M5 scopes below come from the repository's [recorded milestone checkpoint](references/project-state-at-5cb7321.md), not invented verbatim master-roadmap titles. M6 is the recorded microbiology/antimicrobial pathway. This reconciles the foundation milestones with the clinical-domain roadmap without renumbering either.

The original roadmap says it is provisional and may change following architecture reviews and clinical validation. The list records scope and numbering; it is not a completion or clinical-readiness register.

## Consolidated M1–M18 list

| Number | Name or recorded scope | Attribution |
|---|---|---|
| M1 | Typed multidomain patient-state contracts | Recorded milestone scope |
| M2 | Historical ownership validation and cutoff-bounded laboratory/medication assembly | Recorded milestone scope |
| M3 | Explicit A/B/M subset temporal inference | Recorded milestone scope |
| M4 | Patient-state execution contracts, immutable storage, protected execution and reconciliation | Recorded milestone scope |
| M5 | Application dependencies, scoped synthetic review APIs and clinician demo | Recorded milestone scope |
| M6 | Microbiology and antimicrobial pathway, M6.1–M6.5 | Recorded implementation / master context |
| M7 | Hemodynamics, vasopressors and lactate | Original roadmap title; expanded below |
| M8 | Renal physiology and CRRT | Original roadmap title |
| M9 | Fluid balance and output | Original roadmap title |
| M10 | Respiratory support and arterial blood gases | Original roadmap title |
| M11 | Coagulation and transfusion | Original roadmap title |
| M12 | Devices, drains and procedures | Original roadmap title |
| M13 | Sedation, analgesia and neurological state | Original roadmap title |
| M14 | Imaging and longitudinal findings | Original roadmap title |
| M15 | Nutrition and metabolism | Original roadmap title |
| M16 | Medication safety and organ-support dosing | Original roadmap title |
| M17 | Cross-domain integrated clinical reasoning | Original roadmap title |
| M18 | Governed treatment-plan generation | Original roadmap title |

## M7 scope expansion

M7's original roadmap title was **Hemodynamics, vasopressors and lactate**. Its later M7-A/M7-B brief expanded that same number to **Comprehensive Hemodynamic and Circulatory Support System**. The [recovered amendment excerpts](references/m7-expanded-scope-excerpts.txt) preserve that distinction. Cardiac output, echo, rhythm, oxygen transport and other circulatory evidence are part of the broader M7 representation; their presence does not establish completion of full respiratory or imaging modules.

Kernel v1, the early creatinine extension and H1-A–H1-D remain shared foundations or separately labelled increments. They do not consume or replace M8–M18 numbers. Earlier alternative roadmaps, such as the older pilot-chat labels, are not silently merged into this M6.5-era numbered plan.

## Where RF1 fits

| RF1 capability | Roadmap relationship | Remaining boundary |
|---|---|---|
| Original creatinine observations, missing/conflicting values and exact correction history | M8 renal physiology | No generated AKI stage, eGFR or renal treatment recommendation |
| Recorded CRRT net-removal context and relevant source weight | M8 renal support, with M9 accounting context | No full prescribed-versus-delivered renal-support workflow or dose calculation |
| Urine volumes over explicit intervals | M8 renal evidence and M9 output | No generated hourly or weight-based rate; gaps and overlaps remain visible |
| IV fluid, blood-product, drain and source-reported balance records | M9 fluid balance and output | No generated totals/balances or reconciliation of incomplete accounting |
| Shared repository, patient, encounter, review window and historical cutoff | Integration with the existing M7 patient workspace | Shared identity does not establish measurement simultaneity or cross-domain clinical reasoning |

RF1 is the first bounded, read-only synthetic renal/fluid review increment contributing to M8/M9. This is a scope mapping, not a rename of the approved RF1 specification, an implementation authorization, or a claim that either M8 or M9 is complete. The enclosing workspace retains separately accepted hemodynamic authoring; describing RF1 as read-only does not mean the entire workspace is write-incapable.

Future AKI assessment, governed fluid/urine calculations, fuller renal-support review, renal authoring and mixed-kind reassessment/handover need their own bounded specifications and approvals. They are not newly authorized here. M17 reasoning and M18 treatment planning remain distinct future capabilities.

## Review and execution boundaries

This publication changes documentation only. It does not close RF1-F1, establish new CI/browser/container results, alter clinical policy, or change any accepted evidence's attribution. RF1-F1 code and its CI belong to their separate candidate and evidence. Existing review originals remain intact.

Production connected execution remains disabled. No implementation, application-branch update, merge, deployment, external hosting or gate activation is included.

## References

1. [Original master instructions in clinrx chat](https://chatgpt.com/c/6abcd0fa-f054-83ee-87dd-bbfecf5724fc?messageId=4ed11dc1-87ea-4d8f-91d2-b45b1976153a); [recovered roadmap excerpt](references/recovered-master-roadmap-excerpt.txt). The excerpt is a transcription of the retrieved code-block text, not an authenticated full-chat export or approval record.
2. [Repository milestone checkpoint](references/project-state-at-5cb7321.md), preserved from application commit `5cb73212ae6104b02bad361886cd9507795d88bf`. Its dated status statements retain their original attribution; only the milestone scope table is used here.
3. [M7 scope expansion excerpts](references/m7-expanded-scope-excerpts.txt), from the earlier supplied M7-A/M7-B briefs.
4. [Approved RF1 specification](https://github.com/shafin-lab/clinrx-ai/tree/7fa529dd276ceb140700760a358cf3493b44e85b) and [original RF1 implementation evidence](https://github.com/shafin-lab/clinrx-ai/blob/0c4ec5623d9405c4e1547ba39601596861654879/START-HERE.md). Specification approval is separate from implementation acceptance.
