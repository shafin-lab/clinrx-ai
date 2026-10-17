# CLINRX-DATA-001
# Clinical Data & Knowledge Standard

**Project:** ClinRx AI

**Document ID:** CLINRX-DATA-001

**Version:** 0.3

**Status:** Draft

**Date:** 2026-09-25

**Parent Standard:** CLINRX-ARCH-001 Version 1.1 candidate Draft

---

# 1. Purpose

This document defines the conceptual clinical data and knowledge architecture for ClinRx AI.

It establishes the fundamental information objects, relationships, identifiers, versioning principles, provenance requirements, temporal semantics, applicability, jurisdiction, terminology, and clinical data representation rules that will guide future database and application implementation.

This document defines the clinical information model before implementation in PostgreSQL, Supabase, or another persistence technology.

This revision uses CLINRX-ARCH-001 Version 1.1 candidate Draft as its authoritative candidate parent for this alignment, not the incomplete repository Version 1.0. Both standards remain Draft and require approval. “Shall” and “must” express proposed requirements; “should” expresses a recommendation whose exception requires a documented rationale. Conceptual fields and records below express clinical meaning and durable relationships, not physical tables, serialization formats, or deployment components.

---

# 2. Core Principle

ClinRx shall distinguish between:

1. Clinical knowledge
2. Clinical evidence
3. Patient-specific clinical data
4. Clinical rules
5. Clinical calculations
6. Recommendations
7. Audit information

These concepts must not be collapsed into a single generic data structure.

---

# 3. Logical Data Architecture

The long-term ClinRx data architecture is:

```text
                         CLINRX DATA
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
   KNOWLEDGE              EVIDENCE              PATIENT
   OBJECTS                OBJECTS               CONTEXT
       |                      |                      |
       +-----------+----------+----------------------+
                   |
                   v
             CLINICAL RULES
                   |
                   v
             CALCULATIONS
                   |
                   v
                SAFETY
                   |
                   v
            RECOMMENDATIONS
                   |
                   v
                 AUDIT
```

The architecture is intentionally separated into distinct conceptual domains. The diagram expresses conceptual relationships, not a mandatory execution order; provenance and audit apply throughout the workflow.

ARCH-001 Section 5 owns workflow sequencing. The information model shall support candidate → rendering → validation → release → presentation, with distinct records for the content, evaluations, and decisions in Sections 31–33 and 38. An information-domain diagram does not authorize bypassing that sequence.

---

# 4. Knowledge Object

A Knowledge Object represents a structured piece of clinical knowledge used by ClinRx.

A Knowledge Object must have a stable identity independent of its version.

Minimum conceptual fields include:

- knowledge_id
- version
- title
- object_type
- domain
- status
- scope
- jurisdiction
- effective_period
- provenance
- review_metadata
- dependencies

A published Knowledge Object version is immutable.

If clinical knowledge changes, a new version must be created rather than modifying the previously published version.

Published clinical content and its exact dependencies are distinguished from later governance events such as suspension, supersession, and retirement. Those events alter eligibility without rewriting content. Historical retention and authorized privacy-related disposition follow Section 45; immutability is not permission for unlimited retention.

---

# 5. Knowledge Object Types

ClinRx may represent multiple classes of clinical knowledge, including:

- Clinical State
- Disease
- Syndrome
- Drug
- Drug Class
- Microorganism
- Laboratory Concept
- Diagnostic Concept
- Procedure
- Clinical Rule
- Clinical Calculation
- Treatment Principle
- Dosing Rule
- Monitoring Rule
- Safety Rule
- Interaction Rule
- Recommendation
- Guideline-derived Knowledge
- Institutional Knowledge

The object taxonomy may evolve, but new object types must preserve the separation between knowledge, evidence, patient data, rules, calculations, and recommendations. Rule, calculation, and recommendation knowledge types describe reusable definitions; executed rules, calculation results, and patient-specific recommendations remain separate records. This preserves the intended concept-versus-decision separation, but does not establish an approved taxonomy mapping to CAS-KOS-001; unresolved legacy terminology is recorded in Section 50.

---

# 6. Clinical Concept Identity

Clinical concepts must have stable internal ClinRx identifiers.

Where appropriate, ClinRx concepts should map to recognized external terminologies.

Potential terminology systems include:

- SNOMED CT
- LOINC
- RxNorm
- ICD
- ATC
- UCUM

External terminology identifiers must not replace the ClinRx internal identity.

A ClinRx concept may have multiple terminology mappings.

Terminology mappings must include the terminology system and version where known.

A terminology mapping is an identifiable, versioned relationship, not just a code attached to a concept. It shall retain:

- the internal concept identity and relevant version, and the external code plus namespace/system and release/version where known;
- the direction and assessed relationship, such as equivalent, broader, narrower, or related, rather than assuming equivalence;
- mapping source, method or author, assessment time, provenance, reviewer, review status, and change reason;
- applicability, effective period, limitations, uncertainty, and unresolved or deprecated status where relevant.

An unknown terminology version shall be explicit. Candidate, conflicting, unmapped, or lossy mappings shall remain distinguishable from reviewed mappings eligible for a particular use. Terminology mappings do not themselves authorize clinical use; unresolved interoperability information follows Section 40.

---

# 7. External Identifiers

Clinical objects may contain identifiers from external systems.

Examples include:

- hospital identifiers
- laboratory identifiers
- medication identifiers
- national identifiers
- terminology identifiers
- source-document identifiers

External identifiers must remain distinguishable from the stable ClinRx identifier.

External identifiers shall include their assigning authority or namespace, identifier value, entity type, and relevant source/version and period of validity. They shall not be treated as globally unique without that context. Patient/encounter identity linkage is a separately governed assertion with verification status and provenance; ambiguous candidate matches are not verified links and must not combine patient records (Sections 19 and 40).

---

# 8. Knowledge Lifecycle

Knowledge Objects shall support an explicit lifecycle.

Conceptual lifecycle states include:

- Draft
- Under Review
- Approved
- Published
- Superseded
- Retired

A lifecycle state describes governance status and must not be confused with clinical validity or evidence strength.

Only appropriately governed knowledge may be used for production clinical recommendations. Lifecycle transitions must be recorded as governance events without rewriting published version content. Historical references must identify the exact version, not only the stable knowledge_id.

Approved, Published, effective, applicable, and deployed are distinct concepts. Production selection shall retain the eligibility assessment for scope, jurisdiction, time, exact dependency versions, and authorized intended use. Suspension or restriction shall be representable as a separate governed eligibility event with actor, reason, affected versions, and time, without silently changing the lifecycle vocabulary. Authoring, historical retrieval, and current clinical use must remain distinguishable.

---

# 9. Evidence Object

Evidence is represented independently from the Knowledge Object.

An Evidence Object may represent:

- clinical guideline
- systematic review
- meta-analysis
- randomized trial
- observational study
- regulatory document
- professional society statement
- institutional protocol
- authoritative reference
- other documented evidence source

An Evidence Object should contain sufficient provenance to identify the underlying source.

Conceptual fields include:

- evidence_id
- source_type
- title
- publisher
- publication_date
- version
- source_identifier
- citation
- access_information
- evidence_scope
- applicability
- review_metadata

Evidence identity, the assessed source version, and a retained source snapshot are distinct references. Where legally and technically permitted, retain recoverable content or a source snapshot for the material actually used, its stable reference, capture/retrieval time, origin, extent, and access/retention restrictions. An assessed extract must identify its source location and limits; it is not automatically a complete source copy.

Where recovery is restricted or cannot be assured, record that limitation, permitted identifiers/extracts or attestations, and the governed decision permitting qualified use or withholding the affected output. A citation alone does not prove historical recoverability. Source corrections, withdrawals, or retractions shall be representable without erasing the earlier assessment; link affected knowledge and outputs for reassessment under Section 34.

---

# 10. Knowledge-Evidence Relationship

Knowledge Objects and Evidence Objects must remain separate.

A Knowledge Object may reference one or more Evidence Objects.

The relationship should capture, where applicable:

- supporting evidence
- contradicting evidence
- contextual evidence
- historical evidence
- evidence applicability
- evidence interpretation
- date of assessment

This allows ClinRx to distinguish the clinical knowledge representation from the underlying evidence supporting it.

The relationship shall identify the exact knowledge and evidence versions assessed, the assessed claim or source location, interpretation, reviewer, and applicability. A new interpretation creates a traceable assessment rather than silently replacing the support used by an earlier output.

---

# 11. Evidence Applicability

Evidence must not automatically be assumed to apply universally.

Applicability may depend on:

- population
- age
- sex where clinically relevant
- disease state
- organ function
- treatment setting
- geographic region
- healthcare system
- institutional practice
- time period

ClinRx should preserve applicability information rather than reducing evidence to a single generic strength value.

---

# 12. Conflicting Evidence

ClinRx must be capable of representing conflicting evidence.

Conflicting evidence must not be silently overwritten or discarded.

Where credible sources disagree, the system should preserve:

- the individual sources
- their publication/version information
- the affected clinical concept
- the nature of the disagreement
- the applicable population or context
- the date of assessment

The interpretation used by ClinRx must remain traceable to the underlying sources.

---

# 13. Evidence Authority

Evidence sources may have different authority for different purposes.

Authority may depend on:

- regulatory status
- professional society
- national guideline
- institutional protocol
- peer-reviewed literature
- local expert consensus

Authority is contextual and must not be represented as a universal ranking without defining the intended clinical use.

---

# 14. Knowledge Scope

Knowledge must have an explicit scope.

Conceptual scope levels include:

- Global
- National
- Regional
- Institutional
- Hospital
- Department
- Patient-specific

More specific knowledge may refine or constrain broader knowledge.

Local knowledge must not silently overwrite global knowledge without preserving the relationship and provenance.

Patient-specific scope, if supported, denotes a separately governed knowledge exception or constraint with its own identity/version, owner, rationale, review, effective period, and explicit patient binding. It is not a patient observation, diagnosis, order, inference, or recommendation execution. Those remain patient-specific clinical records. The exception must not be promoted into reusable general knowledge or substituted for a patient fact; it requires patient-data access and retention protection (Sections 19 and 45). Local refinement does not automatically authorize overriding a broader safety requirement.

---

# 15. Jurisdiction

Knowledge may be jurisdiction-specific.

Jurisdiction may include:

- country
- state/province
- healthcare system
- institution
- hospital
- department

Jurisdiction must be represented separately from knowledge scope.

This allows the same clinical concept to have different applicable rules in different healthcare environments.

---

# 16. Temporal Semantics

Clinical knowledge and patient data are inherently time-dependent.

Knowledge should support:

- publication date
- effective date
- review date
- supersession date
- retirement date

Patient data should separately support:

- event time
- recording time
- effective time
- retrieval time
- processing time

These timestamps must not be collapsed into a single generic timestamp.

---

# 17. Effective Periods

Knowledge may have an effective period.

A knowledge version may be:

- published but not yet effective
- currently effective
- effective historically
- superseded
- retired

Clinical retrieval must consider temporal applicability.

A current recommendation must not automatically use a historical knowledge version when a newer applicable version exists.

---

# 18. Knowledge Dependencies

Knowledge Objects may depend on other Knowledge Objects.

Examples:

- a dosing rule depends on a drug concept
- a renal dosing rule depends on renal function concepts
- an antimicrobial recommendation depends on a microorganism concept
- a recommendation depends on a clinical state

Dependencies must be explicitly representable.

The system should be capable of determining which upstream objects affect a published clinical output.

Definitions may declare dependency relationships, but execution and release records shall pin the exact resolved versions actually used. Dependency provenance shall support finding outputs affected by changed, withdrawn, or suspended artifacts. Conceptual relationships may be cyclic; execution records must identify the governed evaluation method and any dependency failure rather than implying uncontrolled recursive execution.

---

# 19. Patient Context

Patient Context is a first-class ClinRx domain.

Patient Context represents the clinical state of a specific patient at a specific point in time.

It may include:

- demographics
- diagnoses
- symptoms
- vital signs
- laboratory results
- microbiology
- medications
- procedures
- organ function
- allergies
- devices
- physiological measurements
- clinical events
- derived clinical values
- relevant historical information

Patient Context must remain separate from general clinical knowledge.

A patient-specific workflow shall reference a verified patient identity and encounter, or an explicitly verified longitudinal-care context when no encounter applies. Represent the binding assertion, verification method/source, verifier or authorized system, time, status, and unresolved ambiguity. Access authorization is distinct from identity verification. Record source completeness, relevant clinical times, and freshness assessments; being bound to a patient does not make data current. Snapshot and release binding requirements are owned by Sections 33 and 31.

---

# 20. Clinical Data Categories

ClinRx shall distinguish different types of patient-specific clinical data.

## 20.1 Observation

A directly observed or measured clinical value.

Examples:

- blood pressure
- temperature
- serum creatinine
- INR
- platelet count
- oxygen saturation

## 20.2 Condition

A clinical diagnosis, disease state, syndrome, or problem.

## 20.3 Medication Order

A prescribed or intended medication treatment.

## 20.4 Medication Administration

A medication actually administered to the patient.

## 20.5 Procedure

A clinical procedure performed, planned, or documented.

## 20.6 Derived Value

A value calculated from other patient data.

Examples:

- creatinine clearance
- MELD score
- corrected sodium
- calculated dose

## 20.7 Inference

A clinically inferred state generated from available evidence.

Inferences must remain distinguishable from directly observed facts.

The category describes the clinical record, while origin, verification, uncertainty, and temporal status are separate dimensions. A reported observation may retain its external measured origin without being represented as a direct measurement performed by ClinRx. Inferred states and predictive/probabilistic estimates shall retain identified inputs, method/model and version, target outcome and time horizon where relevant, applicability, uncertainty, and intended-use validation references. Repeatable model execution does not turn an inference into an observed fact or establish treatment benefit. Deterministic derived values link to calculation executions (Section 30).

---

# 21. Patient Fact Metadata

Each patient-specific clinical fact should be capable of carrying metadata such as:

- source
- author
- timestamp
- unit
- reference range where applicable
- verification status
- data quality
- provenance
- clinical context

The metadata must allow ClinRx to determine how a fact entered the system and how trustworthy or applicable it is.

Durable patient facts shall have stable identity, revision identity, verified or unresolved patient/encounter linkage as appropriate, source identifiers, origin, clinical category, and the temporal dimensions in Section 26. Corrections shall preserve the relationship to the superseded record and correction reason, subject to Section 45. Unit and reference-range metadata include the source representation and context needed for interpretation. A generic timestamp alone is insufficient.

---

# 22. Observed, Derived, Inferred, and Reported Data

ClinRx must distinguish at least:

- Observed
- Derived
- Inferred
- Reported

For example, a reported diagnosis from an outside record is not equivalent to a laboratory result directly measured by the hospital laboratory.

Derived and inferred information must preserve their source inputs and method where clinically relevant.

Patient-fact origin is not the same as clinical-output production classification. Sections 31–32 distinguish deterministic, rule-derived, evidence-derived, and AI-generated/inferred claims, including combinations, without replacing these origin categories. Clinician review or acceptance does not rewrite how a fact or claim was produced.

---

# 23. Verification Status

Patient data should support verification states.

Examples include:

- Unverified
- Verified
- Clinician-confirmed
- System-generated
- Patient-reported
- Conflicting

These labels describe different dimensions: Unverified, Verified, and Clinician-confirmed describe verification; System-generated and Patient-reported describe origin; Conflicting describes conflict state. Implementations must represent these dimensions separately so that, for example, a patient-reported fact can also be clinician-confirmed. Verification status must not be interpreted as evidence strength.

---

# 24. Data Quality

Patient data should support explicit data-quality representation.

Potential dimensions include:

- completeness
- timeliness
- consistency
- source reliability
- unit validity
- plausibility
- duplication
- missingness

Poor-quality data should not silently become high-confidence clinical facts.

---

# 25. Uncertainty

ClinRx must represent clinically meaningful uncertainty.

Uncertainty should not be reduced to a generic AI confidence score.

Examples include:

- missing value
- stale value
- conflicting measurements
- uncertain diagnosis
- incomplete medication history
- ambiguous timing
- insufficient evidence

Where uncertainty affects a recommendation, it should be surfaced to the clinical reasoning and safety layers.

Uncertainty records shall distinguish unknown, missing, not measured, and not applicable from negative findings. They shall identify what is uncertain, its source and implications, and the affected use rather than manufacturing a universal confidence percentage. Where a validated probabilistic model produces a probability, retain its target and applicability and references to calibration/validation evidence; a model estimate is not a general assurance of safety.

---

# 26. Clinical Time

Clinical data must support multiple temporal dimensions.

At minimum, ClinRx should distinguish:

- Event time: when the clinical event occurred
- Recording time: when it was documented
- Effective time: when the information became applicable
- Retrieval time: when ClinRx obtained the information
- Processing time: when ClinRx processed the information

This is necessary for reproducibility of historical clinical decisions.

Clinical times shall retain relevant time-zone/offset, precision, uncertainty, and intervals where needed; unknown times shall not be fabricated. Decision, execution, release, presentation, correction, and governance-event times must remain distinguishable. Historical queries shall distinguish information applicable at the clinical event time from information available to ClinRx at the decision time (Section 37).

---

# 27. Historical and Current State

Patient Context must support both:

- current clinical state
- historical clinical state

Historical values must not be overwritten simply because a newer value exists.

The system should be able to reconstruct the patient state at a previous clinical time.

Late-arriving information or corrections may change the reconstructed clinical history without changing what a prior decision actually knew. New evaluations create new linked outputs; they do not rewrite earlier snapshots. Current eligibility, staleness, and withdrawal are later events, not changes to the historical content. Authorized retention/deletion limits follow Section 45.

---

# 28. Conflicting Patient Data

ClinRx must preserve conflicting patient information rather than silently selecting one value.

Examples:

- two different creatinine values from different sources
- conflicting medication lists
- differing allergy documentation
- conflicting diagnoses

Resolution rules may identify a preferred value, but the underlying conflict and source information should remain traceable.

A resolution shall retain the conflict, candidate sources, selected value or unresolved outcome, exact resolution policy/version, actor or method, rationale, and time. Preserving a conflict does not make it safe to use: unresolved safety-critical conflicts shall be represented as blocking the affected recommendation rather than silently selecting a convenient value.

---

# 29. Clinical Rules

Clinical Rules represent deterministic or governed logic.

Examples include:

- contraindication rules
- dose adjustment rules
- interaction rules
- eligibility rules
- monitoring rules
- escalation rules
- safety thresholds

Rules must be separately identifiable and versioned.

Clinical rules with deterministic logic shall be evaluated by governed deterministic implementations, independently of an LLM.

A rule definition describes conditions, required input meanings/types and units, applicability, dependencies, outputs, unknown/conflict behavior, and validation status. A rule execution is a separate identified occurrence linked to the exact rule definition and implementation version.

Each execution shall durably retain actual input values and fact revisions or permitted recoverable references, context snapshot, original and evaluated units, conversions and rounding where applicable, resolved dependency versions, evaluation times, outputs/actions proposed, triggered conditions, and outcome. Distinguish evaluated-and-not-triggered from not evaluated, unsupported, missing input, conflict, timeout, or failure. Record reasons and partial results as such; a failed or unknown evaluation is not a negative result. Policy-controlled conflict resolution shall preserve the policies and rationale used. Definition approval does not certify an individual execution.

---

# 30. Clinical Calculations

Clinical Calculations represent deterministic mathematical or algorithmic transformations.

Examples include:

- creatinine clearance
- MELD
- Child-Pugh
- corrected calcium
- anion gap
- drug dose calculations

Calculations must have:

- defined inputs
- defined units
- defined formula
- defined assumptions
- version
- validation status

Calculation executions shall retain sufficient provenance to reproduce deterministic results within the authorized retention boundaries in Section 45.

A calculation definition is distinct from an execution and a resulting Derived Value. Definitions shall describe the formula/algorithm, applicability, required input meanings/types and units, assumptions, conversions, rounding/precision, boundary behavior, and validation references. Deterministic clinical calculations shall use validated deterministic implementations, not an LLM as the authoritative calculator.

Each execution shall retain:

- execution identity, exact definition/algorithm and implementation versions, configuration and relevant execution-environment identifiers;
- patient-context snapshot and input fact revisions, the actual values used or permitted recoverable references, original units, normalized units, and conversion method/version;
- applicable assumptions, precision and rounding policy, and intermediate values where necessary for reproduction;
- output values and units, calculation time and relevant input clinical times, and warnings;
- completion or failure outcome, reason, missing/incompatible inputs, and any partial output clearly identified as non-final.

A retry or recomputation is a separately traceable execution. Missing input, invalid units, out-of-scope use, or execution failure must not be represented as zero, a normal result, or successful completion. Model predictions remain governed inferences even when repeatable (Sections 20 and 39).

---

# 31. Recommendations

A Recommendation is a structured clinical output generated from:

- patient context
- applicable knowledge
- evidence
- clinical rules
- calculations
- safety checks

A recommendation shall be structured and shall not be stored merely as free-form text.

Conceptually, a recommendation may contain:

- recommendation_id
- recommendation_type
- clinical_action
- rationale
- applicable_context
- evidence
- calculations
- warnings
- monitoring
- alternatives
- uncertainty
- provenance
- timestamp

Natural-language rendering is a presentation layer over the structured recommendation. Consistent with ARCH-001 Sections 4.2 and 4.5, insufficient patient context or unresolved safety-critical uncertainty must permit an explicit insufficient-information outcome rather than an unsupported patient-specific recommendation. Outputs support clinician judgment and do not replace it.

## 31.1 Candidate, Evaluation, Release, and Presentation

A reusable recommendation definition or template is separate from a patient-specific recommendation instance. Each instance shall distinguish candidate revisions, rendered versions, evaluation records, release/withholding decisions, and presentation events. “Validated” means that the required evaluations cover the identified content/context within their stated scope; it is not a synonym for released, presented, accepted, or clinically correct.

The logical sequence is candidate → rendering → validation → release → presentation. A release decision shall bind the exact candidate and rendered clinical content to the verified patient/encounter or longitudinal-care context, context snapshot and freshness assessment, applicable artifact versions, evaluations, permitted warning exceptions, actor/authority, time, and intended use. Presentation events identify what was actually shown, to whom and when, and its release reference. No presentation event may imply that an unreleased clinical recommendation was approved.

**ClinRx validates the exact clinical meaning released to the clinician, not merely an intermediate representation.** Any semantic modification, including changed quantities, units, conditions, translation, summarization, or omitted material warnings, shall create a new content revision and invalidate applicability of prior validation/release to that revision. Retain the old evaluation as historical evidence and link the renewed evaluation. Purely visual changes may preserve validity only if meaning and warning visibility remain intact. Streaming, API export, and downstream presentation must preserve this same boundary.

## 31.2 Safety Evaluation and Decision Records

An identifiable safety evaluation shall retain exact policy and rule versions, evaluated candidate/rendering versions, relevant inputs/context, checks attempted and completed, coverage, limitations, uncertainty, outcomes, reasons, and times. Completion and “no detected violation” do not establish clinical validity. Represent unsupported/out-of-scope claims, unavailable required checks, and unresolved safety-critical data separately from supported results.

Unsupported claims shall produce abstention or withholding of actionable advice. A governed limited-review artifact may expose an explicitly unvalidated hypothesis or question to an authorized reviewer; record its review-only purpose, limitations, authorization, and absence of treatment-action enablement. It still requires applicable identity, privacy, and content controls and is not an actionable recommendation release.

Warnings shall retain the policy designation of overrideability. Hard failures—failed identity binding, denied authorization, unavailable mandatory evaluation, unresolved safety-critical inputs/conversions, invalidated content validation, or actionable use outside validated coverage—are non-overrideable. Correction requires a new evaluation. A separately recorded authorized warning exception may support a release within the intended use; it must not rewrite the original warning as a pass. Human-event requirements are in Section 38.

Released outputs shall support subsequent stale, invalidated, withdrawn, or superseded eligibility events with reasons and references to affected dependencies. Reassessment and recovery create new decisions rather than silently reactivating prior releases.

## 31.3 Clinical Output Classification

Each clinically material claim shall be identifiable within its output and linked to its production provenance: deterministic calculation, rule-derived, evidence-derived, or AI-generated/inferred. More than one classification may apply; an AI-rendered explanation can refer to a deterministic result without changing that result's origin. Retain the contributing execution, evidence assessment, or model interaction and the boundaries between quoted facts, computed results, inference, and explanatory wording. Classification does not confer verification, evidence authority, or safety eligibility.

---

# 32. Recommendation Provenance

Every clinically meaningful recommendation must be traceable to its inputs.

The provenance chain should allow reconstruction of:

```text
Verified Patient Context snapshot + selected Knowledge / Evidence versions
      ↓
Rules / Calculations / governed AI interactions (where used)
      ↓
Structured candidate + rendered clinical content
      ↓
Safety evaluation + content validation
      ↓
Authorization + release or withholding decision
      ↓
Actual presentation + human actions (where permitted)
```

The provenance chain must be preserved sufficiently to support clinical review and audit.

This is a provenance view; independent upstream operations may be iterative or parallel. Preserve the exact relationships, content revisions, output classifications, selected versions, retrieval eligibility and selection rationale, safety coverage, authorization decisions, and freshness assessments used. The final release sequence follows Section 31 and ARCH-001 Section 5. Source rank is not evidence authority; a citation is not an applicability assessment.

---

# 33. Patient Context Snapshots

ClinRx shall retain an immutable Patient Context snapshot for each clinically meaningful patient-specific recommendation, including candidates whose release is withheld, under Section 45 retention controls.

A snapshot represents the patient information available to the system at a specific point in time.

Snapshots enable:

- reproducibility
- retrospective review
- audit
- model evaluation
- safety investigation
- comparison of recommendations over time

A snapshot must identify its creation time and underlying data sources.

The snapshot shall identify its patient/encounter or verified longitudinal-care binding, constituent fact revisions and source references, temporal cutoff, creation time, known missing/conflicting information, and source completeness. Contents must remain recoverable during authorized retention; a pointer to mutable current records is insufficient. Unresolved identity prevents creation of a verified decision context and shall instead be recorded as a withheld workflow with protected source references, not a fabricated patient binding.

Freshness is a separately recorded assessment bound to the snapshot and decision, including policy/version, assessment time, relevant source times, material changes detected since capture, adequacy for the intended use, and rationale. Before release, binding and freshness must be evaluated; safety-critical inadequacy requires a new snapshot/re-evaluation or withholding. Detected material changes before presentation or downstream action invalidate affected eligibility. A snapshot records what was available; it does not remain current merely because it is immutable.

---

# 34. Provenance as a Graph

ClinRx provenance should conceptually be treated as a graph rather than a single source field.

A clinical output may depend on multiple:

- patient facts
- knowledge objects
- evidence objects
- calculations
- rules
- safety evaluations
- model interactions

The system should be capable of tracing relationships across these objects.

Provenance relationships shall identify the exact versions and executions connected, relationship meaning, actor or method, and time. Release and presentation records, evidence snapshots, warning exceptions, and human modifications participate in this graph. Preserve enough dependency information to find outputs affected by a hazard, source withdrawal, policy change, suspended model, or corrected fact. Governance events shall link the affected versions/outputs, safety owner and authority, rationale, mitigation or residual-risk review reference, and withdrawal/notification/reassessment or resumption decisions. Detailed hazard-management procedures belong in the safety standard.

---

# 35. Supersession

When knowledge changes, the relationship between versions must be preserved.

A new version should identify, where applicable:

- previous version
- reason for change
- effective date
- reviewer
- approval information

Superseded versions remain historically retrievable within authorized retention and access boundaries (Section 45).

They must not be silently deleted.

---

# 36. Review Metadata

Clinical knowledge should support governance metadata such as:

- created_by
- reviewed_by
- approved_by
- review_date
- next_review_date
- review_status
- change_reason

Review metadata must remain separate from clinical evidence itself.

Review and approval are version-bound governance events with reviewer authority, outcome, time, rationale, and validation/evidence references. Clinical, knowledge, and engineering review must be distinguishable from publication, deployment, suspension, and individual patient-output review. A revised artifact or changed intended use must not silently inherit an earlier approval.

---

# 37. Temporal Reproducibility

ClinRx must support reconstruction of what the system knew at a previous point in time.

A historical recommendation should be reconstructible using:

- the relevant patient-context snapshot
- applicable knowledge versions
- evidence versions
- rule versions
- calculation versions
- safety evaluation
- AI model/version where applicable

This is a core requirement for clinical auditability.

Historical reconstruction shall distinguish the clinical event-time state from what was available at the decision time. Preserve the decision's resolved artifact/execution versions, source recoverability limitations, snapshot, model interaction, exact rendered content, safety-policy version and coverage, authorization/release or withholding decision, and actual presentation/human events. Re-running a historical case against current knowledge is a new evaluation, not reconstruction of the original decision.

Deterministic reproduction depends on retained inputs, algorithms, conversions, rounding, configuration, and execution identifiers (Sections 29–30). AI interaction reconstruction uses the actual retained inputs, tool results, model output, and presentation record; it does not promise regeneration of identical generative text or access to private model reasoning. Unknown provider versions and unavailable source material must remain explicit limitations. Authorized deletion/redaction may limit reconstruction; record that limitation rather than claiming complete recovery (Section 45).

---

# 38. Audit Data

Audit information must be represented independently from clinical knowledge.

Audit records may include:

- user or system actor
- action
- timestamp
- object affected
- previous state
- resulting state
- reason
- source
- authorization context

Audit data should support investigation without requiring modification of the underlying clinical objects.

For clinically meaningful release or withholding, the audit record shall retain the exact content/context references, identity and freshness assessment, safety-policy/evaluation versions and results, authorization allow/deny decision and policy reference, releasing/withholding actor and authority, reasons, and time. Protect audit records from unauthorized alteration and apply the same privacy/retention boundaries to audit as to other patient-specific artifacts.

Human actions shall be distinct attributable events: review, acknowledgement, acceptance, rejection, modification, and override/authorized warning exception. Each identifies the actor, role/authority, time, patient/context, exact recommendation and rendering reviewed, action, and rationale where required. A modification creates a new candidate linked to its predecessor and requires renewed validation/release before system presentation as a recommendation. An acknowledgement records awareness only; acceptance does not prove an order was placed or treatment administered.

A warning exception requires mandatory rationale and the exact warning, safety policy, authority, and affected content/context. Preserve the original evaluation and exception separately. Acknowledgement, acceptance, or override shall never convert a failed evaluation into a pass; hard failures in Section 31.2 cannot be waived. An attempted unauthorized override or independent clinician decision outside a withheld recommendation may be recorded without labeling it a successful ClinRx release. Presentation records must retain clinically material warnings and limitations so that reviewability can be assessed.

---

# 39. AI Interaction Data

AI interactions must be separately identifiable.

Where an AI model contributes to a clinical workflow, ClinRx shall preserve the applicable decision-relevant information under Section 45 retention controls:

- model identifier
- model version
- provider
- request context
- structured inputs
- retrieved knowledge
- system instructions or governed prompt version
- model output
- safety evaluation
- final structured recommendation
- human action

The AI model must not become the authoritative source of clinical truth.

Retain interaction identity, input/context and output revisions, model configuration and available version identifier, governed instructions, retrieved artifact versions, tool requests/results and their authorization, errors or incomplete responses, and links to candidate, validation, and release records. Preserve explicit unknown/unavailable metadata rather than inventing it. Recording an unknown model version does not itself authorize clinical use; link the intended-use governance assessment.

Generative, predictive, and probabilistic model outputs shall retain inference classification, target/time horizon where relevant, input and population applicability, uncertainty, and versioned validation/calibration references as appropriate. They are not observed patient facts and cannot publish knowledge or authorize action. Link model/provider eligibility and approved data-processing policies covering processing location, subprocessors, retention/deletion and secondary use/training; record relevant changes and suspension decisions. Provider replacement or fallback requires traceable approval for the intended use, not merely a compatible interface. Durable interaction records support historical reconstruction as defined in Section 37, not guaranteed identical regeneration.

---

# 40. Multi-Source Data

ClinRx may receive patient information from multiple sources.

Examples include:

- hospital systems
- laboratory systems
- pharmacy systems
- microbiology systems
- devices
- external records
- clinician-entered information
- patient-reported information

Source identity must be preserved.

Data integration must not erase the origin of clinical information.

Represent the original source information, identity assertions, transformations, and resulting clinical facts separately, subject to Section 45. Transformation records shall retain source and target identifiers/versions, terminology mapping and unit-conversion references, method/version, timing, actor or system, and known loss or ambiguity.

Ambiguous patient matching, unmapped or conflicting codes, unknown units, incompatible conversion, incomplete source data, and clinically material loss shall have explicit issue states, affected fields, reasons, source references, and resolution history. Rejected or quarantined information must remain distinguishable from usable facts; it must not be silently normalized, merged, or interpreted as a negative finding. Ambiguous identities require authorized resolution without combining records.

Qualified use of a mapping/conversion or lossy representation requires a recorded intended-use policy assessment that the limitation cannot invalidate that use, with visible limitations and authorization. Unresolved safety-critical issues block the affected recommendation. Preserve any permitted source content necessary to investigate the issue; rejection does not remove privacy/retention obligations. Successful transport or parsing is not clinical verification.

---

# 41. Source Priority

ClinRx may define source-priority rules for resolving conflicts.

Source priority must be:

- explicit
- context-dependent
- versioned
- auditable

A source-priority rule must not destroy lower-priority source information.

The original observations remain part of the clinical record.

Preserve the exact priority/resolution policy and its applicability, time, selected and excluded source references, and rationale in the decision provenance. A source-priority policy does not cure unresolved identity, mapping, unit, or safety-critical data failures. Retention of original observations is governed by Section 45.

---

# 42. Local Clinical Knowledge

Institutions and departments may maintain local clinical knowledge.

Local knowledge may include:

- antimicrobial protocols
- formulary restrictions
- local susceptibility patterns
- escalation pathways
- monitoring protocols
- institutional dosing policies

Local knowledge must have explicit scope, jurisdiction, ownership, versioning, and review metadata.

---

# 43. Storage Independence

The conceptual data model must not depend on a specific database technology.

The model should be implementable using:

- PostgreSQL
- Supabase
- another relational database
- future interoperable storage systems

Technology-specific implementation details must not redefine the clinical information model.

Portability, migration, and recovery shall preserve clinical meaning, stable/version identities, provenance relationships, disposition restrictions, and governance events. Restored data must retain withdrawal, suspension, and staleness information; physical recovery does not constitute a new eligibility or release decision.

---

# 44. API Representation

API representations should preserve the conceptual distinction between:

- knowledge
- evidence
- patient data
- rules
- calculations
- recommendations
- audit data

APIs should expose stable identifiers and versions.

API contracts should not force clients to reconstruct clinical semantics from unstructured text.

Logical exchange representations shall preserve origin/classification, missingness and uncertainty, candidate/release/presentation distinctions, exact content/version references, safety limitations, and original versus transformed values. Exporting or re-rendering content must not erase required warnings or imply a new release. A semantic modification creates a new revision subject to Section 31, independent of the transport technology. Specific endpoints and interoperability profiles remain future specifications.

---

# 45. Security Boundaries

Clinical data and knowledge must have explicit security boundaries.

Patient-specific data requires stronger privacy controls than publicly available clinical knowledge.

Security design should support:

- authentication
- authorization
- role-based access
- least privilege
- audit logging
- encryption
- tenant or institution isolation where applicable

Security controls must be designed before production patient-data integration.

## 45.1 Authorized Retention and Disposition

Historical immutability means no silent clinical rewrite; it does not require indefinite retention or prohibit authorized deletion or redaction. This qualification applies throughout the standard, including Sections 4, 9, 27, 33, 35, 37, 38, and 41. Preserve records for their approved purpose and authorized retention period, with controls covering patient facts, patient-scoped knowledge, source material, snapshots, executions, AI interactions, recommendations, audits, exports, and recovery copies.

An authorized disposition shall identify the policy and authority, scope, affected identities/versions or permitted non-identifying references, reason, time, and deletion/redaction outcome to the extent legally permitted. A redacted representation shall be distinguishable from the original; do not recreate removed sensitive content in an audit record. Record unavailability and resulting reconstruction limits without falsely asserting that a deleted snapshot or source remains recoverable. Restriction, redaction, or deletion must not fabricate a replacement clinical history. Detailed retention periods and legal determinations belong in approved privacy and operational policies.

Patient-scoped exceptions and limited-review artifacts require patient-data protection. External AI processing permissions and retention/secondary-use restrictions shall remain linked to the governing policy (Section 39). Data loss, restoration, or export must not silently remove access restrictions or reactivate withdrawn clinical eligibility.

---

# 46. Future Conceptual Database Domains

The eventual persistence architecture is expected to contain separate conceptual domains for areas such as:

- knowledge
- evidence
- terminology
- patients
- patient facts
- medications
- microbiology
- observations
- clinical rules
- calculations
- recommendations
- safety evaluations
- provenance
- audit
- AI interactions
- governance

The physical schema should emerge from this conceptual model rather than being designed independently.

Within these domains, preserve the logical distinction between definitions and executions; source records and transformations; candidates, renderings, evaluations, release decisions and presentation events; human actions; and retention/disposition events. These are conceptual responsibilities and relationships, not a requirement for one table, service, or storage engine per record type.

---

# 47. Design Constraints

The following constraints apply to future ClinRx development:

1. Published clinical knowledge versions are immutable.
2. Patient facts must retain provenance.
3. Historical clinical information must remain reconstructible within authorized retention, with explicit limitations for authorized deletion/redaction or unavailable sources (Section 45).
4. Knowledge and evidence must remain distinct.
5. Observed, derived, and inferred information must remain distinguishable.
6. Deterministic calculations must remain reproducible.
7. Clinical rules must be independently versioned.
8. Recommendations must be structured before natural-language rendering.
9. AI-generated content must not become an uncontrolled source of clinical truth.
10. ClinRx must be capable of explaining the basis of a clinical output.
11. Temporal applicability must be explicit.
12. Jurisdiction and scope must be explicit.
13. Conflicting information must not be silently discarded.
14. Storage technology must remain replaceable.
15. The architecture must support future interoperability.

16. Exact clinical meaning, context, evaluation, release, and actual presentation shall be traceably linked.
17. Safety-check completion, clinical validity, release permission, and clinician acknowledgement are distinct.
18. Definitions, executions, and execution failures shall remain separately identifiable.
19. Verified identity and adequate context freshness are prerequisites for patient-specific release.
20. Unresolved interoperability issues shall not be silently converted into verified facts.

Sections 29–33 own execution and output semantics; Sections 38–40 own audit, AI, and integration records; Section 45 owns retention qualifications. These constraints repeat the invariants without replacing those detailed definitions.

---

# 48. Long-Term Data Principle

ClinRx data should remain clinically meaningful even if:

- the database technology changes
- the API changes
- the AI model changes
- the model provider changes
- the user interface changes
- the hospital integration changes

The clinical meaning, provenance, version history, and temporal context must survive technological replacement.

---

# 49. Relationship to CLINRX-ARCH-001

CLINRX-ARCH-001 defines system responsibilities and governing release boundaries. CLINRX-DATA-001 defines the logical information needed to represent and audit those responsibilities. DATA-001 does not prescribe engine deployment, physical schemas, or clinical validation procedures.

For this revision, the authoritative candidate parent is **CLINRX-ARCH-001 Version 1.1 candidate Draft**, in `CLINRX-ARCH-001-completed.md`, reviewed on 2026-09-25. The candidate's SHA-256 at alignment is `7f81c99d702068d00cddb407bb8b4d40deb327d0e7df0a542a612a4f34eb9c5f`. This pins the review to a particular candidate revision; the previously incomplete repository Version 1.0 was not the parent used for this consistency assessment. The reviewed Version 1.1 Draft has since replaced that truncated copy. The SHA-256 above identifies the candidate as reviewed, before formatting and historical-note cleanup; it is not a checksum of the cleaned repository file. Neither alignment nor document completeness constitutes approval for clinical use.

The earlier limited-review note about the then-truncated ARCH-001 was superseded by this candidate-parent alignment. Relevant ownership is:

| Candidate ARCH-001 responsibility | DATA-001 representation |
|---|---|
| Sections 4–5: governed knowledge, identity and exact-meaning release | Sections 4–8, 19, 31–33 |
| Sections 6.1–6.4: context, knowledge retrieval and evidence | Sections 4–19, 21–28, 33, 40–42 |
| Sections 6.5–6.8 and 11: computation, safety, recommendations and output classification | Sections 20, 22, 29–32, 38 |
| Sections 7–8: governed AI inference and provider independence | Sections 20, 25, 37, 39, 45 |
| Sections 9–14: versions, uncertainty, temporal provenance and audit | Sections 8, 16–18, 24–28, 32–39 |
| Sections 15–16: interoperability and privacy | Sections 6–7, 40–45 |
| Sections 17–19: validation, hazards and human oversight | Sections 30–31, 34, 36, 38–39, 51 |
| Section 20: portability and recovery | Sections 35, 43–45, 48 |
| Sections 21–27: evolution, principles and adoption | Sections 47–53 |

Future specifications shall reference the owning standard rather than silently redefine its concepts. Legacy reconciliation items are explicitly retained in Section 50.

---

# 50. Status and Future Work

This document is a conceptual standard.

It does not yet define:

- physical PostgreSQL tables
- Supabase implementation details
- database indexes
- API endpoint specifications
- FHIR resource mappings
- production security configuration
- final terminology-service implementation

Those implementation details should be defined only after the conceptual model is reviewed and approved.

## 50.1 Unresolved Legacy Reconciliation

The following remain governance work, not silently resolved changes to legacy standards:

- CAS-KOS-001's concept-only CKO structure and prohibition on executable algorithms need an approved relationship to the broader Knowledge Object taxonomy and separate rule/calculation definitions. `object_class` and `object_type` require a reviewed mapping; no automatic equivalence is asserted.
- CAS-KOS-001's Clinical/Knowledge/Engineering Review, Implemented, Maintained, and Deprecated terms require mapping to review, deployment, maintenance, and DATA-001 lifecycle dimensions.
- Legacy graph classes and evidence/patient terminology require an explicit mapping that preserves general concepts, evidence sources, and patient-instance separation; graph connectivity does not collapse their identities.
- ADR references to CAS-CDS-001 require recovery or an approved replacement/reference decision; the active repository does not contain that standard. ADR-004's CAS-ARCH-003/004/005 engine titles do not match current Container/Component/Data Architecture filenames.

Accepted ADRs and legacy documents are not amended by this Draft. Resolve these issues through authorized review before declaring the complete standards set reconciled. Detailed safety-policy classes, evaluation methods, human permissions, hazard procedures, terminology profiles, retention schedules, and recovery controls belong in subsequent standards. Those details remain open implementation prerequisites, not missing permission to bypass the logical requirements here.

---

# 51. Definition of Done for this Standard

CLINRX-DATA-001 will be considered ready for implementation when:

- the conceptual object model is approved
- terminology strategy is approved
- evidence representation is approved
- temporal semantics are approved
- provenance requirements are approved
- patient-context model is approved
- recommendation representation is approved
- audit requirements are approved
- security boundaries are approved
- major interoperability requirements are identified

Only then should the physical database schema be designed.

Approval shall also cover definition/execution separation, output classifications and exact-meaning validation, patient/encounter binding and freshness, safety coverage and hard-failure semantics, human-action/exception records, evidence recoverability, interoperability issue representation, and authorized disposition/reconstruction limits. Legacy reconciliation in Section 50 and detailed safety/privacy boundaries require a recorded resolution before production implementation is declared conformant. Logical-model approval is not clinical-release approval.

---

# 52. Design Philosophy

ClinRx is being designed as clinical infrastructure rather than as a temporary AI application.

The data model must therefore prioritize:

- clinical trust
- traceability
- reproducibility
- safety
- interoperability
- governance
- long-term maintainability

The guiding principle is:

**ClinRx governs. AI reasons.**

---

# 53. Document Control

**Document:** CLINRX-DATA-001

**Version:** 0.3

**Status:** Draft

**Parent:** CLINRX-ARCH-001 Version 1.1 candidate Draft

**Owner:** ClinRx AI

**Date:** 2026-09-25

Changes to this standard should be versioned and reviewed before they are used as the basis for production clinical data architecture.

**Revision basis:** Candidate-parent alignment, 2026-09-25. Version 0.3 extends the Version 0.2 Draft with explicit execution records, output lifecycle and classification, context binding/freshness, safety and human decisions, source/terminology provenance, interoperability issues, and authorized disposition. Section 49 identifies the exact candidate parent reviewed. During the alignment, repository ARCH-001 and legacy CAS/ADR documents were unchanged. The reviewed ARCH-001 Version 1.1 Draft has since been installed; legacy documents remain unchanged and approval remains pending.
