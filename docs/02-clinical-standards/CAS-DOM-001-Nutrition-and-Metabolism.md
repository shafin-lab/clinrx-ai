# CAS-DOM-001 — Nutrition & Metabolism

**Document ID:** CAS-DOM-001

**Version:** 1.0 (Draft)

**Status:** In Development

**Owner:** ClinRx AI Clinical Architecture

---

# Clinical Philosophy

Nutrition in critical illness is not a static calculation but a continuous clinical process reflecting the interaction between metabolism, inflammation, organ function, therapeutic interventions, and recovery.

The objective of this Clinical Domain is not to calculate calorie or protein targets alone, but to continuously interpret the patient's metabolic state and generate explainable, evidence-supported clinical reasoning throughout the patient's clinical journey.

ClinRx AI therefore represents Nutrition & Metabolism as a dynamic clinical state rather than a fixed prescription.

---

# Purpose

The Nutrition & Metabolism Clinical Domain provides a standardized representation of nutritional medicine for ClinRx AI.

It continuously integrates clinical observations, physiological changes, therapeutic interventions, and evidence-based nutritional principles to derive the patient's current metabolic state.

The domain supports clinician decision-making by:

- interpreting nutritional status,
- estimating energy and protein requirements,
- identifying nutrition-related risks,
- monitoring metabolic progression,
- recognizing changing clinical phenotypes,
- generating explainable clinical narratives.

This Clinical Domain is reusable across every Specialty Operating System within ClinRx AI.

---

# Scope

## Included

This Clinical Domain includes:

- Nutritional assessment
- Metabolic assessment
- Energy expenditure
- Protein metabolism
- Micronutrient considerations
- Fluid-related nutritional reasoning
- Enteral nutrition
- Parenteral nutrition
- Mixed nutritional support
- Feeding tolerance
- Refeeding syndrome
- Nutrition-related safety
- Continuous nutritional monitoring
- Clinical phenotype recognition
- Evidence-supported nutritional reasoning

---

## Excluded

The following are intentionally excluded and belong to separate Clinical Domains:

- Hemodynamic management
- Mechanical ventilation management
- Renal replacement therapy management
- Infection management
- Antimicrobial therapy
- Coagulation management
- Sedation management
- Endocrine disorders unrelated to nutritional metabolism

These domains interact with Nutrition & Metabolism but remain independently governed.

---

# Domain Objectives

The Nutrition & Metabolism Domain shall:

- Continuously represent the patient's nutritional state.
- Continuously represent the patient's metabolic state.
- Identify clinically relevant nutritional phenotypes.
- Integrate observations from multiple organ systems.
- Apply evidence-supported nutritional reasoning.
- Identify nutrition-related risks.
- Generate standardized structured outputs.
- Produce clinician-readable nutritional narratives.
- Support clinician decision-making without replacing clinical judgement.

---

# Architectural Principles

The Nutrition & Metabolism Domain shall:

- remain patient-centric,
- remain evidence-based,
- remain continuously updated,
- remain explainable,
- remain implementation-independent,
- remain reusable across specialties.

Clinical reasoning shall always precede numerical calculations.

Patient safety shall always take precedence over automation.

Clinical judgement shall always remain the final decision-maker.

---

**Clinical knowledge before implementation. Clinical reasoning before automation.**