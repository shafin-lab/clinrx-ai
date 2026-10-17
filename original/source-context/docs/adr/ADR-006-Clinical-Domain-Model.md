# ADR-006 — Clinical Domain Model

**Status:** Accepted

**Date:** 2026-08-10

---

## Context

ClinRx AI organizes medical knowledge into reusable Clinical Domains.

As the number of Clinical Domains grows, each domain must follow a common conceptual structure to ensure consistency, interoperability, maintainability, and reuse across Clinical Engines and Specialty Operating Systems.

Without a common model, domains would evolve independently, leading to duplication, inconsistent reasoning, and incompatible interfaces.

---

## Decision

Every Clinical Domain within ClinRx AI shall conform to a standardized Clinical Domain Model.

A Clinical Domain represents a self-contained body of medical knowledge responsible for describing one aspect of patient care.

Clinical Domains are independent of:

- User Interface
- Database implementation
- Programming language
- API design
- AI implementation
- Specialty-specific workflow

---

# Responsibilities of a Clinical Domain

Every Clinical Domain shall define:

## 1. Purpose

The clinical problem addressed by the domain.

---

## 2. Scope

What is included and excluded.

---

## 3. Core Clinical Concepts

Definitions and terminology.

Examples:

- Shock
- Frailty
- Malnutrition
- Acute Kidney Injury

---

## 4. Clinical Observations

The raw observations required by the domain.

Examples:

- Vital signs
- Laboratory results
- Physical examination
- Imaging
- Monitoring data

---

## 5. Derived Clinical State

The domain's interpretation of available observations.

Examples:

- Stable
- Improving
- Worsening
- High nutritional risk
- Stage 2 AKI

---

## 6. Calculations and Scores

Validated clinical equations and scoring systems.

Examples:

- SOFA
- MELD
- KDIGO
- Clinical Frailty Scale
- Harris-Benedict Equation

---

## 7. Risk Assessment

Known complications, progression, and prognostic indicators.

---

## 8. Evidence Base

The supporting literature, guidelines, consensus statements, and institutional protocols.

Every recommendation shall be traceable to evidence.

---

## 9. Safety Considerations

Clinical limitations, contraindications, uncertainty, and situations requiring clinician review.

---

## 10. Outputs

Every Clinical Domain shall expose structured outputs that may be consumed by Clinical Engines.

Outputs may include:

- Clinical State
- Derived Calculations
- Risk Indicators
- Evidence References
- Confidence Level
- Safety Alerts

---

# Architectural Principles

1. A Clinical Domain represents medical knowledge, not workflow.
2. Clinical Domains shall remain reusable across specialties.
3. Clinical Domains shall not contain user-interface logic.
4. Clinical Domains shall not contain database implementation details.
5. Clinical Domains shall remain independent of individual Clinical Engines.
6. Clinical Domains shall remain patient-centric.

---

## Rationale

Standardizing the Clinical Domain Model ensures that every future domain follows the same conceptual structure regardless of specialty.

This enables:

- Reusable medical knowledge
- Consistent reasoning
- Explainable AI
- Easier maintenance
- Future interoperability
- Independent evolution of Clinical Engines and Specialty Operating Systems

---

## Consequences

All future Clinical Domain Specifications shall conform to this model.

Examples include:

- CAS-DOM-001 — Nutrition & Metabolism
- CAS-DOM-002 — Hemodynamics
- CAS-DOM-003 — Renal Function & Acute Kidney Injury
- CAS-DOM-004 — Respiratory Support & Mechanical Ventilation
- CAS-DOM-005 — Infection & Sepsis

Additional Clinical Domains shall follow the same structure.

---

## Related Documents

- CAS-CDS-001 — Clinical Knowledge Standard
- ADR-003 — Clinical Knowledge Standard
- ADR-004 — Continuous Clinical Engine Architecture
- ADR-005 — Layered Clinical Architecture

---

## Vision Statement

Every Clinical Domain shall provide a standardized, reusable representation of one aspect of medicine, enabling ClinRx AI to scale across specialties while maintaining a single, coherent clinical knowledge model.

---

**Architecture before implementation. Clinical integrity before automation.**