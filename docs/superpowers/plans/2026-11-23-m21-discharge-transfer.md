# M21 Discharge and Transfer Implementation Plan

> Execute inline with superpowers:executing-plans and a final independent review.

Goal — implement the approved M21 patient workflow and prove transfer/home review persistence and evidence-change flags.
Architecture — additive DischargeRecord source contract, existing catalog assembly and source-pinned browser reviews, existing patient navigation and overview. Shared evidence remains original and source-linked.
Tech stack — existing Python/Pydantic/SQLite/Alembic and React/TypeScript.
Spec — docs/m21-discharge/DESIGN.md.

## Constraints

Preserve prior previews, patient data, and synced sources. Isolate demonstration writes. Keep transition records distinct from actual medication orders and administrations. Represent unavailable or conflicting evidence explicitly.

## Review focus

Cross-transition reviews, future corrections, incomplete retrieval, stale queued saves, and medication/history identity must be tested or reviewed.

## Tasks

- [x] Add DischargeRecord, additive migration and catalog decoding. Test both transition types, corrections and historical cutoff retrieval with original revision resolution.
- [x] Add four-view workspace, overview summary, automatic shared evidence including microbiology and devices, and original-source inspection. Use transition-specific identity and confirm review persistence, changed evidence and scope failure tests.
- [x] Populate disposable transfer and home cases, save reviews through UI, reload, correct relevant evidence and verify flags in both views. Preserve baseline hashes and record verification.
- [x] Independent whole-branch review, resolve material findings, run relevant suites, typecheck, build and whitespace checks. Commit local checkpoint and report precise limits.
