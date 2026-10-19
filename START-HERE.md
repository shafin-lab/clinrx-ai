# RF2 source identity weight assertions and reuse review

Focused documentation revision after Director's changes-required verdict on `58f85671c65c39915ddb365e79fcdaf7ec2a5c07`.

Application baseline stays `5cb73212ae6104b02bad361886cd9507795d88bf`, tree `7505ff88af8089f2d729fc230b15f3a604c5c9c0`. RF2 remains planning only, contributing to M8/M9 without renumbering. No application suite or walkthrough is needed for this wording revision.

Read:

1. [Revised specification](RF2-WORKFLOW-SPEC.md) and [focused diff](RF2-S1-S2.diff).
2. [M1 through M7 reuse audit](M1-M7-REUSE-AUDIT.md), requested by the user to prevent rebuilding existing capabilities. [Source inventory](SOURCE-INVENTORY.json) records inspected paths/hashes at the application baseline; [captured-reference summary](CAPTURED-REFERENCE-SUMMARY.json) records the reused local capture attribution.
3. [Checksums](SHA256SUMS.json). The entire seven-file previously reviewed package is preserved unchanged under reviewed-58f8567/, including its prior draft and original manifests.

RF2-S1 correction: scoped, namespaced issuer/source-record/component identity; explicit exclusion of series/context IDs; material source-content equality independent of fresh local IDs; original retained replay after correction with supersession disclosed; fail-closed ambiguity/multiple matches/budget exhaustion. RF2-02 now names each requested regression.

RF2-S2 correction: acquisition assertion, acquisition method and intended-use/purpose are independent. Dosing use cannot establish acquisition. RF2-03 covers measured-for-dosing reuse without another quantity row, separately asserted dosing value and unavailable historical acquisition.

The reuse audit distinguishes common source facts and existing infrastructure from genuine RF2 integration gaps. It is bounded source/captured-data inspection, not an exhaustive code-clone or hospital-record deduplication certification. No new live API response, runtime exercise or test result is claimed.

Request one focused S1/S2 closure verdict, plus confirmation that the reuse boundaries address the user's duplication concern. Preserve the supported parts of the prior specification and all RF1-F1/hemodynamics acceptances. Source inventory/ownership mapping and proof of bounded metadata fit remain implementation prerequisites.

Keep execution disabled. Do not implement, merge, deploy, host externally or activate execution. Approval of a specification is not implementation acceptance; obtain explicit implementation authorization separately.
