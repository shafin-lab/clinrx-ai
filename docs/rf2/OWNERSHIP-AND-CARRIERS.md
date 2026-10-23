# RF2 implementation prerequisites

Approved specification a4547e215a8c4c20bd04e807d0287c5e1d575c39; application baseline 5cb73212ae6104b02bad361886cd9507795d88bf.

## Concrete ownership map

- Creatinine: ClinicalObservation, concept synthetic-serum-creatinine; RF1 owns the raw composite/history read. RF2 references these exact originals and never writes creatinine or invokes its trend engine.
- Generic body weight: ClinicalObservation, allowlisted concept body-weight (existing recorded-weight test policy). Read/resolve only in RF2. No generic weight writer is added; corrections stay with the original owner. The current ICU episode has no populated generic body-weight observation. Existing generic weight cannot be cloned to CirculatoryEvent.
- Existing dosing weight: circulatory_event/fs-WEIGHT/1, amount 70 kg. Existing infusion delivery references retain this exact source. Acquisition is unavailable, independently of dosing purpose. Reuse adds a pin, not a quantity.
- Existing fluids: CirculatoryEvent entries under clinrx.synthetic.hemodynamic-chart/v1; categories input_iv/input_blood/output_urine/output_drain/output_crrt/net_balance_reported/urine_total_reported/balance_total_reported. Original event/interval ownership and corrections use existing repository revision admission; no copies for RF2.
- New local chart collections: CirculatoryEvent under clinrx.local.rf2/v1; categories input_oral/input_enteral/input_iv/input_blood/output_urine/output_drain/output_other/output_crrt/weight and source-reported totals/balance. Acquisition, method and intended purpose are separate metadata assertions. This is unverified synthetic source entry, not hospital interoperability.
- Renal note: CirculatoryEvent with clinrx.local.rf2/v1 category note and independently encoded exact evidence pins. Existing hemodynamic notes and saved v1 remain unchanged.
- Medication/antimicrobial/vasoactive facts remain owned by M5/M6/M7. RF2 does not recreate orders/administrations or infer medication carrier volumes.

## Source-record replay

Within the repository/patient/encounter, source key = issuer_namespace + issuer + record_namespace + record_id + component. A concrete component is mandatory. No whole-record issuer profile is configured in this bounded local implementation; whole-record/collection/series/context component assertions are rejected rather than treated as record identity. Series/context namespaces are not allowed as record namespaces; infusion series/pump/channel identifiers are never extracted as record IDs. No real issuer integration is asserted. Optional source_version remains material content, not permission to create another measurement chain.

Material projection is the complete validated chart DTO: category, exact decimal string/raw unit or missing reason, point and interval assertions, acquisition/method/purpose, collection/site context, source key/version and uncertainty. Only generated local fact/revision/request identity, local actor/registration time and correction bookkeeping are outside this projection. No numeric tolerance or conversion. Provenance originating in the source must be placed in source_context, which is included. Original source replay resolves historical material content; returns that exact retained revision with current terminal reference/supersession disclosure. Different content requires explicit correction. Ambiguity or any history/aggregate budget failure never permits insertion.

No-key manual entry requires a new_collection_reason and visible possible-duplicate disclosure; it cannot override a conflict on a claimed key. Uncertain command lookup/retry always preserves the full original draft separately from source replay.

## Existing carrier proof before application changes

Existing CirculatoryEvent admits 32 external_evidence entries and 32 associations. Use one RF2 metadata entry plus at most twelve separate pin entries (13/32); pins have twelve associations (12/32). Enforce each encoded metadata/pin <=4096 UTF-8 bytes, narrative <=4096 characters, incoming DTO <=65536 bytes, shared response cap unchanged at 2097152 bytes. Strict schemas further restrict identifier/text lengths. The pre-implementation probe built a maximal 4096-character narrative with twelve conservatively sized pins and source identity metadata through the unchanged model: 31156 serialized bytes, largest metadata entry 988 bytes. No model, migration or limit changes are needed. Runtime admission and shared history accounting still reject over-budget responses; this proof does not waive those checks.

Historical source records outside the local entry profile remain inspectable and cannot be silently converted by the guided form. Corrections of original legacy event amounts preserve other fields and do not promote prose into typed acquisition context. No generic clinical contract, production route or execution policy is extended.

## F3 review-decision carrier extension within existing bounds

The original 13-entry preflight above remains historical prerequisite evidence. The corrected note workflow uses up to twelve additional review-decision entries under clinrx.local.rf2.review/v1, for 25/32 external entries and 12/32 associations. The current strict twelve-pin/review probe reports 49,611 fact bytes, 27,560 request bytes and largest entry 2,672 bytes. All original caps and clinical/storage models remain unchanged. Older notes and original request bytes do not gain a default review declaration. See F1-F3-CORRECTIONS.md.
