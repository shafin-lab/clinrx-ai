# CAS-CKG-001 — ClinRx Clinical Knowledge Graph Specification

**Document ID:** CAS-CKG-001

**Version:** 1.0

**Status:** Draft

**Owner:** ClinRx AI Architecture

---

# Purpose

This document defines the ClinRx Clinical Knowledge Graph (CKG), the canonical representation of clinical knowledge within the ClinRx AI platform.

The CKG provides the common language through which Clinical Domains, Clinical Engines, Evidence Documents, and Specialty Operating Systems understand, share, and reason about patient information.

It represents medicine as a network of evolving relationships rather than isolated facts.

---

# Clinical Philosophy

Medicine is not a collection of independent observations.

It is a continuously evolving network of physiological states, clinical processes, therapeutic interventions, and evidence-supported relationships.

ClinRx AI therefore models patients as interconnected clinical knowledge rather than isolated data points.

Clinical reasoning emerges from understanding these relationships.

---

# Scope

The Clinical Knowledge Graph defines:

- Clinical object classes
- Relationship types
- Knowledge representation
- Shared terminology
- Metadata standards
- Inter-domain connectivity

It does not define:

- Database implementation
- Graph database technology
- APIs
- Storage engines
- Programming languages

The CKG is implementation-independent.

---

# Design Principles

The ClinRx Clinical Knowledge Graph shall be:

- Patient-centric
- Explainable
- Evidence-based
- Continuously evolving
- Domain-independent
- Reusable
- Extensible
- Version controlled

---

# Fundamental Object Classes

All medical knowledge within ClinRx AI shall belong to one or more of the following object classes.

---

## 1. Observation

Represents raw clinical information obtained from the patient.

Examples:

- Heart Rate
- Blood Pressure
- Creatinine
- Lactate
- Albumin
- Weight
- Urine Output
- Respiratory Rate

Question answered:

> What do we observe?

---

## 2. Clinical State

Represents an interpreted understanding of the patient's current condition.

Examples:

- Hypercatabolic State
- AKI Stage 2
- Septic Shock
- High Nutritional Risk
- Stable Hemodynamics

Question answered:

> What is currently true about the patient?

---

## 3. Clinical Process

Represents ongoing biological or physiological activity.

Examples:

- Inflammation
- Catabolism
- Anabolism
- Fibrosis
- Tissue Healing
- Muscle Protein Breakdown

Question answered:

> What is happening biologically?

---

## 4. Clinical Phenotype

Represents clinical contexts that modify reasoning.

Examples:

- Liver Transplant
- CRRT
- ECMO
- Pregnancy
- Burns
- Morbid Obesity
- Frailty

Question answered:

> What clinical context modifies interpretation?

---

## 5. Clinical Intervention

Represents therapeutic actions performed by clinicians.

Examples:

- Enteral Nutrition
- Mechanical Ventilation
- Meropenem
- Vasopressors
- CRRT
- Surgery

Question answered:

> What are we doing?

---

## 6. Clinical Resource

Represents physiological reserve or capacity.

Examples:

- Lean Body Mass
- Glycogen Stores
- Protein Reserve
- Liver Reserve
- Renal Reserve

Question answered:

> What physiological reserve exists?

---

## 7. Clinical Outcome

Represents desired or observed clinical endpoints.

Examples:

- Recovery
- Survival
- Infection Clearance
- Muscle Preservation
- Functional Independence
- Graft Function

Question answered:

> What are we trying to achieve?

---

## 8. Evidence

Represents the scientific basis supporting clinical reasoning.

Examples:

- ESPEN
- ASPEN
- KDIGO
- IDSA
- TARGET Trial
- EFFORT Trial

Question answered:

> Why do we believe this?

---

# Relationship Types

Relationships are first-class entities within the Clinical Knowledge Graph.

Every relationship shall have explicit meaning.

Approved relationship types include:

| Relationship | Meaning |
|--------------|---------|
| has | Structural ownership |
| observes | Raw observation |
| derives | Interpretation from observations |
| influences | Physiological influence |
| causes | Direct causal relationship |
| modifies | Alters behaviour of another concept |
| contributes_to | Multifactorial contribution |
| increases_risk_of | Risk relationship |
| decreases | Negative influence |
| depends_on | Dependency |
| indicates | Diagnostic implication |
| contraindicates | Safety restriction |
| requires_monitoring_of | Monitoring requirement |
| supports | Therapeutic support |
| resolves | Recovery relationship |

Additional relationship types may be introduced through future architectural review.

---

# Knowledge Representation

Clinical reasoning shall emerge from traversing connected concepts rather than isolated rules.

Example:

Patient

↓

Observation

↓

Clinical State

↓

Clinical Process

↓

Clinical Intervention

↓

Clinical Outcome

Every Clinical Domain contributes nodes and relationships to this shared graph.

---

# Node Metadata Standard

Every node shall define:

- Identifier
- Name
- Definition
- Object Class
- Properties
- Incoming Relationships
- Outgoing Relationships
- Evidence References
- Version
- Owner

---

# Relationship Metadata Standard

Every relationship shall define:

- Source Node
- Target Node
- Relationship Type
- Definition
- Evidence
- Confidence (optional)
- Version

---

# Clinical Reasoning

Clinical Engines shall consume the Clinical Knowledge Graph rather than isolated observations.

Reasoning shall emerge from:

- Observations
- States
- Processes
- Phenotypes
- Interventions
- Evidence
- Relationships

The CKG provides explainable pathways from observation to interpretation.

---

# Guiding Principle

Every concept must explicitly declare:

- What influences it.
- What it influences.
- How it changes over time.
- Which Clinical Domains consume it.
- Which Clinical Engines reason over it.

Concepts without relationships are incomplete.

---

# Vision

The ClinRx Clinical Knowledge Graph forms the intellectual foundation of the ClinRx AI platform.

It enables reusable, explainable, evidence-based clinical reasoning across every Clinical Domain, Clinical Engine, and Specialty Operating System.

Rather than representing medicine as isolated facts, the CKG represents medicine as an interconnected network of evolving clinical knowledge.

---

> **Medicine is not a collection of facts. It is a network of relationships evolving over time. ClinRx AI exists to represent, understand, and reason over that network in partnership with clinicians.**