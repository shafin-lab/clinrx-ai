# ADR-003: Clinical Knowledge Standard

## Status

Accepted

---

## Date

2026-08-10

---

## Context

During Sprint 2 planning and architectural review, the scope and purpose of CAS-CDS-001 were evaluated.

The initial working title, **Clinical Data Standard**, implied an implementation-focused specification describing how information should be stored or exchanged.

However, the primary objective of CAS-CDS-001 is to define the conceptual representation of clinical knowledge within ClinRx AI, independent of any database, programming language, or software implementation.

---

## Decision

The official document title shall be:

**CAS-CDS-001 — Clinical Knowledge Standard**

The document identifier remains unchanged:

**CAS-CDS-001**

---

## Scope

CAS-CDS-001 answers one fundamental architectural question:

> **How should ClinRx AI represent clinical knowledge internally?**

The document defines the conceptual model used by the platform and is intentionally independent of implementation details, including:

- Database schema
- API contracts
- User interface
- AI models
- Programming language
- Storage engine
- Infrastructure

---

## Rationale

Clinical knowledge is broader than data structures.

The purpose of CAS-CDS-001 is to establish a stable conceptual foundation describing:

- Clinical concepts
- Relationships between concepts
- Clinical context
- Temporal behavior of clinical information
- Evidence and traceability
- Clinical meaning

Technical implementation belongs to subsequent architecture documents and engineering specifications.

---

## Consequences

All future implementation documents—including database design, APIs, AI engines, user interfaces, and infrastructure
```