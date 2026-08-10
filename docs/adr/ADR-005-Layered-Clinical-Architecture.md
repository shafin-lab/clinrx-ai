# ADR-005 — Layered Clinical Architecture

**Status:** Accepted

**Date:** 2026-08-10

---

## Context

ClinRx AI is designed as a reusable clinical operating platform capable of supporting multiple medical specialties while maintaining a single, consistent clinical knowledge model.

As the platform expands, medical knowledge must not be duplicated across specialty-specific applications. Instead, reusable clinical knowledge should be separated from reusable clinical reasoning and from specialty-specific workflows.

A layered clinical architecture is therefore adopted.

---

## Decision

ClinRx AI shall organize its clinical architecture into three independent layers:

1. Clinical Domains
2. Clinical Engines
3. Specialty Operating Systems

Each layer has a distinct responsibility and shall remain independent of the others.

---

# Layer 1 — Clinical Domains

Clinical Domains represent reusable medical knowledge.

Examples include:

- Nutrition & Metabolism
- Hemodynamics
- Respiratory Support
- Ventilation
- Renal Function
- Acute Kidney Injury
- Liver Function
- Infection
- Sepsis
- Electrolytes
- Acid–Base Disorders
- Fluid Therapy
- Vasopressors
- Sedation
- Analgesia
- Delirium
- Coagulation
- Blood Transfusion
- Frailty
- Glycemic Control
- Antibiotic Stewardship

Clinical Domains shall remain independent of any medical specialty.

Medical knowledge shall exist only once within the platform.

---

# Layer 2 — Clinical Engines

Clinical Engines provide reusable clinical reasoning.

Examples include:

- Clinical Context Engine
- Clinical State Engine
- Clinical Intelligence Engine
- Recommendation Engine
- Validation Engine
- Safety Engine

Clinical Engines consume Clinical Domains and continuously interpret the evolving clinical state of the patient.

Clinical Engines shall not contain specialty-specific workflow logic.

---

# Layer 3 — Specialty Operating Systems

Specialty Operating Systems orchestrate Clinical Engines according to specialty-specific workflows.

Initial Operating Systems include:

- ICU Operating System
- Liver Transplant Operating System
- Nephrology Operating System
- Emergency Medicine Operating System
- Surgical Operating System
- Oncology Operating System

Additional Specialty Operating Systems may be introduced through future Architecture Decision Records without modifying the underlying Clinical Domain architecture.

---

## Architectural Principles

1. Clinical knowledge shall exist only once.
2. Clinical reasoning shall be reusable across specialties.
```