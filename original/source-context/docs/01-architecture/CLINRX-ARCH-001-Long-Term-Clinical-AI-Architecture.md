# CLINRX-ARCH-001 — Long-Term Clinical AI Architecture Standard

**Document ID:** CLINRX-ARCH-001

**Title:** Long-Term Clinical AI Architecture Standard

**Version:** 1.1

**Status:** Draft

**Date:** 2026-09-25

**Effective Date:** Pending approval

**Previous Draft:** Version 1.0, dated 2026-09-24

**Owner:** ClinRx AI

**Classification:** Architecture / Foundational Standard

---

# 1. Purpose

This document defines the long-term architectural principles and system design standards for ClinRx AI.

ClinRx AI is intended to become a trustworthy clinical decision-support platform capable of supporting clinicians with evidence-based, patient-specific clinical reasoning.

The architecture is designed to remain useful and maintainable over a period of at least ten years despite changes in:

- artificial intelligence models
- clinical guidelines
- medical evidence
- drug information
- healthcare workflows
- regulatory requirements
- software technologies
- infrastructure
- interoperability standards

The architecture therefore prioritizes clinical trust, evidence provenance, safety, modularity, auditability, and model independence over rapid feature development.

---

# 2. Vision

ClinRx AI aims to provide clinicians with trustworthy, evidence-grounded, patient-specific clinical decision support.

The core principle is:

> **ClinRx does not replace clinical judgment. It strengthens clinical judgment with structured knowledge, patient context, validated clinical computation, evidence, and AI-assisted reasoning.**

A second architectural principle governs the relationship between AI and the clinical platform:

> **AI reasons. ClinRx governs.**

The AI layer may interpret, synthesize, explain, and communicate information.

The ClinRx platform remains responsible for:

- clinical knowledge
- evidence provenance
- deterministic calculations
- clinical rules
- safety checks
- patient context
- versioning
- auditability
- traceability

---

# 3. Architectural Goals

ClinRx shall be designed to achieve the following goals:

1. Clinical trustworthiness
2. Evidence traceability
3. Patient-specific reasoning
4. Deterministic clinical computation
5. Safe AI integration
6. Model independence
7. Knowledge versioning
8. Full auditability
9. Maintainability
10. Interoperability
11. Scalability
12. Security and privacy
13. Clinical validation
14. Regulatory readiness
15. Long-term technological resilience

---

# 4. Core Architectural Principles

## 4.1 Evidence Before Opinion

ClinRx should preferentially ground clinical recommendations in authoritative and traceable evidence.

Evidence may include:

- clinical guidelines
- regulatory labeling
- peer-reviewed literature
- institutional protocols
- consensus statements
- validated clinical standards
- curated expert knowledge

AI-generated reasoning must not silently become the source of clinical truth.

---

## 4.2 Patient Context Before Recommendation

Clinical recommendations must be interpreted in the context of the individual patient.

Where relevant, ClinRx should consider:

- age
- sex
- weight
- renal function
- hepatic function
- diagnosis
- comorbidities
- allergies
- medications
- laboratory results
- microbiology
- organ support
- CRRT
- ECMO
- transplant status
- procedures
- clinical timeline

A generic recommendation should not be presented as patient-specific advice unless sufficient patient context exists.

---

## 4.3 Deterministic Computation Before AI Estimation

Clinical calculations with defined mathematical or algorithmic logic shall use validated deterministic implementations and shall not depend on an LLM as the authoritative calculator.

Examples include:

- creatinine clearance
- eGFR
- body surface area
- ideal body weight
- adjusted body weight
- corrected sodium
- anion gap
- osmolarity
- MELD
- Child-Pugh
- infusion rates
- renal dose adjustments
- CRRT calculations

AI may explain these results but shall not be the authoritative computational engine.

---

## 4.4 Transparency Before Automation

ClinRx should explain the basis of clinically meaningful recommendations.

The system should be able to communicate:

- what it understood
- which knowledge was used
- which evidence was used
- which patient factors mattered
- which calculations were performed
- which safety rules were triggered
- what uncertainty remains

Automation should not reduce transparency.

---

## 4.5 Safety Before Convenience

When a conflict exists between a faster answer and a safer answer, ClinRx should prioritize safety.

ClinRx should prefer:

> "Insufficient information to determine a safe recommendation."

over an unsupported or fabricated recommendation.

---

## 4.6 AI Assists; AI Does Not Own Clinical Truth

The AI model is a reasoning and communication component.

The AI model shall not be treated as the authoritative source of:

- drug doses
- contraindications
- clinical calculations
- guideline versions
- patient facts
- laboratory values
- safety rules

These should originate from controlled ClinRx systems.

---

## 4.7 Model Independence

ClinRx must not become architecturally dependent on a single AI model or provider.

The system should support an abstraction layer capable of interfacing with:

- commercial frontier models
- future foundation models
- specialized medical models
- local models
- institution-hosted models

Changing the AI model should not require redesigning the clinical knowledge architecture.

---

## 4.8 Knowledge Is Versioned

Clinical knowledge must be versioned.

Published knowledge shall be immutable.

When knowledge changes, preserve the stable identity and publish a new immutable version. For example:

```text
Knowledge identity: NUT-STATE-002
  Version 1.2 — Published; later Superseded by version 1.3
  Version 1.3 — Published; eligible only within its effective period and scope
```

Supersession and retirement are separate governance events. Neither deletes the historical version or rewrites its published content. “Current” means applicable at a specified clinical time, jurisdiction, and scope; it is not a synonym for Approved or Published.

## 4.9 Scope and Interpretation

This standard defines the target logical architecture, component responsibilities, trust boundaries, governance, and release expectations. It does not assert that these capabilities are implemented or clinically validated today. It does not specify treatment policies, physical database tables, deployment topology, or regulatory clearance.

In this draft, “shall” and “must” express proposed requirements for adoption; “should” expresses a recommended approach whose exceptions require a documented rationale; “may” expresses an option. Draft status does not constitute approval for clinical use. Existing accepted ADRs remain in force; conflicts require explicit review and an approved ADR rather than silent supersession.

The ClinRx Clinical Architecture Standards (CAS) remain supporting specifications. CLINRX-ARCH-001 establishes system responsibilities; CLINRX-DATA-001 defines the information model; a future CLINRX-SAFE-001 will specify detailed clinical safety and AI governance controls.

# 5. High-Level Architecture

**ClinRx validates the exact clinical meaning released to the clinician, not merely an intermediate representation.**

ClinRx shall retain the three-layer separation established by ADR-004, ADR-005, and ADR-006:

1. **Clinical Domains:** reusable medical concepts and governed knowledge, independent of specialty and workflow.
2. **Clinical Engines:** reusable interpretation, computation, validation, safety, and recommendation capabilities.
3. **Specialty Operating Systems:** clinical workflow applications that orchestrate engines for a specialty; these are not computer operating systems and must not redefine shared knowledge.

The Knowledge Engine manages domain knowledge. Patient Context remains a distinct patient-specific domain. A patient-scoped knowledge exception, if supported, must remain separately governed and access-controlled; it cannot be promoted into reusable general knowledge or substituted for a patient fact. Evidence remains distinct from interpreted knowledge. The Clinical Knowledge Graph links concepts and evidence; patient facts may reference those concepts without becoming general knowledge. A graph is a logical relationship model and does not mandate a graph database.

```text
Clinician / Specialty workflow
              |
Authenticated, authorized clinical orchestration
              |
Patient Context snapshot + applicable Knowledge / Evidence retrieval
              |
Clinical State / Rules / Calculations / optional AI-assisted synthesis
              |
Structured candidate recommendation
              |
Rendering of proposed clinical content
              |
Safety evaluation + validation of candidate and rendered meaning
              |
Authorized release bound to verified patient/encounter and current context
              |
Presentation of the validated clinical content
              |
Clinician review / separately authorized downstream action
```

Provenance, authorization, audit, and uncertainty handling apply across the entire flow. Upstream retrieval, reasoning, and computation may be iterative or parallel. The final candidate → rendering → validation → release → presentation dependency is mandatory for clinically meaningful content. Preliminary checks may run earlier, but release requires evaluation of the exact clinical meaning that will be presented, including actions, quantities, units, conditions, uncertainty, and warnings. Validation here means the specified content and safety evaluations; it is not a guarantee of clinical correctness or universal applicability.

Any semantic modification after validation, including AI rewriting, translation, summarization, or omission of a clinically material warning, invalidates that validation and requires renewed evaluation and release. Purely visual changes are permitted only when they preserve validated meaning and warning visibility. Clinically actionable streaming content shall not bypass this boundary. Presentation shall show only content covered by the release decision.

Clinical orchestration owns request identity, workflow state, dependency order, context freshness, timeouts, and the final release decision. Components expose typed, versioned contracts and may initially coexist in one application. This logical separation does not require microservices.

| Logical responsibility | Accountable function and boundary |
|---|---|
| Patient Context | Binds source facts to the verified patient/encounter, preserves provenance, and supplies snapshots and freshness information. |
| Clinical State | Derives or infers patient state and trajectory from identified inputs; preserves method and uncertainty rather than declaring inferred facts observed. |
| Clinical Intelligence | Synthesizes applicable evidence, state, and computation within the validated intended use; may use governed AI to propose interpretations. It cannot authorize release. |
| Recommendation construction | Assembles a structured candidate, rationale, alternatives, limitations, and dependencies. It does not certify its own clinical validity. |
| Safety Evaluation | Applies the governed safety policy, records coverage and outcomes, and identifies warnings, unsupported claims, and hard failures. |
| Validation | Checks contractual consistency and fidelity between the candidate and rendered clinical meaning; structural conformance alone is insufficient. |
| Orchestration / release | Enforces the required evaluations, identity, freshness, authorization, and permitted warning exceptions, then records release or withholding. It cannot waive hard failures. |
| Presentation | Renders proposed content before validation and displays the released version afterward, with patient/context identification and visible limitations. It cannot independently revise clinical meaning or authorize action. |

These are logical responsibilities, not a mandate for separate services or model instances. Detailed evaluation methods and operational controls belong in the safety and implementation standards.

Knowledge is authored once per canonical concept and reused. Scoped local variants, evidence disagreement, and historical versions are linked representations, not accidental copies of specialty knowledge.

---

# 6. Major Clinical Components

ClinRx shall evolve around the following major engines.

## 6.1 Patient Context Engine

Maintains the clinically relevant state of the patient.

Potential domains include:

- demographics
- weight
- height
- diagnoses
- allergies
- medications
- laboratory values
- microbiology
- vital signs
- organ function
- renal replacement therapy
- ECMO
- procedures
- transplantation status
- clinical events
- longitudinal timeline

The Patient Context Engine should distinguish between:

- current state
- historical state
- unknown state
- inferred state

Unknown information must not automatically be interpreted as negative information. Clinical Context Engine in ADR-004 and Patient Context Engine here name the same logical responsibility.

Patient facts shall distinguish Observation, Condition, Medication Order, Medication Administration, Procedure, Derived Value, and Inference. A medication order is not proof of administration. Observed, derived, inferred, and reported origin, verification, conflict state, and clinical status are independent dimensions. Corrections create traceable revisions rather than erasing prior facts. The engine records event, recording, effective, retrieval, and processing times, and assembles an immutable snapshot for each clinically meaningful recommendation.

Every patient-specific workflow shall have verified patient and encounter binding, or an explicitly verified longitudinal-care context where no encounter applies. Ambiguous matches shall not be merged or used to generate patient-specific advice. Before release, orchestration shall verify that this binding still holds and evaluate the snapshot's freshness, source completeness, and material changes since its creation against the intended-use policy. Critical changes or inadequate freshness require a new snapshot and re-evaluation, or withholding the recommendation. An immutable snapshot proves what was used, not that it remains current. Material changes detected before presentation or downstream action shall invalidate affected release eligibility; previously displayed outputs shall be marked stale or withdrawn as appropriate.

A Clinical State Engine interprets observations and trajectories into versioned patient-specific derived or inferred states. It records inputs, method, uncertainty, and time; it must not promote an inference into an observed fact.

---

## 6.2 Knowledge Engine

Stores structured clinical knowledge.

Knowledge should be represented as versioned Knowledge Objects.

Governed knowledge definitions may describe:

- drugs
- diseases
- clinical states
- procedures
- laboratory concepts
- dosing rules
- interactions
- contraindications
- clinical recommendations
- monitoring requirements
- antimicrobial spectra
- stewardship rules

---

The term Knowledge Object is the broad DATA-001 category. A concept CKO conforming to CAS-KOS-001 represents a medical concept and does not execute algorithms. Rule definitions, calculation definitions, and recommendation templates are separately identified governed artifacts referencing those concepts. Their execution results belong to patient-specific records, not the reusable concept object. This proposed relationship requires taxonomy review with CAS-KOS-001; it does not silently amend that specification.

## 6.3 Retrieval Engine

The Retrieval Engine identifies relevant knowledge for a clinical question.

Retrieval should support:

- deterministic filtering
- relevance ranking
- structured retrieval
- domain filtering
- status filtering
- object-class filtering
- future semantic retrieval
- evidence-aware retrieval

Retrieval must remain separate from AI reasoning.

AI should receive controlled retrieval results rather than unrestricted access to raw clinical data.

Production retrieval shall enforce authorization, publication eligibility, jurisdiction, scope, effective period, and dependency compatibility before selecting knowledge for a patient. Relevance ranking is neither evidence strength nor clinical applicability. Draft and retired material may be retrieved in explicitly authorized authoring or historical modes, but must not silently enter current clinical recommendations. Each result shall identify stable identity, exact version, evidence references, applicability, and selection rationale. Indexes and caches must preserve these boundaries and invalidate unsafe or superseded selections through governed changes.

---

## 6.4 Evidence Engine

The Evidence Engine manages the relationship between clinical knowledge and
its supporting evidence.

Evidence may include:

- clinical guidelines
- regulatory documents
- drug labels
- systematic reviews
- clinical trials
- institutional protocols
- consensus statements
- peer-reviewed publications

Evidence shall retain source identity, citation or locator, source version where available, publication and retrieval times, and provenance. Evidence Objects remain distinct from the Knowledge Objects interpreting them. Supporting, contradicting, contextual, and historical relationships shall preserve applicability, assessment date, and reviewer. Authority is contextual to the use and jurisdiction; no universal ranking may silently discard credible conflicting sources. Local knowledge must identify ownership and its relationship to broader knowledge.

ClinRx shall retain recoverable evidence content or source snapshots for the material actually used, where legally and technically permitted, with a stable reference to the retained version. Where retention is restricted or recovery cannot be assured, preserve permitted identifiers, relevant assessed extracts or attestations, and the limitation. A citation alone does not guarantee historical recoverability. The intended-use governance policy shall determine whether that limitation permits qualified use or requires withholding the affected output.

---

## 6.5 Clinical Calculation Engine

Clinical calculations with defined mathematical or algorithmic logic shall be performed by validated deterministic implementations.

Examples include:

- creatinine clearance
- eGFR
- ideal body weight
- adjusted body weight
- body surface area
- corrected sodium
- anion gap
- osmolarity
- MELD
- Child-Pugh
- drug dosing calculations
- infusion calculations
- renal replacement therapy calculations

The AI layer may explain calculations but shall not be the authoritative calculator for deterministic clinical computations.

Calculation definitions shall specify input types, units, applicability, formula or algorithm version, assumptions, validation status, boundary behavior, and rounding. An execution record retains actual inputs and their fact versions, unit conversions, result, warnings, and software version. Missing or incompatible inputs produce an explicit failure or insufficient-information result. A formula name alone is insufficient for reproduction.

---

## 6.6 Clinical Rule Engine

The Rule Engine evaluates deterministic clinical rules.

Examples:

- renal dose adjustment
- maximum dose
- contraindications
- drug interaction rules
- duplicate therapy
- allergy-related warnings
- monitoring requirements
- dose interval adjustments

Rules shall be versioned and testable independently of the AI model. Rule definitions identify required inputs, scope, dependencies, triggering conditions, outputs, and handling of unknown or conflicting data. Each execution records the exact rule version and evaluation outcome. Conflicting rules require explicit governed resolution or escalation; execution order must not silently determine clinical authority.

---

## 6.7 Safety Engine

The Safety Engine evaluates clinically actionable outputs, including AI-generated clinical claims, before presentation to the clinician.

Potential checks include:

- patient allergies
- renal function
- hepatic function
- drug interactions
- duplicate therapy
- contraindications
- dose limits
- missing critical information
- incompatible assumptions
- unsafe recommendations

Safety controls shall not rely solely on generative AI. The evaluation shall distinguish checks completed and their results from coverage, unresolved uncertainty, and clinical validity. “No detected violation” means only that the identified checks found none within their validated scope; it shall not be presented as proof that the recommendation is clinically correct or safe in all circumstances. Outcomes shall record the exact safety-policy version, evaluated content, relevant inputs, triggered rules, coverage limitations, and reasons.

Unsupported or out-of-scope clinical claims shall not be released as actionable recommendations. ClinRx shall abstain from the affected advice and identify the missing support or applicability. A governed limited-review workflow may expose a clearly labeled unvalidated hypothesis or unresolved question to an authorized reviewer, with its limitations and without treatment-action enablement. That workflow still requires verified identity where patient data is involved, authorization, faithful presentation, and applicable safety/privacy controls; it is not an override that converts an unsupported claim into validated advice.

The safety policy shall distinguish:

- **Overrideable warnings:** explicitly designated advisory outcomes for which a qualified, authorized clinician may approve an exception within the validated intended use. The exception requires a rationale, actor and authority, time, warning and policy versions, and the affected content/context. The warning and exception remain visible and auditable; acknowledgment alone is not resolution.
- **Non-overrideable hard failures:** failed patient/encounter binding, denied authorization, unavailable mandatory evaluation, unresolved safety-critical input or conversion errors, invalidated content validation, or attempted actionable use outside validated coverage. Orchestration shall withhold the affected recommendation. The failure must be corrected and evaluated again; routine clinical override cannot waive it.

Policy changes require separate governance and validation, not a per-request bypass. A clinician may make an independent clinical decision outside a withheld ClinRx recommendation; the system shall not misrepresent that decision as a successful ClinRx safety evaluation. Detailed warning classes, role permissions, and escalation procedures belong in CLINRX-SAFE-001.

---

## 6.8 Recommendation Engine

The Recommendation Engine combines:

- patient context
- retrieved knowledge
- evidence
- deterministic calculations
- clinical rules
- safety checks

to construct a structured clinical recommendation.

A recommendation shall be represented as structured data before being converted into natural language. Candidate, rendered, evaluated, released, and withheld states shall be distinguishable. The released record binds the structured candidate and exact rendered clinical content to context snapshot, knowledge/evidence versions, rules, calculations, safety-policy version and outcomes, rationale, warnings, alternatives, uncertainty, and the authorization/release decision. Rendering and presentation follow Section 5; the Recommendation Engine constructs candidates while orchestration authorizes release. Accepting a recommendation, placing an order, and administering treatment are separate authorized events.

---

# 7. AI Reasoning Layer

The AI layer is responsible primarily for reasoning, synthesis, explanation,
and natural-language interaction.

The AI layer may:

- understand clinician questions
- summarize patient context
- interpret retrieved knowledge
- synthesize evidence
- explain recommendations
- identify missing information
- communicate uncertainty
- answer follow-up questions

The AI layer must not become the authoritative source of clinical truth. Clinical Intelligence Engine in the ADRs is the broader governed synthesis capability; the AI Reasoning Layer is an optional component within it, not a replacement for all Clinical Engines.

Within an explicitly validated intended use, AI may propose patient-specific hypotheses, interpretations, or recommendation candidates from authorized context and traceable evidence. Such proposals shall remain labeled inferences with source inputs, model/method identity, applicability, uncertainty, and limitations. They shall not invent missing facts, replace governed deterministic calculations, publish knowledge, or authorize clinical action. An inference becomes eligible for presentation only through the Section 5 release path and the Section 6.7 coverage policy; plausibility or clinician acknowledgment alone is insufficient.

Predictive and probabilistic models, whether generative or otherwise, require validation for their target outcome, population, setting, input requirements, and intended decision role, including calibration where probabilities are reported and assessment of relevant subgroup limitations. Model estimates are not observed facts, and predictive performance does not establish treatment benefit. Computing a validated formula is deterministic computation; developing or applying a learned clinical prediction is a separately governed inference capability, even when its execution is repeatable.

Clinician text, external documents, retrieved content, and model outputs are untrusted inputs to the control plane. They cannot change authorization, execute arbitrary tools, or override governed instructions. Model-proposed tool calls require typed validation and independent authorization. Model output must be checked for unsupported patient facts, invented citations, changed doses or units, and omitted safety conditions before release. AI-generated knowledge proposals enter a separate review workflow and cannot publish themselves.

ClinRx Flow is a consumer/workflow designation in existing concept specifications; Astra is a possible model choice. Neither defines the clinical information model or an architectural dependency.

---

# 8. Model Abstraction

ClinRx shall maintain an abstraction between the clinical platform and
specific AI providers.

Conceptually:

```text
ClinRx Core
     |
     v
AI Abstraction Layer
     |
 +---+----------+-----------+
 |              |           |
 v              v           v
Provider A   Provider B   Local Model
```

This permits future replacement of the underlying model without requiring
major changes to clinical knowledge, safety engines, or patient context.

The architecture must avoid unnecessary vendor lock-in. The adapter contract separates request, authorized context, retrieved references, structured output, errors, and usage metadata from provider-specific transport. Requests record model/provider identity, available version information, governed prompt version, configuration, and tool interactions. Unknown provider version details are recorded as unknown.

A model or provider change requires evaluation against the intended clinical use before promotion. Fallback models are permitted only within validated policy; an unavailable provider must not trigger an unvalidated clinical fallback. Deterministic capabilities may continue only when their own prerequisites and safety controls remain available.

External-provider use requires approved boundaries for authorized data, processing location, subprocessors, retention/deletion, and secondary use including training. Provider defaults shall not determine clinical data policy. Changes to those boundaries or to model behavior require review before continued affected clinical use. If exact model-version information is unavailable, governance shall explicitly assess whether the available identification, change controls, and evaluation evidence are sufficient; merely recording “unknown” does not authorize deployment. An adapter enables replacement but does not make providers clinically interchangeable.

---

# 9. Knowledge Versioning

Clinical knowledge shall be versioned.

A Knowledge Object should have at minimum:

- unique identifier
- version
- status
- creation metadata
- modification metadata
- provenance
- lifecycle state

Example:

```text
NUT-STATE-002
    v1.0
    v1.1
    v1.2
```

A new version must not silently overwrite a previously published version.

The DATA-001 conceptual lifecycle is Draft → Under Review → Approved → Published, with subsequent Superseded or Retired states recorded through governance events. Approved does not itself mean published, effective, applicable, or deployed. Review specialties and implementation/deployment stages are distinct dimensions. Publication requires recorded clinical, knowledge, and engineering review and an authorized approval; deployment eligibility also requires applicability and validation checks. CAS-KOS-001's Clinical Review, Knowledge Review, Engineering Review, Implemented, Maintained, and Deprecated require an explicit mapping before migration; they must not be relabeled automatically.

Published content shall remain immutable. Exact dependency versions and the selected evidence versions shall be retained with a released output. Local extensions carry scope, jurisdiction, owner, review metadata, and effective periods. Publishing a newer global version must not silently erase or authorize a local exception.

---

# 10. Provenance

ClinRx shall be able to determine:

> Where did this information come from?

Provenance shall identify, as applicable:

- source
- source organization
- source version
- publication date
- retrieval date
- knowledge-object version
- reviewer
- approval status
- superseded version
- exact input fact and artifact versions
- execution and safety evaluation identifiers
- typed dependency relationships

Provenance is a graph of inputs, interpretations, computations, and outputs; audit records who changed or accessed them and why. These are related but separate responsibilities. Relationships themselves require identity, meaning, version, and evidence where relevant. Cycles in clinical concept relationships need not be prohibited, but execution dependencies must have a defined evaluation strategy rather than uncontrolled recursion.

---

# 11. Clinical Output Classification

ClinRx should distinguish different types of output.

### 11.1 Deterministic

Example:

```text
Creatinine clearance = 32 mL/min
```

### 11.2 Rule-derived

Example:

```text
Renal dose adjustment is required.
```

### 11.3 Evidence-derived

Example:

```text
Guideline X recommends...
```

### 11.4 AI-generated explanation

Example:

```text
Given the patient's renal function and current therapy...
```

These classifications describe how output claims were produced; they are separate from patient-fact origin and verification categories in DATA-001. One output can contain multiple classified claims. The distinction and supporting provenance shall remain available for auditing and validation. Evidence-derived content requires an assessed source link and applicability; it is not made authoritative by being generated in natural language.

---

# 12. Uncertainty and Missing Information

ClinRx must be capable of explicitly representing uncertainty. Missingness, time status, data origin, verification, evidence strength, and patient applicability must remain separate dimensions rather than a single status or confidence percentage.

The system should not invent missing clinical information.

Examples:

```text
Known
Unknown
Not measured
Not applicable
Historical
Inferred
```

If critical information is missing, ClinRx should be able to respond:

> Insufficient information to safely determine the recommendation.

rather than generating an unsupported answer.

---

# 13. Patient Timeline

ClinRx shall support the longitudinal context needed for each validated intended use.

Example:

```text
09:00  Creatinine 1.2
14:00  Creatinine 1.8
20:00  Creatinine 2.3
02:00  CRRT initiated
```

Clinical reasoning should be capable of distinguishing current state from trajectory. Values in the illustrative timeline above are not calculation inputs without units, dates, time-zone context, and source metadata.

The system must distinguish what was clinically true at an event time from what was known to ClinRx at a decision time. Late-arriving corrections are preserved without retroactively changing a prior snapshot. Re-evaluation against new data creates a new recommendation linked to the previous one. “Latest” requires a stated temporal and source-priority policy, not simply the last received record.

---

# 14. Auditability

ClinRx shall retain sufficient records to reconstruct how a clinically meaningful response was produced before that capability is used in patient care.

The audit chain should include, where applicable:

```text
Clinical Question
        |
        v
Patient Context Version
        |
        v
Knowledge Retrieved
        |
        v
Evidence Retrieved
        |
        v
Calculations
        |
        v
Rules Triggered
        |
        v
AI Model + Version
        |
        v
Safety Checks
        |
        v
Final Response
```

The purpose is reproducibility, quality improvement, debugging, and clinical governance. The chain is illustrative, not a mandatory call order.

Audit records include actor, action, authorization context, affected identity/version, time, reason, and previous/resulting state as applicable. They must be protected from unauthorized modification. Access to patient context, knowledge publication, overrides, model interactions, and downstream actions are auditable. Operational telemetry must minimize patient-identifiable content.

For each released or withheld clinical output, the decision record shall bind the candidate and rendered content to the verified patient/encounter context, freshness assessment, exact safety-policy and evaluated rule versions, coverage/results, authorization decision, and release or withholding decision with actor and time. Warning exceptions retain authority and rationale without overwriting the original evaluation. Retain what was actually presented and any subsequent withdrawal, stale designation, or correction. Evidence recoverability and its limitations follow Section 6.4. This record supports reconstruction of both the clinical inputs and the governance decision that permitted or prevented release.

Reproduction of deterministic results requires the original inputs, method, versions, configuration, and execution environment identifiers. Generative outputs may not be bit-for-bit reproducible even with model metadata; preserve the actual request context, authorized inputs, tool results, output, and displayed response under the retention policy. Auditability means reconstruction of the decision record, not a promise to regenerate identical model text or access private model reasoning.

---

# 15. Interoperability

ClinRx should be designed with healthcare interoperability in mind.

The architecture should be capable of future integration with:

- Electronic Health Records
- Laboratory Information Systems
- Pharmacy systems
- Microbiology systems
- Hospital Information Systems

Healthcare interoperability standards such as FHIR should be considered
during data-model design.

Full interoperability implementation is not required at the earliest stage,
but the internal architecture should avoid unnecessary incompatibility.

Adapters shall preserve source identifiers, namespaces, source versions, clinical time, units, provenance, and correction semantics. Internal ClinRx identities remain independent of SNOMED CT, LOINC, RxNorm, ICD, ATC, UCUM, and local system codes. Terminology mappings must identify system/version where known, mapping relationship and limitations, and review provenance; codes from different systems are not automatically equivalent. FHIR mappings require a separately reviewed profile/version strategy. No conformance or terminology license entitlement is implied by this draft.

Ambiguous identity matching shall be held for authorized resolution without combining patient records. Unresolved terminology mappings, incompatible or uncertain unit conversions, and clinically material information loss shall be rejected or quarantined from affected clinical reasoning, preserving the original source and error. Qualified use is permitted only where the intended-use policy establishes that the limitation cannot invalidate the proposed use and the limitation remains visible and traceable. ClinRx shall not guess a mapping or conversion to complete an answer; safety-critical unresolved failures block the affected recommendation.

Public and internal API contracts shall preserve the DATA-001 domain boundaries, stable identities, exact versions, explicit errors, and authorization context. Contract evolution needs compatibility policy; serialization must not erase clinical distinctions.

---

# 16. Security and Privacy

Clinical data should be treated as highly sensitive.

Before production patient-data use, the architecture shall support:

- authentication
- authorization
- role-based access
- encryption
- audit logging
- secure data storage
- data minimization
- tenant isolation
- secure API design
- appropriate retention policies

Security architecture shall be reviewed before real patient data is introduced. Patient facts, snapshots, recommendations, AI requests, audit records, caches, exports, and backups all remain inside defined privacy boundaries. Apply least privilege and tenant isolation to retrieval and model tools as well as storage. Minimize data sent to external providers and govern purpose, access, retention, and deletion obligations. Secrets must remain outside clinical content and prompts.

Historical retention does not mean unlimited or unlawful retention of identifiable patient information. A reviewed retention and deletion policy must reconcile audit needs with applicable obligations, preserving a record of authorized deletion or redaction where permitted. This standard defines design requirements, not a declaration of legal compliance.

---

# 17. Clinical Validation

Clinical functionality must be validated independently from general
software testing.

Validation shall include the following as applicable to the intended use:

- unit testing
- integration testing
- clinical rule testing
- calculation validation
- evidence validation
- edge-case testing
- adversarial testing
- hallucination testing
- regression testing
- clinician review
- prospective evaluation where appropriate

A feature shall not be considered clinically ready merely because its software tests pass. Release evidence must identify intended use, supported populations and settings, exclusions, clinical reviewers, acceptance criteria, validated versions, known limitations, and rollback criteria. Knowledge updates, formulas, rules, safety policy, and model changes each require proportionate validation and regression checks. Intended use and applicable regulatory requirements must be assessed by qualified owners before deployment; draft architecture is not authorization for clinical use.

## 17.1 Clinical Hazard Management

Clinical governance shall assign accountable owners for identifying hazards, selecting and verifying mitigations, and explicitly accepting or rejecting residual risk for each intended use. The safety case shall connect hazards to controls and validation evidence rather than equating a checklist of passed checks with clinical assurance. Incidents, new evidence, model changes, and observed misuse shall trigger proportionate reassessment.

Authorized safety owners shall be able to suspend affected knowledge, models, or workflows urgently without destroying their historical records. Provenance shall support identifying affected prior outputs for withdrawal, clinician notification, or reassessment according to clinical risk. Resumption requires documented review of the mitigation and remaining risk. Detailed hazard records, escalation thresholds, and suspension procedures belong in CLINRX-SAFE-001 and operational standards.

---

# 18. AI Evaluation

AI evaluation should assess more than linguistic quality.

Evaluation should include:

- factual accuracy
- evidence grounding
- clinical relevance
- omission errors
- unsafe recommendations
- hallucination rate
- appropriate uncertainty
- patient-context adherence
- citation correctness
- consistency
- robustness to ambiguous questions
- resistance to prompt manipulation

Clinical safety evaluation must remain separate from general model benchmark performance. Versioned evaluation sets should include missing, stale, contradictory, and out-of-scope patient information, citation errors, prompt injection, and failure of required services. Define measurable acceptance criteria and adjudication, track regressions and subgroup limitations, and protect evaluation data from inappropriate disclosure. Post-release monitoring and incident review must feed back into controlled changes rather than automatic unreviewed clinical learning.

---

# 19. Human Oversight

ClinRx is a clinical decision support system.

The clinician remains responsible for interpreting recommendations within
the appropriate clinical context.

The system should make this relationship clear through:

- transparent recommendations
- evidence access
- warnings
- uncertainty
- alternatives
- relevant patient context
- appropriate human confirmation

Clinician acceptance, rejection, correction, or override shall be recorded as a separate event with actor, time, rationale where required, and the reviewed recommendation version. Human confirmation does not retrospectively make an unsupported output valid. Permission to view advice does not grant permission to place an order. Autonomous downstream clinical action is outside this draft's authorized behavior and requires a separately approved intended use, safety case, and integration design.

Overrides are limited to the warnings and authorities defined in Section 6.7; their rationale is mandatory. Presentation shall make the patient/encounter, context currency, proposed action, material uncertainty, supporting evidence, and unresolved warnings understandable at the point of review. Human-factors validation shall address automation bias, alert fatigue, misleading certainty, warning prioritization, and whether clinicians can meaningfully inspect and reject advice under intended working conditions. Review shall not depend on hidden warnings or perfunctory confirmation; prioritization must not suppress material safety information.

---

# 20. Long-Term Technology Independence

ClinRx should avoid making core clinical functionality dependent on:

- one AI provider
- one database technology
- one frontend framework
- one cloud provider
- one software framework
- one proprietary data format

Technology choices may change.

Clinical concepts and governance should remain portable. Export/import and migration must preserve identity, exact versions, units, timestamps, relationships, provenance, and access restrictions.

## 20.1 Resilience and Recovery

Each clinical deployment shall define availability and recovery expectations, accountable escalation owners, and tested restoration procedures appropriate to its intended use. Recovery shall preserve the integrity of context, knowledge, access restrictions, and audit records. Restoring a service or backup shall not automatically reactivate stale recommendations, withdrawn knowledge, or suspended models; eligibility and applicable safety controls must be re-established.

A failed or stale dependency must have explicit behavior: block affected clinical recommendations, provide a clearly limited safe mode if validated, or escalate to a clinician. Retries and event-driven processing must avoid duplicate clinical actions. Continuous clinical interpretation from ADR-004 means governed reassessment on relevant changes, not an unbounded autonomous loop.

A degraded mode shall clearly expose unavailable capabilities and remain within its validated scope; it cannot bypass a hard failure defined in Section 6.7. Recovery and reprocessing shall reassess affected outputs without silently rewriting historical decisions. Detailed recovery targets, backup mechanisms, and incident procedures belong in deployment and operational standards.

---

# 21. Architecture Evolution

ClinRx architecture should evolve through explicit architectural decisions.

Significant architectural changes should be documented using Architecture
Decision Records (ADRs).

An ADR should record:

- problem
- context
- options considered
- decision
- consequences
- alternatives rejected
- date
- status

Accepted ADR-004–006 preserve the Domain → Engine → Specialty workflow separation. ADR-003 identifies CAS-CDS-001 as the Clinical Knowledge Standard; that file is not present in the active repository. CAS-KOS-001 and CAS-CKG-001 are supporting concept and graph specifications, not implicit replacements for a missing approved document. ADR-004's CAS-ARCH-003/004/005 engine references conflict with the current Container/Component/Data Architecture filenames. These reference and lifecycle conflicts require a governed reconciliation; this reconstruction does not silently rename documents or override accepted decisions.

DATA-001 provides detailed information semantics; ARCH-001 provides component and cross-cutting responsibilities. Repetition of invariants is intentional, but future detailed requirements should have a single owning standard and explicit cross-references. Physical schema and API implementation follow approval of the conceptual model and safety boundaries.

---

# 22. Principles for Future Development

Before implementing a major feature, the team should ask:

1. Does this improve clinical safety?
2. Is the clinical knowledge structured?
3. Is the evidence traceable?
4. Is the behavior deterministic where it should be?
5. Can the output be audited?
6. Can the underlying AI model be replaced?
7. What happens when information is missing?
8. What happens when the system is wrong?
9. Can the feature be clinically validated?
10. Will the design remain maintainable in ten years?

---

# 23. Architectural Anti-Patterns

ClinRx should explicitly avoid the following:

### AI as the database

The LLM must not become the clinical knowledge repository.

### AI as the calculator

Clinical calculations with defined mathematical or algorithmic logic shall use validated deterministic implementations; language-model reasoning shall not serve as their authoritative calculator.

### Silent knowledge replacement

Published clinical knowledge must not be silently overwritten.

### Untraceable recommendations

Clinically meaningful recommendations should have an identifiable basis.

### False precision

ClinRx should not manufacture numerical confidence when the underlying
uncertainty cannot be quantified meaningfully.

### Feature-first development

New features should not be prioritized at the expense of foundational
clinical architecture.

### Vendor lock-in

Core clinical functionality should remain independent of a specific AI
provider.

---

# 24. Long-Term Vision

ClinRx should evolve into a clinical reasoning infrastructure rather than
simply an AI chatbot.

The logical architecture in Section 5 is the governing flow. Knowledge, Patient Context, Evidence, and reusable Clinical Engines remain durable platform responsibilities; any AI synthesis and rendering remain within the final safety and validation boundary.

The objective is not to automate clinical judgment.

The objective is to provide clinicians with a system that is:

- evidence-grounded
- patient-aware
- transparent
- reproducible
- auditable
- continuously maintainable
- clinically validated
- AI-model independent

---

# 25. Definition of Clinical Trust

ClinRx should earn clinical trust through architecture and evidence rather
than through branding or claims.

A clinician should be able to ask:

> What do you know?

> Where did you get it?

> Does it apply to my patient?

> How did you calculate this?

> What are the risks?

> What information are you missing?

> How certain are you?

> What evidence supports this?

> Can I verify it?

The architecture should make these questions answerable.

---

# 26. Status and Implementation Gates

This is a reconstructed Draft, not a clinically approved implementation specification. The repository currently demonstrates JSON-backed knowledge retrieval and typed search results; it does not demonstrate the complete patient-context, evidence, version-selection, safety, or recommendation platform described here. In particular, retrieval relevance scores and an Approved label are not production clinical eligibility controls.

Before clinical implementation proceeds, review and approve the architecture and DATA-001 conceptual model, reconcile legacy terminology and accepted ADR references, and define the detailed safety standard (planned CLINRX-SAFE-001). Before real patient integration, approve security, privacy, retention, and interoperability boundaries. Before any clinical release, complete intended-use-specific validation, human workflow review, operational recovery checks, and release authorization.

The staged path is conceptual standards → safety and governance specifications → physical schema and API contracts → validated deterministic capabilities → controlled AI integration → clinically evaluated workflows. Research prototypes may explore these capabilities using appropriate non-patient or authorized test data, but must remain clearly separated from production clinical claims.

Completion of this document means a coherent draft is available for review. Adoption requires named architectural and clinical reviewers, resolved blocking issues, approval metadata, and an effective date. No approval is implied by the reconstruction.

---

# 27. Document Control and Reconstruction Record

**Document ID:** CLINRX-ARCH-001

**Title:** Long-Term Clinical AI Architecture Standard

**Version:** 1.1

**Status:** Draft

**Date:** 2026-09-25

**Effective Date:** Pending approval

**Owner:** ClinRx AI

**Supersedes upon approval:** Incomplete Version 1.0 draft dated 2026-09-24

**Approval:** Pending user, architecture, and clinical review

Version 1.0 was committed as `dfefedd6ae084f72b7d6e8955a94e6f6fec5f41d` on 2026-09-25 with 236 logical lines. Its final line was `Active` within the open code fence in Section 4.8; the working copy at the start of reconstruction matched that committed content. The file had no closing fence or final newline. This confirms incomplete content existed at the initial commit, not that Git subsequently truncated it.

A complete 25-section alternative draft (labeled Version 0.1) was recovered from the referenced ClinRx AI Project Plan conversation, assistant message `f3c7ac8c-c05f-4cce-8811-850d1b37fc17`. The recovered text differs from the saved Version 1.0 introduction. This Version 1.1 therefore preserves the saved opening principles and reconstructs the remainder from that draft, the preceding architecture review, accepted ADRs, CAS concept/graph specifications, and DATA-001. It is not presented as a byte-for-byte restoration of an unavailable Version 1.0 original.

The conversation's draft used a triple-backtick outer Markdown fence around content containing triple-backtick diagrams. That formatting is a plausible contributor to incomplete copying. The recorded save/commit workflow checked status and line count without verifying the final section. The precise clipboard or editor event is not recoverable; copy/paste truncation remains an inference.

Reconstruction changes include complete component responsibilities, the Domain/Engine/Specialty relationship, final safety validation after AI transformations, governed publication and applicability, temporal audit records, human oversight, failure behavior, and explicit implementation gates. At that reconstruction stage, DATA-001 was unchanged pending consistency review; DATA-001 Version 0.3 Draft subsequently completed the candidate-parent alignment.

Candidate revision following substantive review: clarified exact-meaning validation and release sequencing, patient/encounter binding and freshness, safety coverage and warning exceptions, AI inference boundaries, hazard management, human factors, provider governance, interoperability failures, evidence recovery, audit decisions, and resilience. Version 1.1 remains Draft pending approval. The reviewed candidate has now replaced the previously truncated repository copy; this cleanup changes only formatting and historical notes, not substantive requirements.

The canonical repository filename remains `CLINRX-ARCH-001-Long-Term-Clinical-AI-Architecture.md`; the longer `...-Architecture-Standard.md` name used in the request was not present. No duplicate standard is created.

**AI reasons. ClinRx governs.**
