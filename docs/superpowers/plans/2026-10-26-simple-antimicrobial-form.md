# Simple Antimicrobial Form Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, TDD and one fresh fixed-checkpoint reviewer.

**Goal:** Apply the approved four-field form without altering clinical data or review semantics.
**Architecture:** Adapt the existing editor and compatible manual chart DTO; retain exact old serialization and recovery. Optional details compose a validated schedule.
**Tech Stack:** React/TypeScript, Pydantic, existing loopback preview.
**Spec:** docs/superpowers/specs/2026-10-26-simple-antimicrobial-form-design.md

## Global constraints
Preserve sources/, original databases, open browser drafts, previous assets, source provenance, saved reviews, prescribed-vs-given separation and explicit validate/review/save. No profile changes. Mobile deferred.

## Tasks
- [ ] 1. RED→GREEN backend optional preparation/basis and prescription detail coherence/legacy exact serialization; regenerate transport. Tests: tests/test_antibiotic_chart.py.
- [ ] 2. RED→GREEN combined dose parser, frequency custom fallback, timezone adapter; implement simpler editor and migrate existing user-facing tests. Tests: simpleAntimicrobialForm, antibioticWorkflow, antibioticCorrections, prescriptionChart.
- [ ] 3. Full frontend/backend suites, typecheck/build; one independent reviewer at code checkpoint. Fix material findings with regressions. Copy-only browser save/recovery/history and preservation verification.
- [ ] 4. Archive existing builds, publish compatible assets/backend to existing ports without data migration; open a fresh preview tab and record handoff.

## Review focus
- Missing preparation must remain unknown; linked administrations must preserve exact source product identity.
- Unsupported dose text must not silently assume units or numeric amount; given/non-delivery remain separate.
- Corrections preserve source-owned basis, candidate receipts, custom frequency and exact pending recovery.
- Local date/time conversion must preserve instants including DST-invalid entries and unchanged legacy seconds.
- Optional detail text must roundtrip without duplicate append or schedule disagreement.

## Ledger
Baseline 2135531; existing feature checkout reused, only untracked frontend/node_modules present. Explicit implement approval covers the demonstrated design; no additional approval gate needed. Task 1 DTO consumed by Task 2 editor and transport; optional fields must be omitted on legacy requests to preserve canonical receipts. Task 3 consumes Task 1/2 release; no original patient writes.
