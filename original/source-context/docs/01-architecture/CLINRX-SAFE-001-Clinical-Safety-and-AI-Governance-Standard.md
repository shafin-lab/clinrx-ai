# CLINRX-SAFE-001 — Clinical Safety & AI Governance Standard

**Document ID:** CLINRX-SAFE-001

**Version:** 0.2

**Status:** Draft

**Date:** 2026-09-25

**Effective Date:** Pending approval

**Owner:** ClinRx AI

**Classification:** Architecture / Clinical Safety and AI Governance Standard

**Parent Standard:** [CLINRX-ARCH-001 v1.1 — Long-Term Clinical AI Architecture Standard](CLINRX-ARCH-001-Long-Term-Clinical-AI-Architecture.md), Draft

**Related Foundational Standard:** [CLINRX-DATA-001 v0.3 — Clinical Data & Knowledge Standard](CLINRX-DATA-001-Clinical-Data-and-Knowledge-Standard.md), Draft

---

# 1. Purpose and Interpretation

This standard defines the clinical safety obligations for ClinRx decision support throughout development, evaluation, deployment, use, change, and retirement. It operationalizes the parent standards without replacing their architecture or information semantics.

**AI reasons. ClinRx governs.** Clinical judgment remains with the treating clinician; platform owners remain accountable for the safety of the system they provide. Human review is a safety control, not a transfer of all system risk to the clinician.

“Shall” and “must” express proposed mandatory requirements upon adoption. “Should” expresses a recommendation whose exception requires documented rationale; “may” expresses an option. Draft status, repository publication, and completion of this document do not authorize clinical use.

**Passing automated checks does not itself establish universal clinical validity.** No detected violation means only that specified checks found none within their evaluated coverage. Clinical validation, release permission, presentation, clinician acceptance, and clinical benefit remain distinct.

This standard is technology-independent. It specifies durable safety invariants and required decisions, not database tables, services, model vendors, prompts, interface layouts, treatment thresholds, or operational runbooks. It neither declares regulatory classification nor claims compliance or clearance; qualified owners shall determine applicable obligations for each intended deployment.

The following terms shall remain distinct throughout the workflow:

| Term | Safety meaning |
|---|---|
| Clinical contraindication | A clinical circumstance that argues against an intervention; its absolute or conditional consequence follows applicable governed knowledge and policy |
| Hard failure / hard stop | A non-overrideable failure / the resulting withholding of the affected ClinRx advice or action path |
| Warning | A policy-classified advisory finding; acknowledgement and an authorized exception, where permitted, are different events |
| Unknown | Relevant information or its interpretation is not established; not a negative finding |
| Negative finding | An attributable observation or assessment that did not identify the specified condition within its method, timing, and scope; not universal exclusion |
| Outside validated scope | The proposed use exceeds established clinical coverage; apparent plausibility does not authorize actionable release |

# 2. Relationship to Parent Standards

ARCH-001 owns system responsibilities, the Domain → Engine → Specialty workflow separation, and the final release boundary. DATA-001 owns information categories, lifecycle semantics, versions, executions, provenance, and retention qualifications. SAFE-001 owns safety-policy decisions, assurance expectations, clinical oversight, and lifecycle governance.

| Safety concern | Owning parent reference | SAFE-001 operational coverage |
|---|---|---|
| Exact meaning and output release | ARCH Sections 5, 6.7–6.8; DATA Section 31 | Sections 5–6, 10–11 |
| Patient identity, freshness, uncertainty | ARCH Sections 6.1, 12–13; DATA Sections 19–28, 33 | Sections 7–9 |
| Knowledge, evidence, rules, calculations | ARCH Sections 6.2–6.6, 9; DATA Sections 4–18, 29–30 | Sections 8, 12–14, 20 |
| AI, providers, output classification | ARCH Sections 7–8, 11, 18; DATA Sections 20, 31.3, 39 | Sections 4, 15, 19, 21 |
| Human oversight and hazards | ARCH Sections 17–19; DATA Sections 34, 36, 38 | Sections 16–18, 26–28 |
| Integration, security, audit, recovery | ARCH Sections 14–16, 20.1; DATA Sections 32–45 | Sections 22–25 |

The parent versions are the installed repository ARCH-001 v1.1 and DATA-001 v0.3 at commit `2ff21b786c3bc8f4e9eb002d556f4f373ddca014`. DATA-001's historical candidate-parent reference remains historical; SAFE-001 does not treat the earlier incomplete ARCH draft as its parent.

Accepted ADRs and legacy CAS documents remain unchanged. The taxonomy, lifecycle, and reference reconciliation issues in DATA-001 Section 50.1 remain open. Conflicts require explicit governance review and, where architectural decisions change, an approved ADR; this Draft does not silently supersede them.

# 3. Intended Use and Safety Scope

Every clinical capability shall have an approved, versioned intended-use specification before patient-care release. It shall identify:

- the clinical question, decision role, benefit claimed, and actions the output could influence;
- intended users, required competence, care setting, jurisdiction, workflow, and expected time to act;
- supported populations, exclusions, relevant subgroups, and conditions requiring specialist review;
- required sources, input meanings, completeness and freshness, output scope, and mandatory checks;
- permitted AI contribution, human responsibilities, foreseeable misuse, and downstream integrations;
- validation evidence, risk acceptance, operational monitoring, escalation, and suspension criteria.

General information shall not be represented as patient-specific advice without sufficient verified context. Summaries, triage rankings, predictions, omitted findings, and recommendations to take no action are clinically meaningful when they can influence care; a disclaimer or an “informational” label does not remove their safety obligations.

Autonomous downstream clinical action is outside this Draft's authorized behavior. Ordering and administration require separate authorization and records; acceptance of advice is neither. Any future autonomous capability requires a separately approved intended use, safety case, and integration design consistent with ARCH-001 Section 19.

Research, authoring, testing, historical review, limited review, and production use shall remain distinguishable. Nonproduction evaluation shall not silently influence live clinical care. Scope expansion is a governed change, not an inference from apparently good performance.

Applicability shall be established for each contributing evidence interpretation, rule, calculation, model, and their combination, not only for the overall workflow label. Relevant dimensions shall include developmental stage in pediatric care, pregnancy/lactation, body size and composition, renal and hepatic dysfunction and trajectory, organ support, transplant type and phase, and perioperative phase where these can materially affect the use. Missing information needed to determine applicability shall not default to a general-population pathway; affected advice shall be narrowed to supported scope or withheld.

Where relevant to the intended use, verified patient preferences, goals of care, and treatment limitations shall constrain recommendation construction and clinical reconciliation. Unknown preferences shall remain unknown, and conflicts with proposed care shall be made explicit rather than resolved by assumed consent or an AI-inferred treatment goal.

# 4. Clinical Output and Risk Classification

Each clinically material claim shall retain the DATA-001 Section 31.3 production classification: deterministic calculation, rule-derived, evidence-derived, or AI-generated/inferred. Multiple classifications may contribute to an output. AI rendering of a calculation does not change the result's origin; repeatable prediction remains inference. Origin does not determine clinical risk or establish authority.

The following internal assurance tiers guide review effort; they are not regulatory device classes:

| Tier | Foreseeable influence and harm | Minimum assurance emphasis |
|---|---|---|
| A: Clinical information | Bounded reference or summary use with limited immediate decision impact | Source fidelity, omissions, applicability, and comprehension |
| B: Patient-specific support | Interpretation or advice whose error or omission could change management | Full patient binding, required safety coverage, clinical evaluation, and meaningful human review |
| C: High-consequence support | Potential serious harm through error, delay, omission, or overreliance, including high-risk treatment and urgent prioritization | Independent clinical challenge, explicit failure analysis, relevant subgroup evaluation, workflow simulation, and demonstrated suspension/recovery controls |

Clinical safety owners shall assign the tier with documented severity, likelihood and its uncertainty, time sensitivity, reversibility, exposure, detectability, and reliance on human mitigation. A reference summary may be Tier C in an urgent workflow. Dose advice shall receive explicit high-consequence assessment rather than a lower tier merely because it is deterministic.

Uncertain classification shall use the more protective applicable tier pending review. Mixed outputs inherit the highest relevant tier unless lower-risk portions are demonstrably separable. Tiers scale evidence and review effort; none waives the parent hard failures or the release boundary.

These tiers are internal aids to proportional assurance, not a second regulatory classification system. High-consequence control coverage follows Section 17; assigning a tier does not substitute for identifying and controlling the actual hazards.

# 5. Output States and Release Decisions

The logical sequence is **candidate → rendering → validation → release → presentation**. The broader information-to-action chain shall preserve the distinctions:

**data → derived value → inference → recommendation → rendered claim → safety evaluation → release → presentation → human decision → downstream clinical action**.

This is a dependency and accountability view, not a requirement to execute every step. Deterministic or evidence-based pathways may bypass AI inference; some do not require a derived value. Data does not become a verified fact merely through reuse, a calculation does not establish an inference's clinical truth, and an inference is not an authorized recommendation. In this chain, recommendation means a structured candidate and rendered claim means proposed clinical content; required safety evaluation and exact-meaning validation precede release. Presentation proves neither human acceptance nor action, and an order proves neither execution nor administration.

Upstream work may be iterative or parallel; the final release dependency cannot be bypassed. The following describe distinct records or events, not a mandated single database state machine.

| Record or state | Meaning and permission |
|---|---|
| Candidate | Structured proposed output with dependencies, rationale, limitations, and claim classifications; not eligible as released clinical advice |
| Rendered | Exact proposed clinical content prepared for the intended destination; not yet authorized for clinical presentation |
| Evaluated | Identified checks and exact-meaning validation attempted/completed with outcomes and coverage; failure, uncertainty, or incompleteness remains explicit |
| Released | Orchestration has recorded permission for the exact evaluated content, context, intended use, recipient authority, and permitted warning exceptions |
| Withheld | A recorded decision not to release the affected advice, with reasons and a safe next step where available |
| Presented | Record of what released content was actually shown, to whom, when, and through which destination |
| Stale, invalidated, withdrawn, or superseded | Later eligibility events affecting prior outputs; historical content and decisions are preserved under retention policy |

“Validated” denotes coverage by the required evaluations within their stated scope; it is not a declaration of universal correctness. Release requires verified binding, adequate freshness, authorized use, eligible dependencies, required evaluation completion, acceptable outcomes, and no unresolved hard failure. A safety component reports findings; orchestration owns the release decision and cannot waive hard failures.

Missing or failed mandatory evaluation shall withhold affected advice. A timeout, retry, partial response, or empty result shall not be interpreted as a pass. Status messages may explain unavailability without leaking an unevaluated treatment proposal. Clinically actionable streaming fragments shall not precede release.

Presentation shall preserve the release reference and content. Immediately before presentation, ClinRx shall verify the destination's patient, encounter or verified longitudinal-care context, request, and intended-use binding against the released output, and establish that release remains eligible under the applicable freshness and update-availability requirements. A delayed response shall not attach to a different active chart or workflow. Mismatched, superseded-request, or otherwise obsolete responses shall not be presented as current clinical advice; authorized historical review shall remain clearly distinguishable.

Before any ClinRx-enabled downstream clinical action, ClinRx shall reassess action-relevant identity, context, authorization, prerequisites, and continuing release eligibility. The human decision, authorized action request, and known action disposition shall be separately attributable and linked to the reviewed recommendation; unavailable confirmation shall remain unknown, not assumed completion. These checks do not authorize autonomous action excluded by Section 3.

Material changes detected before presentation or downstream action invalidate affected eligibility. If eligibility cannot be established, withhold current advice or action enablement and follow Sections 7 and 24; an earlier release is not sufficient permission. Reassessment and resumption require new decisions; recovery never silently reactivates an old release.

# 6. Validation of Exact Clinical Meaning

Validation shall cover both the structured candidate and the clinical meaning of the exact rendered content. It shall assess claim support, patient/context consistency, and fidelity of actions, negation, quantities, units, route, timing, conditions, exclusions, alternatives, uncertainty, and material warnings. Checking syntax or a structured intermediate alone is insufficient.

The approved method shall combine controls appropriate to the content and risk. Defined quantities and constraints require governed deterministic checks; clinical interpretation requires relevant evidence and clinical evaluation. An AI self-critique, agreement between models, or fluent explanation is not sufficient safety assurance. Evaluation methods themselves require validation against known unsafe and misleading outputs, including omissions and plausible near-misses.

Any semantic change after evaluation—including clinician edits, AI rewriting, translation, summarization, truncation, or omission of a material warning—creates a new revision requiring renewed evaluation and release. Purely visual changes are permitted only where meaning and warning visibility remain intact. Destination rendering, exports, accessibility transformations, and localization shall be assessed for these effects.

Where the system cannot establish required fidelity, it shall withhold the affected clinical content. A limited-review artifact follows Section 10 and is never a shortcut to actionable release.

Evaluation shall address the combined proposed plan, including clinically material interactions, cumulative effects, sequencing, mutually exclusive alternatives, prerequisites, and monitoring feasibility across recommendations and relevant existing or pending actions. Individually acceptable recommendations do not establish an acceptable combination. Concurrent recommendations from different capabilities shall be reconciled where they can affect one another; uncertainty about pending actions shall remain explicit.

The output shall distinguish “choose one” alternatives from cumulative instructions. Listing a prerequisite does not mean it is satisfied. The governed plan shall identify conditions that must be confirmed before action and prevent ClinRx-enabled action on an unmet or unknown safety-critical prerequisite. If safe plan coherence or required monitoring feasibility cannot be established, narrow or withhold affected advice, or require clinical reconciliation before renewed evaluation and release. Partial release remains subject to Section 10.

Exact-meaning assurance shall use clinically meaningful granularity and validated methods proportionate to risk. It does not mandate human approval of every sentence or output, or a separate record or service for every phrase; mandated human review and warning exceptions remain enforceable.

# 7. Patient and Encounter Binding and Context Freshness

Patient-specific use shall bind to a verified patient and encounter, or an explicitly verified longitudinal-care context when no encounter applies. Access authorization and identity verification are separate requirements. Ambiguous matching shall not combine records or fabricate a verified snapshot.

The intended-use policy shall define clinically justified freshness limits, source completeness requirements, relevant clinical times, and material-change triggers for each required input. One global expiry interval is insufficient. Record event, effective, recording, retrieval, and processing times as defined by DATA-001; “latest received” does not necessarily mean “latest clinically applicable.”

Before release, orchestration shall assess binding, snapshot adequacy, source availability, and material changes since capture. Critical changes, identity reassignment, inadequate freshness, or unresolved safety-critical conflicts require a new verified snapshot and evaluation or withholding. Pending or delayed sources shall remain explicit; absence from an incomplete feed is not a negative clinical finding.

Relevant triggers include corrected results, allergies, medication or administration changes, transfers, major organ-function changes, and initiation or cessation of organ support where they can affect the output. The intended use shall specify the reassessment mechanism and acceptable detection delay; monitoring shall detect failures of that mechanism.

Previously displayed affected advice shall be marked stale or withdrawn with a visible reason and risk-appropriate notification. A change unrelated to the advice need not invalidate it when a governed dependency assessment establishes that separation. Historical reconstruction shall not rewrite what the system knew at the earlier decision time.

Input suitability shall include temporal coherence, clinical phase, sampling conditions, and required relationships between events. Individually fresh values shall not be combined as if they describe one physiological state when that relationship is unsupported. Intended-use policies shall govern administration-relative sampling, cumulative exposure windows, changing organ support, and pre-/post-intervention measurements where relevant. Unknown or incompatible timing shall block interpretations that depend on it.

Continuing eligibility shall account for unavailable updates, lost source connectivity, and elapsed validity at presentation and action time as required by Section 5. The use policy shall define when renewed data or bedside confirmation is needed and which affected outputs must be withheld. Bedside confirmation shall be an attributable clinical assertion sufficient for the affected use, not a blanket acknowledgement that bypasses missing mandatory data or checks. ClinRx shall communicate its observation limits and shall never imply awareness of deterioration or events it has not observed. Interim and degraded behavior follows Section 24.

# 8. Evidence and Clinical Claim Support

Every clinically material claim shall link to an appropriate basis: patient fact revisions, validated calculation/rule executions, assessed evidence and knowledge versions, or governed inference inputs and validation references. A patient-specific conclusion shall preserve both its general clinical basis and the patient applicability assessment. Not every patient fact requires a literature citation.

Evidence assessment shall address the actual claim, population, setting, jurisdiction, effective period, limitations, and contradictory evidence. A real citation does not establish that its source supports the claim; retrieval rank, model familiarity, and publication status are not evidence strength. Recommendations shall not overstate causal conclusions or treatment benefit from predictive associations.

Clinical reviewers shall resolve material evidence disagreement through a documented, scoped interpretation or preserve uncertainty and abstain when no safe resolution exists. Local policy or patient-scoped knowledge exceptions require governed scope and rationale; greater specificity does not automatically override safety requirements.

Evidence recovery follows ARCH-001 Section 6.4 and DATA-001 Section 9. Where source recovery is restricted, retain permitted references, extracts or attestations, and the limitation. Qualified use requires intended-use authorization; inability to verify safety-critical support requires withholding. AI-generated knowledge proposals require separate review and publication governance.

The applicable institutional or jurisdictional policy authority, scope, material conflicts, and rationale for the selected interpretation shall be identifiable. Clinical evidence and contraindications shall remain distinguishable from formulary availability, operational restrictions, and jurisdictional constraints. An unavailable option shall not be portrayed as clinically inferior solely because of its availability. Unresolved safety-critical policy conflicts require escalation or withholding; local exceptions shall not silently amend shared safety requirements.

Evidence dependence shall be assessed where it affects support: copied claims, repeated reports, or sources derived from one underlying assertion shall not count as independent corroboration. Inference reuse and subsequent confirmation follow Section 15. Where lineage is unavailable, ClinRx shall not presume independence or increase certainty on that basis.

# 9. Uncertainty, Missing Data, and Conflicting Inputs

Missingness, origin, verification, temporal status, evidence strength, and applicability shall remain separate. Unknown, not measured, unavailable, conflicting, and not applicable shall not be converted into negative findings, zero, normal values, or fabricated patient facts.

Each use policy shall designate critical inputs and define how noncritical uncertainty affects output scope. An assumption may be used only where explicitly permitted and clinically justified, with its consequence visible; an assumption shall not fill a safety-critical gap. Conditional advice must specify its conditions and shall not imply that unverified conditions are satisfied.

Uncertainty communication shall identify what is unknown, why it matters, what advice is withheld or qualified, and what information or review could resolve it. Numeric probabilities require validated targets, horizons, calibration, and population applicability; generic AI confidence percentages shall not imply safety assurance.

Conflicting facts require the governed source-resolution policy and preserved alternatives. Selection shall not conceal unresolved safety-critical disagreement. Plausibility checks may flag anomalies but shall not silently correct an unusual value into a presumed normal one.

Diagnostic reasoning shall distinguish “not found in retrieval,” “not tested,” a negative result, and a clinically supported exclusion. Diagnostic exclusion, advice against investigation, and “no action” recommendations require support appropriate to the clinical question, timing, test limitations, and intended use. Absence of evidence shall not be converted into evidence of absence. Where relevant, retain unresolved serious alternatives and supported reassessment or escalation conditions; a differential shall not be presented as a confirmed diagnosis.

# 10. Abstention and Limited Review

ClinRx shall abstain from affected actionable advice when support, applicability, identity, critical data, required safety evaluation, or validated coverage is insufficient. Abstention shall be explicit and distinguish “cannot assess” from “no action needed” and “no detected violation.”

The response shall identify the reason at a useful level, unavailable capability, and safe escalation or information request where supported. It shall not reproduce the unsupported recommendation under a disclaimer. Delay and abstention can also cause harm; intended-use design shall evaluate those hazards and provide an established clinical fallback pathway without pretending that ClinRx has answered the question.

Partial release is permitted only where the released portion has independent support and complete applicable evaluation, and omission does not distort the remaining advice. Shared unresolved dependencies block all affected portions. Withheld parts and consequential limitations shall remain visible.

A separately governed limited-review workflow may show an unvalidated hypothesis or unresolved question to authorized reviewers. It requires patient binding where applicable, privacy, faithful presentation, explicit review-only labeling, and no treatment-action enablement. It is not an actionable recommendation release, and acknowledgement cannot promote it into one.

Limited-review governance shall define permitted reviewers, purpose, workflow, and downstream reuse, and evaluate foreseeable indirect influence on care. Removing an order button does not make persuasive unsupported treatment instructions safe to expose. Unsupported actionable instructions shall not be released through the review-only pathway; an unvalidated hypothesis or question may be shown only within the assessed review purpose and controls. Promotion into ordinary clinical advice requires the complete governed evaluation and release pathway.

Repeated prompting, requests for greater certainty, urgency, or requests to omit warnings or answer despite missing information shall not relax abstention, coverage, or warning requirements. Reconsideration may follow new relevant information or an independently approved policy change, with renewed evaluation; insistence alone is not evidence or authority.

# 11. Hard Stops, Warnings, and Override Authority

A hard stop is the withholding consequence of a non-overrideable hard failure. It blocks the affected ClinRx advice or action path, not the clinician's ability to deliver independent care.

| Condition | Required disposition |
|---|---|
| Failed patient/encounter binding or denied authorization | Withhold; resolve identity or permission through authorized processes |
| Unavailable mandatory evaluation, invalidated exact-meaning validation, or missing required decision traceability | Withhold until restored and evaluated |
| Unresolved safety-critical inputs, mappings, units, conversions, or context freshness | Withhold; correct or obtain adequate context and evaluate again |
| Unsupported actionable claim or use outside validated coverage | Abstain; no routine override |
| Suspended or ineligible mandatory dependency, or unapproved provider use | Withhold affected advice; use only an independently eligible validated alternative |
| Policy-designated absolute clinical prohibition | Withhold affected recommendation; a policy change requires separate governance |
| Explicitly designated overrideable advisory warning | Release only under the warning policy and any required authorized exception |

Warnings shall specify clinical meaning, severity, scope, required response, overrideability, and permitted roles. A caution needing no exception and a warning requiring an exception shall be distinguishable. Unclassified safety failures shall not default to overrideable.

An authorized warning exception requires a qualified clinician acting within clinical scope and institutional authority. Authority shall be specific to warning class and use; application administration rights, patient access, or developer status do not confer clinical override authority. Higher-risk warnings shall require additional review where the approved policy so specifies. If required reviewers are unavailable, the exception cannot proceed.

Record the warning and policy versions, exact content/context, clinician identity and authority, rationale, time, conditions, and duration or encounter scope. The original finding remains unchanged and visible with the exception. Acknowledgement alone is not an exception, and an exception never converts a failed check into a pass. Material context or content changes require renewed assessment of the exception.

Emergency urgency cannot waive parent hard failures. Independent clinician decisions may be recorded as such, without a successful ClinRx release claim. Reclassifying a warning or weakening a hard stop is a governed safety-policy change, never a per-request bypass.

# 12. Medication and Dose Safety

Medication support shall have a defined intended use and qualified clinical/pharmacy review proportionate to risk. Numerical dose limits and treatment protocols belong in governed knowledge and policies, not this standard.

Before releasing affected medication advice, required checks shall address:

- exact drug/ingredient, formulation, strength, route, indication, and relevant product distinctions;
- allergy and reaction information, contraindications, interactions, duplication, and reconciled current therapy;
- relevant age, weight and weight basis, pregnancy/lactation, organ function and trajectory, and supported special populations;
- applicable renal replacement therapy or other organ support, including changes affecting dosing assumptions;
- dose basis, per-dose versus daily total, frequency, interval, duration, loading versus maintenance, maximum limits, cumulative exposure, and last administration when relevant;
- preparation/concentration, dilution, infusion rate and duration, device or route constraints, and feasible delivery where part of the intended advice;
- required monitoring, reassessment, and stopping conditions supported by the applicable knowledge.

The use specification shall identify which checks are mandatory; an irrelevant check may be explicitly assessed as not applicable with rationale. A required check cannot be omitted because data or a service is unavailable. An empty medication or allergy feed shall not imply no medicines or no allergies.

Distinguish orders, administration, dispensing or reported use, and proposed treatment. Do not assume an order was administered or duplicate a loading dose through retries. Unclear product identity, dosing weight, renal estimate applicability, or route/strength shall block affected dose advice. Formula selection and special-population extrapolation require approved applicability; AI cannot invent an adjustment.

High-risk medication workflows shall assess the need for independent verification and make that requirement enforceable. Clinical release, order authorization, and administration checks remain separate, and downstream changes require renewed assessment.

Medication validation shall assess relationships among ingredient, formulation, strength, dose basis, route, concentration, volume, infusion rate, duration, frequency, and cumulative exposure wherever relevant, not merely the validity of each field. The prescribed quantity and intended delivered quantity shall be consistent under the actual product and preparation assumptions. Relevant weight/body-size basis, renal/hepatic adjustment method and applicability, and administration timing shall remain linked to that assessment. Safety-critical ambiguity or inconsistency requires withholding affected dose advice.

Duplicate-therapy checks shall account for ingredient overlap and combination products. Allergy assessment shall preserve reaction, severity, certainty, and relevant cross-reactivity; interaction assessment shall consider the proposed regimen, relevant current or pending therapy, and timing. These checks shall use governed knowledge, preserve unknowns, and participate in the combined-plan evaluation in Section 6. High-consequence control coverage and independent challenge are required by Section 17, including the adequacy of any decision about independent medication verification.

# 13. Units, Conversions, and Numerical Representation

Clinical values shall retain original and interpreted units, quantity meaning, source, and conversion provenance. Dimensional compatibility is necessary but not sufficient: per-dose versus per-day, absolute versus indexed organ-function estimates, body-weight bases, mass versus activity units, and product-dependent concentrations may have different clinical meanings.

Only validated, applicable conversion definitions may be used. Unknown units, ambiguous abbreviations, incompatible quantities, or missing conversion factors shall not be guessed. Preserve necessary precision and intermediate results; round only under the governed calculation and presentation policy. Validate threshold behavior and cumulative rounding effects.

Presentation shall prevent ambiguous decimals, lost signs, misplaced scales, and hidden unit changes. Locale changes, decimal separators, scientific notation, and translated units require fidelity assessment. A numerically correct result with misleading units or dose basis fails exact-meaning validation.

Computational precision shall remain distinct from measurement, assumption, and clinical uncertainty. Where plausible input variation or alternative justified assumptions could materially change the recommended action, the evaluation shall assess that sensitivity using a governed method and require clarification, supported qualification, or abstention as appropriate. A precisely calculated point value shall not imply certainty beyond its inputs or applicability. Quantified uncertainty requires a validated method; invented confidence intervals or unsupported numerical precision are not acceptable substitutes.

# 14. Rule and Calculation Validation

Definitions and executions remain distinct as required by DATA-001 Sections 29–30. Each definition shall specify scope, evidence basis, inputs and units, assumptions, boundaries, missing/conflicting-input behavior, dependencies, version, and expected outputs. Conflicting rules require governed resolution; execution order shall not determine authority.

Validation shall use independently reviewed reference cases and expected results, boundary and out-of-range cases, conversions, precision, temporal assumptions, missingness, and dependency failures. Test the implementation against the intended clinical definition, rather than merely checking it against itself. Formula transcription, input selection, and applicability errors require assessment even when arithmetic is correct.

Each execution shall retain actual input revisions, resolved versions, conversions, relevant configuration, result or failure, and sufficient reproduction information within authorized retention. Partial or failed execution shall not appear as a final normal result. Retry is a separately traceable execution.

Changes to formulas, rule thresholds, terminology, conversion methods, or rounding require impact assessment and proportionate regression validation. A deterministic implementation can still be clinically wrong or applied outside scope; software correctness alone does not establish clinical validity.

# 15. Deterministic and AI-Assisted Functions

Defined mathematical and algorithmic clinical calculations shall use validated deterministic implementations. AI may explain those results, summarize authorized inputs, and propose interpretations or candidates within validated scope. It shall not be the authoritative calculator, source of missing patient facts, publisher of clinical knowledge, or release authority.

Predictions and probabilistic estimates remain inferences even when repeatable. Their evaluation shall address the target, horizon, population, decision role, calibration where relevant, and downstream consequences. Prediction accuracy does not by itself establish treatment benefit.

AI outputs shall be assessed for invented facts or citations, unsupported conclusions, omission of relevant counterevidence, changed numbers, and lost conditions. Safety assurance shall not depend solely on generative AI. Fallback to another model is a governed clinical change, not just a transport decision.

Derivation, lineage, and clinically relevant uncertainty of AI-generated or inferred information shall be preserved when it is copied, summarized, exported, reimported, or reused in future reasoning, including through external clinical notes. Repetition, copying, clinician acknowledgement, and acceptance shall not constitute independent confirmation or silently promote an inference into an observed fact. Derived values likewise retain their inputs and method rather than gaining independent evidentiary status through reuse.

Genuine subsequent clinical confirmation shall be a separately attributable assertion with its own clinical basis, author or authorized source, and time, linked to the earlier inference without rewriting its origin. The record shall distinguish independent supporting observations from a clinician's assessment based on the same existing information. Dependent evidence shall not be counted as independent corroboration, and unavailable lineage shall not be treated as proof of independence.

Correction or withdrawal of an upstream assertion shall trigger identification and risk-appropriate reassessment of affected descendant inferences, recommendations, and eligibility, with stale/withdrawn designation and notification where required. A descendant shall not be retained as valid merely because it was previously accepted. Lineage limitations and authorized retention/disposition constraints shall be explicit; inability to establish safety-critical support requires qualification within supported scope or withholding, not fabricated reconstruction.

# 16. Human Oversight and Human Factors

Clinicians shall be able to understand, inspect, reject, and correct advice within realistic workflow constraints. At review, present patient/context identity, currency, proposed action, relevant rationale and evidence, material warnings, uncertainty, and alternatives where appropriate. Explanations shall reflect actual sources and calculations rather than fabricated rationales or claims of access to private model reasoning.

Meaningful human review shall be demonstrated through representative workflow evaluation, including time pressure, handover, interruptions, and incomplete information. Training and competence expectations shall be explicit. Each workflow shall identify who remains responsible for time-critical findings, pending results, monitoring, and handover; displaying advice does not establish that follow-up occurred. ClinRx shall not be relied on as an emergency detection or notification service unless that role is explicitly validated and approved. Where a reviewer cannot reasonably identify a critical failure, merely adding a confirmation button is not an adequate mitigation.

Alert prioritization and suppression policies shall balance missed hazards, automation bias, alert fatigue, and delay. Grouping or deduplication may reduce repetition only if material warnings and changed conditions remain visible. Suppression requires defined scope, duration, rationale, and reassessment; it shall not suppress hard failures. Monitor inappropriate acceptance, systematic dismissal, and misunderstanding, not just click rates.

Review, acknowledgement, acceptance, rejection, modification, and warning exception remain distinct attributable events. User feedback informs governed improvement; it shall not automatically retrain models, publish knowledge, or establish clinical truth.

# 17. Hazard Management and Residual Risk

Each intended use shall maintain a proportionate safety case connecting clinical benefits and hazards to controls, verification, clinical evaluation, and a documented residual-risk decision. It may be concise for a bounded capability; it need not introduce separate services or elaborate documentation for every control.

The hazard record shall identify hazardous situations and foreseeable harms, initiating conditions, affected populations and workflows, severity, likelihood and uncertainty, existing controls, verification evidence, residual risk, owner, review date, and status. Assess wrong advice, omitted advice, delayed advice, incorrect reassurance, wrong-patient use, overreliance, inequitable performance, failure of shared dependencies, and risks introduced by mitigations themselves.

Controls shall favor preventing unsafe states and constraining output before relying on warnings and user vigilance. Evaluate combined failures and common causes; several checks sharing one faulty source or model are not independent protection.

Clinical safety leadership shall explicitly accept, restrict, or reject residual risk against predefined criteria and benefit-risk rationale. Serious foreseeable harms shall not be hidden by an average performance score or assumed unlikely without evidence. Unknown likelihood remains uncertainty requiring management. Unacceptable residual risk blocks deployment; business urgency or general user acceptance cannot substitute for clinical risk acceptance.

New incidents, near misses, subgroup findings, changes, or foreseeable misuse shall reopen relevant hazards and acceptance decisions. Risk acceptance is scoped and reviewable, not permanent immunity from reassessment.

For each high-consequence capability, the safety case shall map material foreseeable hazards to prevention/detection controls, evaluation evidence, runtime prerequisites, and failure disposition. A suitably qualified clinical reviewer independent of the change's author shall challenge the adequacy of that coverage, including omitted hazards and common-source failures; compliance with a self-selected checklist alone is insufficient.

Where ordinary clinical review cannot reasonably detect a potentially serious failure, deployment shall require additional independent controls, narrower validated scope, or abstention from the affected use. Independence shall be justified by the failure modes addressed, not merely by using a second component or model. The need for human verification shall follow this assessment; this requirement does not mandate a second clinician for every output.

# 18. Governance Responsibilities

Roles describe accountability, not required departments. One person may hold multiple roles where competent and authorized, but approval of high-consequence capabilities or deployment changes and their residual-risk acceptance require a suitably qualified reviewer independent of the change's author. Conflicts of interest and delegated authority shall be recorded.

Capability/deployment approval establishes the authorized scope, versions, controls, and operating conditions under Section 26. Individual patient-output release is the orchestration decision under Section 5 within that approved scope. It shall enforce required evaluations and human exceptions but does not itself require a committee or manual approval of every output. Review effort for changes shall be proportional to clinical impact; small changes need not create new governance bodies.

| Accountable function | Required decisions and responsibilities |
|---|---|
| Clinical safety lead | Intended-use risk assessment, hazard ownership, hard-stop policy, residual-risk decision, suspension and clinical resumption approval |
| Clinical domain/pharmacy reviewers | Evidence applicability, medication policy, reference cases, clinical adjudication, warning-class authority |
| Knowledge/evidence steward | Controlled authoring, review, publication eligibility, dependency impacts, correction and retraction response |
| Engineering/validation owner | Implementation fidelity, independent evaluation controls, traceability, regression and recovery evidence |
| AI/model owner | Model eligibility, evaluation, subgroup limitations, provider/change assessment, drift investigation |
| Privacy/security owner | Patient-data boundaries, access and processing policy, security risks affecting clinical safety |
| Deployment/operations owner | Monitoring, escalation, containment, tested rollback, restoration, notification execution |
| Institutional clinical owner | Local workflow suitability, competent users, local policies, clinical escalation and follow-up |
| Release authority | Confirms all required approvals and evidence for the exact deployment scope; cannot waive unresolved hard failures or unacceptable residual risk |

Named owners, deputies, contact/escalation routes, and decision authority shall be assigned before deployment. Disagreement shall be escalated; unresolved blocking safety concerns prevent release. Authorized operations or safety personnel shall be able to suspend urgently without waiting for the normal release committee; resumption follows Section 24.

# 19. Model Validation and Change Control

Model eligibility shall be specific to its intended use, input requirements, population, setting, configuration, governed instructions, retrieval/tool boundaries, and output role. General benchmark performance or provider marketing is insufficient.

Evaluation shall use clinically representative, protected, versioned cases with independent reference assessment and adjudication. Assess data leakage and overlap with development/training data, reference-label uncertainty, relevant subgroups, rare severe failures, out-of-distribution inputs, missing/stale/conflicting context, robustness, omissions, unsupported claims, citation fidelity, and prompt manipulation. Report denominators and uncertainty, not only aggregate success percentages.

Predictive models require target/horizon assessment and calibration where probabilities are shown; threshold performance shall reflect the intended clinical decision. Generative models require assessment of variability and clinically harmful failure patterns across representative runs. Subgroup performance gaps shall lead to mitigation, restricted scope, or withholding where risk is unacceptable.

Model, prompt/instruction, tool, retrieval, preprocessing, configuration, or provider changes shall undergo documented impact assessment, proportionate revalidation, hazard review, and approval before affected clinical promotion. Fixed interfaces do not imply unchanged behavior. No uncontrolled online learning or silent self-update is permitted in clinical use.

Where precise model versions are unavailable, governance shall assess available identification, provider change controls, monitoring, and evaluation evidence and explicitly authorize a bounded use or decline it. “Unknown” metadata is not approval. Unexpected behavior or a suspected silent change shall trigger restriction or suspension when eligibility cannot be established.

During investigation of suspected drift or silent model/provider change, interim eligibility shall follow Section 24. Bounded acceptance of unavailable model metadata shall identify the compensating controls, reassessment conditions, and review responsibility; uncertainty cannot justify indefinite use after those controls cease to operate.

# 20. Knowledge and Evidence Change Control

Clinical knowledge shall follow DATA-001's Draft → Under Review → Approved → Published lifecycle with later Superseded or Retired governance events. Suspension or restriction changes eligibility without rewriting published content. Approved, published, effective, applicable, and deployed remain distinct.

Changes to knowledge, sources, interpretations, rules, terminology mappings, safety policy, and local variants require version-bound clinical, knowledge, and engineering review as applicable. Assess changed dependencies, conflicting guidance, jurisdiction, effective periods, clinical cases, and affected historical outputs. A newer version is not automatically appropriate for every institution or patient.

Retractions, urgent safety notices, and materially incorrect content shall trigger prompt eligibility review, containment, and risk-based notification/reassessment. Accelerated correction may shorten scheduling but shall not skip required validation or authorization. Historical decisions retain their original references; corrected advice receives a new linked decision.

Review schedules and event triggers shall be assigned by risk and source volatility. Overdue review shall trigger a documented eligibility decision; a date alone neither proves invalidity nor permits indefinite continued use. Retrieval indexes, caches, and downstream consumers shall enforce suspensions and eligibility changes.

# 21. External AI and Provider Governance

Provider use shall require approved data purpose, minimum necessary content, processing location, subprocessors, retention/deletion, secondary use/training restrictions, security arrangements, and incident/change notification expectations. Provider defaults shall not determine patient-data policy.

Clinical eligibility shall cover service behavior, available model identity, tool access, output limitations, availability, timeout behavior, and evidence needed for investigation. Contracts and technical compatibility cannot substitute for clinical validation. Provider outages shall not trigger unvalidated fallbacks or transmission through an unauthorized service.

Material changes to processing boundaries or behavior require renewed review before affected use continues. If approved boundaries cannot be maintained, suspend that processing and use only independently authorized, validated alternatives. Local or institution-hosted models remain subject to equivalent safety and access controls.

# 22. Privacy and Security Boundaries Relevant to Safety

Production patient-data integration requires approved privacy, security, retention, and access controls. Apply authorization, minimization, tenant isolation, and integrity protection to patient facts, snapshots, retrieval, prompts, tool calls, outputs, logs, exports, and recovery copies. Wrong-tenant retrieval and unauthorized disclosure are safety-relevant failures as well as security events.

Clinician text, external documents, retrieved content, and model outputs are untrusted inputs to the control plane. They shall not alter governing instructions, permissions, publication status, or release policy. Model-proposed tool requests require independently enforced authorization and validated arguments. Secrets shall not become clinical content.

Threat assessment shall include prompt injection, data or knowledge tampering, poisoned sources, compromised credentials, and service disruption affecting care. A suspected integrity compromise shall quarantine affected data or capabilities until eligibility is established. Emergency access procedures, if separately approved, do not waive identity, exact-meaning, or mandatory safety evaluation requirements.

Retention and authorized deletion/redaction follow DATA-001 Section 45.1. Immutability means no silent clinical rewrite, not indefinite retention. Record permitted disposition information without recreating deleted sensitive content; disclose resulting investigation or reconstruction limits.

# 23. Interoperability and Data-Quality Failures

Successful transport, parsing, or schema conformance is not clinical verification. Source transformations shall preserve identity namespaces, original values, code-system versions where available, clinical time, units, corrections, and provenance.

Mappings shall distinguish equivalent, broader, narrower, related, conflicting, and unresolved meanings. Unknown units, uncertain patient matching, material loss, duplicate or out-of-order events, delayed feeds, and unsupported status codes shall have explicit failure or issue states. Do not silently normalize them into usable facts.

Unresolved safety-critical issues block affected recommendations. Qualified use of incomplete or lossy data requires a recorded policy assessment that the limitation cannot invalidate that particular use, with visible limitations and authorization. Rejection or quarantine preserves permitted source references for investigation and does not remove privacy obligations.

Integration validation shall cover source corrections, medication discontinuation, patient merges/splits, encounter changes, time-zone ambiguity, replay, and partial source outages where relevant. Downstream exchange shall preserve release status, warnings, exact content, and subsequent withdrawal; imported or exported content does not gain a new approval merely by transfer.

Exchange and transformation shall preserve derivation and uncertainty under Section 15, including AI-origin content embedded in external records. Imported text shall not be presumed independently verified merely because it comes from a clinical system. Any loss of lineage shall be recorded and assessed for the intended use.

# 24. Incidents, Rollback, and Emergency Suspension

Deployments shall define risk-based incident severity, response time objectives, escalation routes, and accountable responders. Credible severe hazards and near misses shall trigger immediate triage and proportionate containment without waiting for proof of actual harm.

The response shall identify affected patients, outputs, versions and dependencies; preserve permitted evidence; restrict or suspend affected functions; communicate unavailable capabilities; and arrange risk-appropriate clinical notification and reassessment. Notification shall identify actionable consequences and a responsible clinical recipient. Delivery failure and unresolved follow-up require escalation; issuing a notification alone does not prove that care was reviewed.

Suspension shall be enforceable across applicable workflows, retrieval, caches, providers, and downstream consumers. Scope may be narrow only where unaffected capabilities are demonstrably independent. A whole-workflow suspension is required where safe separation cannot be established.

Rollback shall use a known eligible combination of software, model, knowledge, rules, policy, and integration dependencies. An older version may also be unsafe or incompatible; rollback is not inherently a safety resolution. Restoration shall preserve withdrawal, access, and stale-state controls, avoid duplicate downstream actions, and reassess context before new release. Downtime behavior and clinical fallback shall be tested.

Resumption requires documented cause assessment, verified mitigation, proportionate regression and clinical evaluation, residual-risk review, and authorized clinical/operational approval. Root-cause investigation, corrective actions, effectiveness checks, and required external reporting shall have owners; applicable reporting obligations are determined by qualified governance personnel.

Interim disposition shall be defined for suspected model or source changes, unavailable dependencies or surveillance, loss of updates, and partial system failure. While investigation proceeds, affected clinical use may continue only with a documented, authorized basis that the remaining controls support the specific capability and risk. Otherwise restrict or suspend it. That assessment shall have an owner and review/stop conditions; no interim decision may waive a hard failure.

A degraded mode shall remain within independently established validated scope, disclose missing capabilities, and never imply completion of unavailable checks. Mandatory update or monitoring failure shall block affected use when its safety case depends on that function and no validated alternative preserves eligibility. Source recovery and restoration do not themselves establish that delayed or queued recommendations remain current; Sections 5 and 7 apply.

For controlled consumers, enforce withdrawal and current-use restrictions. Where a disconnected export cannot be recalled or updated, retain that limitation and use risk-appropriate communication and reconciliation; do not claim that every external copy has been withdrawn.

# 25. Audit, Provenance, and Reproducibility

Implement DATA-001 Sections 31–39 record semantics rather than inventing a parallel audit model. Retain the chain from intended use and authorized inputs through exact artifact versions, executions, AI interactions, candidate/rendering, evaluations, release or withholding, actual presentation, human actions, and subsequent eligibility events.

Decision records shall identify authority, time, reasons, coverage and limitations, freshness, permitted warning exceptions, and the exact content/context reviewed. Required traceability shall be available before clinical release; a failure to create the required record blocks the affected release. Technical storage mechanisms belong in implementation specifications.

Deterministic reproduction requires retained inputs, versions, conversions, precision, and necessary execution/configuration information. AI reconstruction preserves actual authorized inputs and outputs; it does not promise identical regeneration or private model reasoning. Re-evaluation using current information is a new decision, not reconstruction of the historical one.

Audit integrity, access, and authorized disposition shall be controlled. Unavailable evidence, provider metadata, deleted data, and incomplete presentation confirmation shall remain explicit limitations. Do not claim a clinician saw or acted on content without the corresponding event evidence.

Investigation records shall preserve why decision-relevant information was absent from the evaluated context, to the extent knowable: source availability/completeness, relevant late arrivals, retrieval selection or exclusion rationale, material omission or truncation during context preparation, and detected update failures. Distinguish information known not to have existed from information whose existence is unknown, information unavailable at decision time, information available but not selected, and information selected but lost during processing.

These records shall support investigation of omission and lineage failures under Section 15 without requiring unlimited source retention or a record for every irrelevant item. Preserve permitted metadata and material rationale at clinically meaningful granularity, under authorized retention, and state unknown causes and reconstruction limits honestly.

# 26. Clinical Evaluation and Release Gates

Before evaluation, define intended-use-specific acceptance criteria, clinically meaningful outcomes, unacceptable failures, reference/adjudication methods, populations, subgroup analyses, and statistical uncertainty where relevant. Numerical targets belong in the approved evaluation plan; this standard does not invent universal thresholds.

Evaluation shall examine the combined system and human workflow, including omission, delay, incorrect reassurance, misuse, and degraded behavior. Retrospective performance alone may not establish effectiveness in practice. Prospective or supervised evaluation shall be required when necessary to resolve consequential uncertainty; any decision that it is unnecessary requires documented clinical rationale. Evaluation involving patients or patient data requires applicable institutional, privacy, and ethical authorization.

| Gate | Required evidence and decision |
|---|---|
| Foundation and scope | Approved applicable standards, resolved blocking legacy issues, intended use, owners, hazards, and evaluation plan |
| Patient-data readiness | Approved identity, integration, security, privacy, retention, and data-quality controls before real patient integration |
| Technical and content readiness | Verified rules/calculations, knowledge eligibility, exact-meaning controls, provenance, hard failures, and failure-path testing |
| Clinical and human readiness | Clinical adjudication, appropriate population/subgroup evidence, human-factors results, limitations, training, and residual-risk acceptance |
| Operational readiness | Working monitoring, accountable clinical follow-up, incident response, suspension, tested recovery, and eligible fallback |
| Deployment authorization | Version-bound approvals for the exact capability, site, users, population, configuration, release scope, and review/stop criteria |

A failed blocking criterion shall not be averaged away by other successes. Exceptions may narrow deployment scope with supporting evidence, but cannot waive hard failures or declare unsupported use validated. Staged rollout requires explicit exposure limits, supervision, stop criteria, and review; the term “pilot” does not exempt patient-care use from safety gates.

Release approval shall record unresolved nonblocking limitations and follow-up owners. Passing software tests, completing automated checks, or receiving clinician acceptance does not establish universal clinical validity or treatment benefit.

Evaluation shall include proportionate adversarial cases for reimported inferences and dependent corroboration, patient/encounter switches during processing, loss of context updates, incompatible concurrent recommendations, and temporally incoherent inputs. Verify that supported partial outputs, limited-review artifacts, and repeated prompting cannot bypass abstention or required warnings. These are capability-level acceptance scenarios, not a requirement for manual review of every future output.

# 27. Monitoring and Post-Deployment Surveillance

Every deployment shall have a risk-based surveillance plan with named owners, review intervals, metrics, denominators, investigation thresholds, and action/suspension triggers. Monitor both system availability and clinical performance; absence of incident reports is not evidence of absence of harm.

Measures shall include relevant unsupported or incorrect claims, omissions, unsafe dose or unit outputs, wrong-context events, stale-data use, abstention and warning rates, overrides and their appropriateness, alert burden, latency, source failures, and subgroup performance. Assess drift in populations, practice, evidence, source quality, model behavior, calibration, and workflow reliance. Feedback capture shall include near misses and delayed outcomes where ascertainable.

Use representative review of apparently successful outputs as well as reported failures. Interpret changing rates in context: higher abstention may be an appropriate response to worse inputs, while lower alerts may reflect a broken check. Monitoring failure itself requires response when the safety case relies on surveillance.

Signals shall trigger investigation, hazard reassessment, restriction, correction, or suspension proportionate to risk. Findings shall enter controlled change and revalidation; monitoring shall not automatically authorize model learning or policy relaxation. Periodic continued-use review shall confirm that benefit-risk, intended-use fit, owners, and controls remain adequate. Retirement of a capability or provider shall include communication to affected users, disposition of outstanding clinical follow-up, removal of current-use eligibility, and preservation or authorized disposition of historical records. Withdrawal of decision support shall not silently abandon an established monitoring responsibility.

# 28. Adoption, Conformance, and Open Decisions

Conformance requires demonstrable evidence for the applicable requirements and a traceable, approved rationale for items assessed as not applicable. Documentation completeness is not operational conformance. This Draft does not assert that ClinRx currently implements these controls.

Before adoption and patient-care implementation, governance shall resolve or approve:

- named clinical, architecture, knowledge, engineering, privacy/security, operational, and release owners;
- initial intended uses, exclusions, risk tiers, mandatory inputs/checks, and context freshness policies;
- clinical warning taxonomy, permissions, exception conditions, escalation, and emergency contacts;
- acceptance criteria, reference cases, clinical evaluation plans, hazard records, and residual-risk authority;
- provider/data-processing eligibility, retention, integration profiles, monitoring thresholds, and recovery procedures;
- blocking legacy reconciliation identified in DATA-001 Section 50.1 and parent-standard approval requirements.

These are bounded implementation and governance prerequisites, not permission to delay every prototype or invent a complete future platform. Development may proceed through reviewed, limited capabilities using appropriate test data, while preserving the clinical release gates. Detailed schemas, product-specific mechanisms, numerical thresholds, and operational runbooks shall live in their owning specifications and link back to these invariants.

# 29. Informative Reference

The external reference below informs lifecycle review and is not incorporated as a claim of regulatory conformance. ARCH-001 and DATA-001 remain the normative internal basis for this Draft.

- [FDA, Health Canada, and MHRA: Good Machine Learning Practice for Medical Device Development — Guiding Principles (2021)](https://www.fda.gov/media/153486/download). Informative support for multidisciplinary evaluation, representative data, human–AI team assessment, clinically relevant testing, and monitoring of deployed models. Applicability and any current jurisdiction-specific requirements require separate qualified assessment.

# 30. Document Control

**Document ID:** CLINRX-SAFE-001

**Version:** 0.2

**Status:** Draft

**Date:** 2026-09-25

**Effective Date:** Pending approval

**Owner:** ClinRx AI

**Parent / Related Standards:** CLINRX-ARCH-001 v1.1 Draft; CLINRX-DATA-001 v0.3 Draft

**Approval:** Pending architecture, clinical safety, clinical domain, knowledge, engineering, privacy/security, and operational review as applicable

**Revision Basis:** Version 0.1 established the initial clinical safety and AI governance draft aligned to the installed parent standards. Version 0.2, dated 2026-09-25, incorporates the substantive safety review: inference lineage and circular corroboration; presentation/action-time eligibility; combined-plan safety; high-consequence coverage; temporal, medication, population, diagnostic, uncertainty, policy, limited-review, degraded-mode, and omission-reconstruction controls. It clarifies terminology and capability/deployment approval versus patient-output release while retaining the existing architecture. Parent and legacy documents are unchanged. Internal risk tiers remain proportional assurance categories, not regulatory classifications.

Changes shall preserve version history and undergo proportionate review. Adoption requires named approvals, resolved blocking issues, and an effective date. Completion of drafting or checks does not constitute clinical release authorization.
