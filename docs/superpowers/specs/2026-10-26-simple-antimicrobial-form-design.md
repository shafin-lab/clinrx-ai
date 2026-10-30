# Simple antimicrobial entry

Approved in conversation: implement the demonstrated form. Primary fields are Antimicrobial, Dose per administration (amount + unit in one box), Route and Frequency. Preparation is optional and collapsed. Additional prescription details hold duration/review wording, administration instructions and indication. Keep record type, a normal date/time picker, source attribution and the existing validate/review/save and exact-recovery flow. Source identifiers remain available under Source details. No repeated clinical review or inferred prescriptions.

## Approach
Retain the current manual record editor and append-only backend. Add a small presentation adapter for combined dose, known frequency choices with an exact custom fallback, and local date/time conversion. Optional prescription detail metadata retains separate fields and composes the human-readable schedule; validate their agreement server-side. Existing requests without this metadata serialize exactly as before. Empty preparation becomes an explicitly absent formulation; no fabricated product or component basis. Existing source details and candidate review provenance must survive corrections. Keep prior guards and no-dose non-delivery semantics.

Alternative: a new editor/backend would duplicate existing recovery and audit behavior; rejected. Mandatory preparation/three separate medicine boxes was rejected by the user.

## Boundaries
No sources/, dosing profiles, NCDC, shared dose review, age/DOB model or original patient database changes. The age-only context proposal is separate from the approved prescription demo. Preserve all preview builds and browser drafts; publish additive assets without forcing open tabs to reload. New optional metadata only for prescriptions, never administrations. Date picker records the source prescription/event time, not an invented treatment start. Local timezone is labelled. Mobile deferred.
