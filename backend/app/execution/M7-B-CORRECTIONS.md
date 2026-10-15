# M7-B independent-review corrections

Review baseline: `8f8cd5972ea866bc2e29bca135dbcd59704123af`.
M7-C remains gated on independent re-review. These corrections do not establish
clinical readiness or patient-care authority.

## Reproductions and fixes

The original three safe-outcome regression assertions all failed at the baseline:
F1 accepted distinct .1234561/.1234569 times as simultaneous; F2 raised AttributeError
for source-documented singleton lactate; F3 accepted a selection omitting an exact
binding-provenance dependency. Raw failing and subsequent passing logs accompany
the review package, including intermediate fixture/canonical-compatibility failures.

F1: M7 ClinicalInstant distrusts fractional seconds with discarded nonzero digits.
Six-digit microseconds and additional trailing zeroes retain their exact meaning.
Equivalent offsets continue to compare by actual instant. Newly supplied alternative
and conflicting assertion lexemes are retained as optional evidence. Absent new
fields remain omitted when decoding old canonical payloads. Old source strings
already lost before admission cannot be reconstructed. No M5/M6 RecordedTime or
integer instant comparison code changed. Canonical serialization and reopening are
tested; explicitly empty lexeme fields cannot hide supplied nonzero precision.

F2: the shared Measurement validator uses the literal expected concept `lactate`
for LactateResult and each other measurement's declared concept otherwise.
Contradictory mappings still fail. No lactate concept field, schema or payload
identity change was introduced.

F3: the M7-only support helper collects exact dependencies of provenance actually
consumed, including consumed association provenance. Assembly follows those edges
under the existing history, graph and byte limits. Inference requires the complete
explicit closure in its sorted support pins (maximum 32), then retains matching
inputs and derived_from edges. Protected execution already witnesses all pins;
no workflow, transaction or receipt producer change was needed. Missing,
wrong-scope, historical-only, unsupported or cyclic support cannot permit release.
Unrelated context/order/dosing-weight association provenance stays outside timing
inputs. Such associations may still be retained as comprehensive source context.

Limits count traversal work, including repeated shared-parent paths, not merely
unique nodes. Independently counted exact-limit/limit+1 tests cover depth, fanout,
relationships, steps, contextual items, groups, signals, issues, 64 contextual
children and 32 supporting pins. Workflow tests cover exhaustion and rollback of
both a provisional fact and the execution. A dense 32-support test now uses two
layers within the depth cap; an over-depth chain is separately rejected. Exhaustion
remains QueryLimitExceeded rather than clinical withholding. No new graph cap or
larger operational allowance was introduced.

## Historical compatibility and prepared requests

No stored facts, inferences, requests or receipts are rewritten. M7 method/workflow
identifiers, clinical contracts outside M7, Kernel v1, M5/M6 identities, schema,
migrations, dependencies, transaction poisoning/rollback and completion-unknown
semantics are unchanged. Migration head remains m7_0008.

Existing exact receipts remain historical decisions made under the old producer;
they are not retroactively certified safe by this correction. Retry/reconciliation
perform retained-only lookup first, preserve original bytes, UUID and metadata and
do not recompute or reauthorize even after correction or grant expiry. A regression
simulates an affected old producer receipt and verifies unchanged stored bytes.

Previously prepared commands without a retained receipt undergo the corrected
original-prefix replay. A command relying on lossy timing, omitted consumed support,
or an assembly digest changed by newly retained support cannot pass reconstruction:
it fails with the existing sanitized integrity error and creates no withheld or
released receipt. Do not silently add pins, substitute revisions, change its UUID,
rewrite the persisted inference, or repeat the POST automatically. An undispatched
command can be explicitly discarded and prepared anew with fresh inference and
execution identities. For an attempted or uncertain command, retain it and reconcile
its exact identity first. Absence is not proof of rollback; any same-command retry
must be explicit and still passes corrected replay. A replacement is a separately
explicit preparation, not automatic recovery. Historical affected receipts require
separate review; no automatic revocation or historical migration is implemented.

## Approved policy versus decisions pending reconciliation

The original supplied P/L/V policy is included unchanged in the review package.
The following implementation decisions are documented for explicit reconciliation;
they are not represented as verbatim approved policy or newly approved refinements:

- Terminology: the first inference currently admits five exact canonical identifiers:
  norepinephrine, epinephrine, vasopressin, phenylephrine and dopamine. Confirm this
  bounded v1 terminology scope. Broader source evidence remains persistable.
- Lactate quality: pressure requires explicitly acceptable quality. Lactate currently
  rejects invalid quality but permits unknown/suspect; the supplied policy does not
  explicitly apply the pressure quality requirement to lactate. Confirm the distinction.
- Conservative exclusions: known future availability/recording/event time, negative
  lactate concentration and contradictory arterial compartment are unsuitable. These
  fail-closed refinements need explicit reconciliation, not a claim of unsafe release.
- Calibration applicability: adequate attributed invasive calibration/zeroing is
  required, but the policy does not specify how events or retrospective attestations
  establish applicability to acquisition time. No freshness threshold, invented
  interval policy or automatic clock adjustment has been added. Confirm the intended
  applicability contract before clinical use or connected M7-C policy claims.

Under the currently supplied unit policy, raw pressure unit must be exactly `mmHg`.
An unresolved source unit is accepted as recorded; if assessed, it must additionally
identify UCUM `mm[Hg]`. A raw `mm[Hg]` spelling is unsuitable even with that code.
No spelling normalization or conversion is performed. The previous documentation's
claim that raw `mm[Hg]` was eligible was incorrect and has been removed.

## Validation evidence

The external review package identifies the exact corrected source checkpoint/tree,
separate correction commits, original policy/review, source archives, patches,
checksums, environment versions and raw commands/logs/exit codes. Python 3.11.6
is required for the backend. No hosted feature CI is claimed or triggered, and no
push, merge, deployment or connected M7-C implementation is part of this pass.

## Director R1: remaining numeric precision bypass

At a1680c4, `1791426600123456.1e-6` and `1791426600123456.4e-6`
were admitted as the same trusted instant. Numeric exactness now compares the
full Decimal value, including its exponent, to the actual parsed epoch in seconds
or milliseconds. Exact Decimal construction/comparison avoids arithmetic-context
rounding and enormous integer-ratio expansion for extreme exponents. Numeric forms
rejected by the existing datetime parser remain rejected. No normalization or unit
conversion changes that parser's admission or interpretation rules.

Lossy exponent evidence remains persistable with its original string, but cannot
establish exact inference ordering. An affected old preparation without a receipt
fails corrected reconstruction with the existing sanitized integrity error and
creates no receipt; retained history is not rewritten. The existing explicit
reconciliation/retry and separately explicit re-preparation policy above applies.
The four policy questions above remain pending, and M7-C remains gated.

## Director R2: timestamp validation boundary

Conflict containers and members are now checked with bounded Pydantic adapters
before any iteration or lexeme capture. Null/malformed containers, members and
companion-lexeme fields produce structured ValidationError results. Existing
list/tuple/iterable admission, mixed ISO/numeric/datetime values and the eight-member
cap remain supported. Valid byte strings and Decimal numeric values follow the
existing datetime admission rules as well.

String assertions preserve their original lexemes. Non-string numeric objects have
no original string lexeme; their value spelling is retained, adding a harmless `.0`
where the existing string parser requires it for scientific notation. This does not
reconstruct any wire lexeme already lost when an upstream JSON number was decoded.
New loss evidence cannot be hidden by a mixed container or explicit empty companion.
Legacy canonical JSON does not acquire optional lexeme fields on read. Round trips,
stored corruption and sanitized inference-boundary failures have regressions.

R1/R2 do not change F2/F3, exact support closure, workflow/receipt identities,
immutable stored history, shared transactions, governance, schema or dependencies.
No automatic retry/re-execution or connected M7-C work is introduced. Existing PR
#22 is the review target; no additional PR or ZIP is created in this correction pass.

A further R1 probe covered native numeric primary/alternative values. They now
retain the numeric object's value spelling as well, so precision loss cannot hide
behind a non-string input. Supported exact native values still admit and qualify;
lossy values remain retained but unsuitable. A JSON number's original wire spelling
cannot be reconstructed after decoding; callers needing that lexeme must supply it
as string evidence. Existing canonical JSON contains parsed datetime strings, so
this capture does not rewrite legacy payloads. The interrupted backend validation
log is retained; final validation is rerun against the completed correction.
