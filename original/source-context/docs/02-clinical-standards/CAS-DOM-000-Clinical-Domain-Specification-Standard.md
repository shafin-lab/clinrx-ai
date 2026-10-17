# CAS-DOM-000 — Clinical Domain Specification Standard

**Document ID:** CAS-DOM-000

**Version:** 1.0

**Status:** Approved

**Owner:** ClinRx AI Architecture

---

# Purpose

This document defines the mandatory structure and governance for every Clinical Domain within ClinRx AI.

Its purpose is to ensure that all Clinical Domains are:

- Clinically consistent
- Reusable across specialties
- Evidence-based
- Explainable
- Independent of software implementation
- Independent of specialty-specific workflows

Every future Clinical Domain Specification shall conform to this standard.

---

# Guiding Philosophy

A Clinical Domain is not:

- a calculator
- a protocol
- an order set
- a guideline
- a software module

A Clinical Domain is a structured representation of one area of clinical medicine.

It defines how ClinRx AI understands, interprets, reasons about, and communicates that aspect of medicine.

---

# Mandatory Sections

Every Clinical Domain Specification shall contain the following sections.

---

## 1. Purpose

Defines why the Clinical Domain exists.

---

## 2. Scope

Defines:

- Included concepts
- Excluded concepts
- Dependencies
- Interfaces with other Clinical Domains

---

## 3. Core Clinical Concepts

Defines:

- Terminology
- Definitions
- Relationships
- Clinical meaning

---

## 4. Clinical Phenotypes

Defines patient contexts that modify reasoning.

Examples include:

- Septic Shock
- CRRT
- ECMO
- Acute Liver Failure
- Liver Transplant
- Burns
- Pregnancy
- Morbid Obesity
- Frailty

Clinical Phenotypes represent reasoning contexts rather than diagnoses.

---

## 5. Clinical Observations

Defines all observations consumed by the Clinical Domain.

Examples include:

- Vital signs
- Laboratory investigations
- Imaging
- Monitoring devices
- Medication exposure
- Nutrition delivery
- Ventilator parameters
- Clinical examination
- Timeline

---

## 6. Derived Clinical State

Defines how observations are transformed into meaningful clinical understanding.

Examples include:

- Early Acute Flow Phase
- High Nutritional Risk
- Stage 2 AKI
- Enteral Feeding Intolerance
- Hyperdynamic Shock
- High Bleeding Risk

Derived Clinical States represent clinical interpretation rather than raw data.

---

## 7. Clinical Reasoning

Defines the reasoning pathway used by the Clinical Domain.

Clinical reasoning shall integrate:

- Clinical Phenotypes
- Clinical Observations
- Derived Clinical State
- Evidence-supported knowledge
- Safety considerations
- Monitoring priorities

Clinical reasoning shall support clinician decision-making without directly prescribing treatment.

---

## 8. Evidence Layer

Every Clinical Domain shall reference one or more associated Clinical Evidence Documents (CAS-EVD).

Evidence shall be maintained independently of the Clinical Domain Specification to facilitate future evidence updates.

---

## 9. Safety Framework

Defines:

- Contraindications
- Evidence limitations
- Uncertainty
- Monitoring triggers
- Escalation criteria
- Situations requiring clinician review

Patient safety shall always take precedence over automation.

---

## 10. Structured Outputs

Every Clinical Domain shall expose standardized outputs including:

- Clinical State
- Risk Profile
- Evidence References
- Confidence
- Monitoring Priorities
- Safety Alerts

These outputs provide the interface between Clinical Domains and Clinical Engines.

---

## 11. Clinical Narrative

Every Clinical Domain shall generate a clinician-readable narrative describing:

- Current clinical interpretation
- Clinical reasoning
- Relevant risks
- Evidence-supported considerations
- Monitoring priorities

The Clinical Narrative explains reasoning while preserving clinician autonomy.

---

## 12. Future Extensions

Defines areas suitable for future enhancement without altering the core Clinical Domain architecture.

Examples include:

- Machine learning integration
- Continuous monitoring devices
- Wearable data
- Omics integration
- Predictive analytics

---

# Clinical Reasoning Cycle

Every Clinical Domain shall follow the same reasoning model.

Patient

↓

Clinical Observations

↓

Clinical Phenotype Recognition

↓

Derived Clinical State

↓

Evidence-supported Clinical Reasoning

↓

Risk Assessment

↓

Safety Evaluation

↓

Structured Outputs

↓

Clinical Narrative

---

# Clinical Domain Acceptance Checklist

Before approval, every Clinical Domain shall demonstrate:

- Clear purpose
- Defined scope
- Core clinical concepts
- Clinical phenotypes
- Required clinical observations
- Derived clinical states
- Evidence-supported reasoning
- Referenced evidence base
- Safety framework
- Standardized outputs
- Clinician-readable narrative

Clinical Domains that do not satisfy these criteria shall not be considered complete.

---

# Vision Statement

Clinical Domains form the clinical knowledge foundation of ClinRx AI.

They provide reusable, explainable, evidence-based representations of medicine that remain independent of implementation while supporting every Clinical Engine and Specialty Operating System within the ClinRx AI ecosystem.

---

**Clinical knowledge before implementation. Clinical reasoning before automation.**