# ClinRx M11 first slice — approved scope

The human user approved the general GI/liver review for implementation on 2 November, with work resumed on 4 November 2026. The candidate starts from c0c3d23 (the same source tree as merged PR27 cde32d37). The earlier two display defects are resolved. This approval covers the bounded synthetic workflow below, preserving the original preview, databases and existing modules. Mobile and native browser fault injection remain qualified verification gaps.

## Goal
One connected GI/hepatobiliary review in the shared patient workspace: source observations, liver/biliary/pancreatic laboratory results, source imaging/procedure reports and a source-bound clinician review with correction/history/reload.

## First increment
Reuse shared laboratory, medication, microbiology, imaging-report and fluid evidence. Automatically display relevant results; no reuse button or duplicate transcription. Keep individual results once in primary display, with distinct specimens/repeat studies separate. Capture source-recorded symptoms, examination and feeding tolerance without asserting a diagnosis. Share feeding-tolerance identity with future Nutrition rather than duplicate it.

Preserve patient/encounter/repository binding, exact report/component/revision/digest identity, collection/report/availability times, units, specimen, method, status, quality and uncertainty. Missing is not normal; withdrawn and conflicting findings stay qualified. Lab mapping needs explicit source-code admission, not name similarity. Imaging is report review, not image interpretation/PACS integration.

First delivery includes recorded findings and clinician-authored review only. No generated liver severity scores, diagnostic thresholds, treatment advice, dosing, automatic orders, transplant eligibility or live integrations. Later scope requires its own clinical policy and validation.

## Acceptance
A fictional patient with liver chemistry, a distinct repeat sample, abdominal report, GI observation and feeding-tolerance record can be reviewed together. Correction keeps old evidence inspectable, invalidates current matching, and permits an explicit renewed review. Reload retains exact saved support; uncertain saves require exact lookup before retry. Other modules see the same accepted record automatically. No original patient database is changed.

## Product boundary
The approved first journey is general GI/hepatobiliary review. The established same-browser review store is adequate for this synthetic increment; authenticated shared audit is required before clinical deployment. Specialist completeness is outside this bounded slice.

## Approved demo and execution decisions
General GI/liver review, current findings, shared liver/pancreatic laboratory trends, original abdominal imaging/procedure reports, patient course and one clinician review. No automatic diagnosis or treatment. Canonical laboratory concepts are explicitly admitted; unknown units retain source wording. A new gastrointestinal_record stores only original domain findings/reports, including feeding tolerance for later Nutrition reuse. Shared laboratory records are never copied into it. Existing synthetic browser review storage is reused, with exact source pins and append-only history.

Implementation baseline c0c3d23 has the same tree as merged PR27 cde32d37. The two historical display defects are resolved. Mobile remains deferred. Protected databases and original preview builds are immutable; a new isolated build/copy will be used.
