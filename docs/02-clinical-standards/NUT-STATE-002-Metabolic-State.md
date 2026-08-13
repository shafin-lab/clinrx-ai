# NUT-STATE-002 — Metabolic State

**Artifact Type:** Clinical Knowledge Object

**Conforms to:** CAS-KOS-001 v1.0

**Knowledge Graph Standard:** CAS-CKG-001

**Clinical Domain Standard:** CAS-DOM-001 – Nutrition & Metabolism

---

**Identifier:** NUT-STATE-002

**Version:** 1.0

**Status:** Draft

**Domain:** Nutrition & Metabolism

**Object Class:** Clinical State

**Owner:** ClinRx AI

---

# 1. Definition

## Statement

Metabolic State is the continuously evolving clinical representation of a patient's metabolic condition, reflecting the balance between energy production, energy utilization, substrate availability, hormonal regulation, and physiological adaptation to health or disease.

## Interpretation

Metabolic State integrates the patient's metabolic response to illness, injury, nutrition support, inflammation, endocrine regulation, organ function, and recovery into a single interpretable Clinical State. Metabolic State reflects the dynamic interaction between anabolic and catabolic processes that determine the patient's physiological capacity to maintain homeostasis and respond to stress

It represents the overall metabolic condition of the patient rather than isolated biochemical measurements or individual metabolic pathways.

As a Clinical State, Metabolic State continuously evolves throughout the patient's clinical journey and requires reassessment as physiological conditions change.

## Exclusions

Metabolic State is **not**:

- A single laboratory value.
- Blood glucose concentration.
- Lactate concentration.
- Acid–base status.
- A diagnosis.
- A nutritional prescription.
- An endocrine disorder.
- An isolated metabolic pathway.

---

# 2. Purpose

## Primary Purpose

Provide the canonical representation of a patient's overall metabolic condition within the ClinRx Clinical Knowledge Graph.

## Secondary Purposes

- Support interpretation of metabolic adaptation during illness and recovery.
- Provide context for downstream Clinical Knowledge Objects.
- Enable longitudinal metabolic assessment.
- Standardize metabolic reasoning across Clinical Domains.
- Support explainable clinical reasoning throughout the ClinRx platform.

## Boundaries (Non-Purpose)

Metabolic State does **not**:

- diagnose metabolic diseases.
- calculate energy expenditure.
- prescribe nutrition therapy.
- recommend insulin therapy.
- recommend metabolic interventions.
- independently generate clinical recommendations.

These responsibilities belong to downstream Clinical Engines reasoning over multiple interconnected Clinical Knowledge Objects.

---

# 3. Clinical Significance

Metabolic State is a central determinant of physiological adaptation during health, critical illness, injury, and recovery.

It influences energy utilization, protein turnover, substrate mobilisation, immune function, organ performance, response to nutrition support, and overall recovery.

In critically ill patients, Metabolic State is shaped by the interaction of inflammation, endocrine responses, nutritional intake, organ dysfunction, and therapeutic interventions.

Within ClinRx AI, Metabolic State serves as a foundational Clinical State supporting nutritional reasoning, critical care assessment, perioperative management, and future Clinical Intelligence Engines.

---

# Design Notes

This Clinical Knowledge Object represents the canonical interpretation of a patient's overall metabolic condition within the ClinRx AI platform.

Subsequent sections will define:

- Attributes
- Derived From
- Supported By Clinical Observations
- Influences
- Temporal Behaviour
- Clinical Reasoning
- Evidence Foundation
- Evidence Traceability
- Knowledge Graph Connections
- Clinical Reasoning Capabilities
- Consumers
- Related Knowledge Objects
- Design Intent

---

# 4. Attributes

Metabolic State possesses the following intrinsic characteristics.

## Dynamic

Metabolic State continuously changes in response to physiology, disease, nutrition, endocrine regulation, and therapeutic interventions.

## Adaptive

Metabolic State reflects the body's ability to adapt to health, stress, injury, and recovery through coordinated metabolic responses.

## Multidimensional

Metabolic State integrates energy metabolism, substrate utilization, protein turnover, hormonal regulation, inflammation, and organ function into a unified Clinical State.

## Context-dependent

Interpretation depends upon disease severity, physiological stress, nutritional intake, endocrine responses, and organ function.

## Longitudinal

Metabolic State should always be interpreted as an evolving physiological trajectory rather than an isolated assessment.

## Explainable

Every interpretation of Metabolic State should be traceable to identifiable clinical observations and supporting scientific evidence.

---

# 5. Derived From

Metabolic State emerges from the interaction of multiple upstream Clinical Knowledge Objects.

## Clinical States

- Inflammatory State
- Endocrine State
- Hepatic Function
- Renal Function
- Body Composition State

## Clinical Processes

- Catabolism
- Anabolism
- Glucose Metabolism
- Lipid Metabolism
- Protein Metabolism

## Clinical Phenotypes

- Hypermetabolism
- Metabolic Dysfunction
- Insulin Resistance

## Clinical Resources

- Nutrition Support

## Clinical Interventions

- Insulin Therapy
- Metabolic Monitoring

As the ClinRx Clinical Knowledge Graph matures, these conceptual references shall be replaced by explicit Knowledge Object relationships conforming to CAS-CKG-001.

---

# 6. Supported By Clinical Observations

Metabolic State is inferred through integration of multiple observations rather than individual measurements.

## Clinical Assessment

- Nutritional history
- Recent weight change
- Functional capacity
- Clinical evidence of catabolism
- Recent changes in body composition (when available)

## Laboratory Investigations

- Blood glucose
- Lactate
- Electrolytes
- Blood ketones (when appropriate)
- Liver function tests
- Renal function tests
- Arterial blood gas (where clinically relevant)

## Physiological Monitoring

- Indirect calorimetry (when available)
- Energy expenditure assessment
- Nitrogen balance (where measured)
- Respiratory quotient (when indirect calorimetry is available)

## Nutrition Monitoring

- Calorie delivery
- Protein delivery
- Feeding adequacy
- Feeding interruptions

No individual observation independently defines Metabolic State.

---

# 7. Influences

Metabolic State influences multiple downstream Clinical Knowledge Objects.

## Clinical States

- Nutritional State
- Recovery State
- Immune State
- Functional State

## Clinical Processes

- Catabolism
- Anabolism
- Wound healing
- Tissue repair

## Clinical Outcomes

- Recovery
- ICU length of stay
- Functional outcomes
- Mortality

Metabolic State contributes to downstream reasoning but does not independently determine clinical decisions.

---

# 8. Temporal Behaviour

Metabolic State evolves continuously throughout the patient's clinical course.

Its trajectory reflects the interaction between illness severity, inflammation, endocrine regulation, nutrition support, organ function, and recovery.

## Temporal Characteristics

- Baseline metabolic health
- Acute metabolic adaptation
- Hypermetabolic phase
- Recovery phase
- Long-term metabolic restoration

## Reassessment Triggers

Metabolic State should be reassessed following:

- Major surgery
- ICU admission
- Significant clinical deterioration
- Major changes in nutrition support
- Major endocrine changes
- Recovery from critical illness

Metabolic State should always be interpreted as a dynamic physiological trajectory.

---

# 9. Clinical Reasoning

Metabolic State is interpreted through the integration of multiple Clinical Knowledge Objects rather than isolated laboratory values or physiological measurements.

Clinical reasoning should consider:

- Energy production and utilization
- Substrate availability
- Anabolic and catabolic balance
- Endocrine regulation
- Inflammatory burden
- Organ function
- Nutrition support
- Physiological adaptation
- Temporal clinical trajectory

Interpretation shall always consider the patient's overall physiological context rather than isolated biochemical abnormalities.

Clinical reasoning within this Knowledge Object represents clinician thought processes and does not include predictive algorithms, equations, or treatment recommendations.

---

# 10. Evidence Foundation

The interpretation of Metabolic State shall be supported by established physiological principles and high-quality scientific evidence.

## Clinical Practice Guidelines

Examples include:

- ESPEN Clinical Nutrition Guidelines
- ASPEN/SCCM Clinical Nutrition Guidelines

## Consensus Statements

Examples include:

- GLIM Consensus
- International Critical Care Nutrition Recommendations

## Scientific Evidence

Examples include:

- Energy metabolism
- Protein metabolism
- Glucose metabolism
- Lipid metabolism
- Critical illness physiology
- Endocrine stress response

## Foundational Physiology

Examples include:

- Cellular energy production
- Mitochondrial physiology
- Hormonal regulation
- Organ-specific metabolism

The Evidence Foundation shall evolve as new scientific evidence becomes available.

---

# 11. Evidence Traceability

Every major interpretation of Metabolic State should be traceable to supporting scientific evidence.

ClinRx AI shall preserve the relationship between:

Patient-specific Clinical Observations

↓

Clinical Interpretation

↓

Supporting Scientific Evidence

This ensures explainability, transparency, and auditability of clinical reasoning.

Future versions may reference dedicated Clinical Evidence Objects.

---

# 12. Knowledge Graph Connections

Metabolic State exists as a central physiological node within the ClinRx Clinical Knowledge Graph.

Examples of incoming relationships include:

- derived_from
- influenced_by
- supported_by
- modified_by

Examples of outgoing relationships include:

- influences
- informs
- contributes_to
- enables

Relationship definitions shall conform to CAS-CKG-001.

---

# 13. Clinical Reasoning Capabilities

Metabolic State enables ClinRx AI to:

- Assess metabolic adaptation
- Interpret metabolic trajectory
- Identify metabolic deterioration
- Evaluate physiological response to illness
- Provide context for nutritional reasoning
- Support downstream Clinical Engines

This Knowledge Object provides context rather than recommendations.

---

# 14. Consumers

This Knowledge Object may be consumed by:

## Clinical Domains

- Nutrition & Metabolism
- Critical Care
- Hepatology
- Nephrology
- Endocrinology

## Clinical Engines

- Nutrition Intelligence Engine
- Critical Care Intelligence Engine
- Perioperative Intelligence Engine

## Specialty Operating Systems

- ICU Operating System
- Liver Transplant Operating System
- Anti-Infective Operating System

## ClinRx Flow

- AI Clinical Summary
- Clinical Timeline
- Clinical Reasoning Viewer

---

# 15. Related Knowledge Objects

## Parent Objects

None

## Peer Objects

- Nutritional State
- Inflammatory State
- Hemodynamic State

## Child Objects

Examples include:

- Catabolism
- Anabolism
- Protein Metabolism
- Glucose Metabolism
- Lipid Metabolism

---

# 16. Design Intent

Metabolic State serves as one of the foundational physiological Clinical States within the ClinRx AI platform.

It provides a reusable representation of the patient's metabolic condition that can be interpreted across multiple Clinical Domains and consumed by diverse Clinical Engines.

By separating metabolic interpretation from observations, interventions, and clinical decisions, Metabolic State enables explainable, reusable, and longitudinal clinical reasoning throughout ClinRx AI.

---

# Version History

## Version 1.0

Initial Clinical Knowledge Object.