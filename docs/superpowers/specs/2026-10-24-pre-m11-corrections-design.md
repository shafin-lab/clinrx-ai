# Pre-M11 correction checkpoint — 24 October 2026

The user requested a fresh assessment and necessary corrections before M11. This is the bounded correction pass from the preceding assessment, not new clinical-module development.

## Approach and scope
Continue the preserved connected candidate and its existing React/TypeScript patterns. A restart would discard integration; a broad redesign or server-review migration would enlarge this pass. Make presentation/navigation corrections at their current owners, then independently review one fixed checkpoint. The user has already authorised the corrections; no new treatment capability is introduced.

1. Route legacy ABG/pulse-oximetry findings to Respiratory and haemoglobin/coagulation findings to Hematologic in overview, before generic circulatory source-kind matching. Keep each original record and source link; classify laboratory findings by their component label rather than the whole panel's labels.
2. Suppress the dimensionless unit code `1` in bedside evidence text, retaining original source bytes and other units.
3. Start M10 clinical setting as unknown/unconfirmed, including the transmitted context. Distinguish no quantified evidence, reconciled recorded entries and unresolved recorded subtotals; none certifies complete patient exposure.
4. Keep workspace URLs aligned with successful internal navigation, preserve other query parameters/hash, support reload into the selected enabled view, and do not allow history navigation to bypass protected pending drafts.
5. Update only investigation catalog presentation associations to the final M1–M21 roadmap. Do not rename records, migrations, persisted review domains or source identifiers.

## Preservation and exclusions
Existing original and candidate previews/assets/databases stay untouched. Use new immutable build assets and a disposable database copy only for verification; no write to existing patient records or browser review stores. Preserve the existing uncommitted roadmap documentation. Sources/ remains read-only. Mobile checks remain deferred. Clinical execution and M7-C remain gated. Full shared Labs/Imaging, server-side clinical review storage, comprehensive respiratory/transfusion redesign and M11 are separate milestones.

## Acceptance
Regressions first reproduce each defect, then pass with the minimal correction. Full frontend suite, typecheck and seven-flag production build must pass on the final source. Use an independent reviewer after freezing source; check the real read-only browser workflow on an isolated preview if the browser is available. Compare protected database/reference hashes before and after. The current GitHub baseline is merged PR24 / head07859c8, with hosted frontend/backend success; do not confuse this with tests for these new changes.
