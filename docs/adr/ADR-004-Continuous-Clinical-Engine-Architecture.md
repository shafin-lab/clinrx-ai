# ADR-004 — Continuous Clinical Engine Architecture

**Status:** Accepted

**Date:** 2026-08-10

---

## Context

During Sprint 2 architectural planning, it was recognized that ClinRx AI must support multiple medical specialties while preserving a single, reusable clinical knowledge model.

Rather than building isolated applications for ICU, Liver Transplant, Emergency Medicine, Oncology, and future specialties, the platform shall implement reusable Clinical Engines that are orchestrated by Specialty Operating Systems.

This approach separates core clinical reasoning from specialty-specific workflows.

---

## Decision

ClinRx AI shall adopt a layered architecture consisting of:

1. Clinical Knowledge Standard (CAS-CDS-001)
2. Clinical Engines
3. Specialty Operating Systems

Clinical Engines shall provide reusable capabilities including:

- Clinical Context Engine
- Clinical State Engine
- Clinical Intelligence Engine

Specialty Operating Systems shall orchestrate these engines according to specialty-specific workflows without redefining the underlying clinical knowledge.

---

## Specialty Operating Systems

Specialty Operating Systems shall orchestrate multiple Clinical Engines according to specialty-specific workflows.

Examples include:

- ICU Operating System
- Liver Transplant Operating System
- Surgical Operating System
- Emergency Medicine Operating System
- Oncology Operating System

Operating Systems shall not redefine the underlying clinical knowledge model.

---

## Rationale

This architecture provides:

- Reusable clinical logic
- Consistent patient representation
- Reduced duplication
- Explainable AI outputs
- Easier extension to future specialties
- Improved maintainability

The platform remains patient-centric while allowing specialty-specific workflows to evolve independently.

---

## Consequences

Future software development shall implement reusable Clinical Engines before developing specialty-specific Operating Systems.

All future modules shall consume standardized clinical knowledge defined by CAS-CDS-001.

---

## Related Documents

- CAS-ARCH-003 — Clinical Context Engine
- CAS-ARCH-004 — Clinical State Engine
- CAS-ARCH-005 — Clinical Intelligence Engine
- CAS-CDS-001 — Clinical Knowledge Standard

---

**Architecture before implementation. Clinical integrity before automation.**