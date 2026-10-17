# NUT-STATE-001 — Nutritional State

**Clinical Knowledge Object**

Conforms to: CAS-KOS-001 v1.0

Knowledge Graph Standard: CAS-CKG-001

Clinical Domain: CAS-DOM-001 Nutrition & Metabolism

**Identifier:** NUT-STATE-001

**Version:** 1.0

**Status:** Draft

**Domain:** Nutrition & Metabolism

**Object Class:** Clinical State

**Owner:** ClinRx AI

---

# 1. Definition

## Statement

Nutritional State is the continuously evolving clinical representation of a patient's nutritional health and physiological capacity to tolerate, respond to, and recover from illness or injury.

## Interpretation

Nutritional State integrates nutritional reserve, nutrient availability, metabolic demand, inflammatory burden, organ function, body composition, functional capacity, and the patient's response to nutrition therapy into a single interpretable clinical state.

It represents the patient's overall nutritional condition rather than any individual observation, laboratory value, diagnosis, or intervention.

As a Clinical State, Nutritional State evolves continuously throughout the patient's clinical journey and requires ongoing reassessment as new clinical information becomes available.

## Exclusions

Nutritional State is **not**:

- A laboratory measurement.
- A nutritional screening score.
- A diagnosis.
- A feeding prescription.
- A calorie target.
- A protein target.
- An isolated anthropometric measurement.
- A single nutritional observation.

---

# 2. Purpose

## Primary Purpose

Provide the canonical representation of a patient's nutritional condition within the ClinRx Clinical Knowledge Graph.

## Secondary Purposes

- Support nutrition-related clinical reasoning.
- Provide contextual information for downstream Clinical Engines.
- Enable longitudinal assessment of nutritional health.
- Standardize nutritional interpretation across Clinical Domains.
- Support explainable clinical reasoning across the ClinRx platform.

## Boundaries (Non-Purpose)

Nutritional State does **not**:

- prescribe nutritional therapy.
- calculate calorie requirements.
- calculate protein requirements.
- recommend feeding routes.
- diagnose malnutrition independently.
- generate clinical recommendations.

These responsibilities belong to downstream Clinical Engines reasoning over multiple Clinical Knowledge Objects.

---

# 3. Clinical Significance

Nutritional State influences nearly every aspect of critical illness, including immune function, wound healing, skeletal muscle preservation, respiratory performance, organ recovery, infection susceptibility, rehabilitation potential, and overall clinical outcomes.

In critically ill patients, Nutritional State evolves continuously in response to disease severity, inflammatory burden, endogenous substrate production, nutritional therapy, and physiological recovery.

Accurate representation of Nutritional State enables clinicians to interpret nutritional adequacy within the broader physiological context rather than relying on isolated nutritional metrics.

Within ClinRx AI, Nutritional State serves as a foundational Clinical State informing multiple Clinical Domains, Clinical Engines, and Specialty Operating Systems.

---

# Design Notes

This Clinical Knowledge Object represents the canonical nutritional interpretation of the patient within the ClinRx AI platform.

Subsequent sections will define:

- Attributes
- Derived From
- Supported By Clinical Observations
- Influences
- Temporal Behaviour
- Clinical Reasoning
- Evidence Foundation
- Knowledge Graph Connections
- Clinical Reasoning Capabilities
- Consumers
- Related Knowledge Objects
- Design Intent

---

# 4. Attributes

Nutritional State possesses the following intrinsic characteristics.

## Dynamic

Nutritional State continuously evolves throughout the patient's clinical course and shall never be considered static.

## Multidimensional

Nutritional State represents the interaction of nutritional reserve, metabolic demand, inflammatory burden, organ function, body composition, functional capacity, and response to nutrition support.

## Context-dependent

Interpretation depends upon the patient's disease process, severity of illness, physiological stress, organ dysfunction, and therapeutic interventions.

## Longitudinal

Nutritional State should be interpreted as an evolving trajectory rather than an isolated assessment.

## Explainable

Every interpretation of Nutritional State should be traceable to identifiable clinical observations and supporting evidence.

## Clinically Meaningful

Nutritional State provides a clinically interpretable representation of nutritional health that supports patient understanding and downstream clinical reasoning.

---

# 5. Derived From

Nutritional State emerges from the interaction of multiple upstream Clinical Knowledge Objects rather than a single observation.

## Clinical States

- Metabolic State
- Functional State
- Body Composition State
- Inflammatory State
- Gastrointestinal Function
- Hepatic Function
- Renal Function

## Clinical Processes

- Catabolism
- Anabolism
- Hypermetabolism
- Protein Turnover
- Nutrient Utilization

## Clinical Phenotypes

- Malnutrition
- Sarcopenia
- Cachexia
- Frailty
- Obesity

## Clinical Resources

- Oral Nutrition
- Enteral Nutrition
- Parenteral Nutrition

## Clinical Interventions

- Nutrition Support
- Micronutrient Supplementation
- Nutrition Monitoring

As the ClinRx Clinical Knowledge Graph matures, these conceptual references shall be replaced by explicit Knowledge Object relationships conforming to CAS-CKG-001.

---

# 6. Supported By Clinical Observations

Nutritional State is inferred through the integration of multiple patient-specific observations rather than any individual finding.

## Clinical Assessment

- Nutrition history
- Dietary intake
- Appetite
- Recent weight loss
- Physical examination
- Muscle wasting
- Loss of subcutaneous fat
- Presence of oedema or fluid overload
- Functional performance

## Anthropometry

- Body weight
- Height
- Body Mass Index (BMI)
- Mid-arm circumference
- Calf circumference
- Body composition assessment

## Laboratory Investigations

- C-reactive protein (CRP)
- Prealbumin (when clinically appropriate)
- Nitrogen balance (where measured)
- Electrolytes relevant to nutrition
- Micronutrient concentrations (when indicated)

## Functional Assessment

- Handgrip strength
- Functional mobility
- Frailty assessment
- Sarcopenia assessment

## Nutrition Support Monitoring

- Oral intake
- Enteral nutrition delivered
- Parenteral nutrition delivered
- Energy adequacy
- Protein adequacy
- Feeding interruptions

No individual observation independently defines Nutritional State.

Clinical interpretation always requires integration of multiple observations.

---

# 7. Influences

Nutritional State influences downstream Clinical Knowledge Objects, Clinical Domains, Clinical Engines, and patient outcomes.

## Clinical States

- Recovery State
- Functional State
- Immune State
- Metabolic State

## Clinical Processes

- Wound healing
- Immune response
- Muscle protein synthesis
- Tissue repair
- Rehabilitation

## Clinical Decisions

- Nutritional assessment frequency
- Selection of nutrition support
- Route of nutritional support
- Monitoring priorities

## Clinical Outcomes

- Infection susceptibility
- Duration of mechanical ventilation
- ICU length of stay
- Hospital length of stay
- Functional recovery
- Mortality

Nutritional State contributes to downstream reasoning but does not independently determine clinical decisions.

---

# 8. Temporal Behaviour

Nutritional State continuously evolves throughout the patient's clinical journey.

Its trajectory reflects the interaction between disease severity, inflammation, metabolism, nutrition support, organ recovery, and rehabilitation.

## Temporal Characteristics

- Baseline nutritional reserve
- Acute deterioration
- Progressive nutritional recovery
- Functional restoration
- Long-term recovery

## Reassessment Triggers

Nutritional State should be reassessed following:

- Significant clinical deterioration
- Major surgery
- ICU admission
- ICU discharge
- Initiation or discontinuation of nutrition support
- Development of organ dysfunction
- Major change in inflammatory burden

Nutritional State should always be interpreted as a longitudinal clinical trajectory rather than a single point-in-time assessment.

---

# 9. Clinical Reasoning

Nutritional State is interpreted through the synthesis of multiple interconnected Clinical Knowledge Objects rather than isolated observations.

Clinical reasoning should consider:

- Nutritional reserve
- Metabolic demand
- Inflammatory burden
- Organ function
- Body composition
- Functional capacity
- Response to nutrition support
- Temporal clinical trajectory

Interpretation shall always integrate the overall clinical context rather than relying upon individual measurements.

Clinical reasoning within this Knowledge Object represents clinician thought processes and does not include algorithms, equations, predictive models, or treatment recommendations.

---

# 10. Evidence Foundation

The interpretation of Nutritional State shall be supported by high-quality scientific evidence and established physiological principles.

## Clinical Practice Guidelines

Examples include:

- ESPEN Clinical Nutrition Guidelines
- ASPEN/SCCM Clinical Nutrition Guidelines
- GLIM Consensus Criteria

## Randomized Controlled Trials

Examples include:

- EFFORT Protein Trial
- TARGET Trial
- PRECISe Trial

## Systematic Reviews

Current systematic reviews and meta-analyses relevant to nutritional assessment and nutrition support.

## Physiological Evidence

Examples include:

- Protein turnover
- Energy metabolism
- Endogenous glucose production
- Starvation physiology
- Recovery physiology

The Evidence Foundation shall evolve as scientific evidence matures.

---

# 11. Evidence Traceability

Every major clinical interpretation within Nutritional State should be traceable to supporting scientific evidence.

ClinRx AI shall preserve the relationship between:

Patient-specific Clinical Observations

↓

Clinical Interpretation

↓

Supporting Scientific Evidence

This ensures transparency, explainability, and auditability of clinical reasoning.

Future versions may reference dedicated Clinical Evidence Objects.

---

# 12. Knowledge Graph Connections

Nutritional State exists as a central node within the ClinRx Clinical Knowledge Graph.

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

Nutritional State enables ClinRx AI to:

- Assess nutritional condition
- Interpret nutritional trajectory
- Monitor longitudinal nutritional changes
- Identify nutritional deterioration
- Evaluate response to nutrition support
- Support recovery assessment
- Provide context for downstream Clinical Engines

This Knowledge Object provides context rather than recommendations.

---

# 14. Consumers

This Knowledge Object may be consumed by:

## Clinical Domains

- Nutrition & Metabolism

## Clinical Engines

- Nutrition Intelligence Engine
- ICU Clinical Reasoning Engine

## Specialty Operating Systems

- Anti-Infective OS
- ICU Operating System
- Liver Transplant Operating System

## ClinRx Flow

- AI Scribe
- Clinical Timeline
- Clinical Narrative Generator
- Clinical Handover Assistant

---

# 15. Related Knowledge Objects

## Parent Objects

None

## Peer Objects

- Metabolic State
- Functional State
- Recovery State

## Child Objects

Examples include:

- Energy Balance
- Protein Balance
- Nutrition Adequacy
- Nutrition Risk
- Nutrition Support

---

# 16. Design Intent

Nutritional State serves as the canonical representation of a patient's nutritional condition within ClinRx AI.

It separates nutritional interpretation from observations, calculations, interventions, and clinical decisions.

This separation enables reusable, explainable, longitudinal clinical reasoning across Clinical Domains, Clinical Engines, and Specialty Operating Systems.

Nutritional State is intended to serve as the foundational nutrition-related Clinical State upon which future nutrition intelligence will be constructed.

---

# Version History

## Version 1.0

Initial Clinical Knowledge Object.