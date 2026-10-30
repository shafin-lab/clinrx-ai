# Antibiotic profiles in the main ClinRx workspace

The expanded antibiotic reference belongs in the full multi-system ClinRx application, alongside the existing cardiovascular, renal, respiratory and hematologic work.

Open **Antimicrobials → Reference library → Antibiotics**. **Infections & treatment** remains alongside it and retains the NCDC infection guidance and supplementary evidence unchanged.

Current reviewed preview:
http://127.0.0.1:5253/?workspace=antibiotics&antibioticView=library&reviewBuild=main-antibiotic-profiles-20261029

The 94 imported profiles provide Overview, Uses & spectrum, Dosing, PK/PD, Safety, Administration & monitoring, and References. The profile collection loads when first opened and remains mounted when switching collections. Imported records remain draft references with their source conditions, provenance and gaps; they do not alter prescriptions or drive patient dose suggestions.

Source entry: frontend/src/antibiotics/AntibioticReferences.tsx. New components: frontend/src/profiles/. Attributed dataset: frontend/src/data/antibiotic-profiles.json, SHA256 a8a42756c4bba66f58cd46bf0b4296ccf6420a91a5083ba316f0a6d7574bb1e4. Do not edit imported content without updating its provenance.

Verification: full frontend suite 1,739 passed / three skipped; production build and typecheck passed; 16 focused tests and typecheck passed again on 30 October 2026. Independent source review reported no actionable findings. Desktop workflow was checked within the full app. Final resumed full run with two workers also passed 1,739 tests with three skipped. A prior four-worker run had one cardiac-output inspector timing failure, which passed unchanged in isolation and in the final full run. The final scoped style correction restores valid panel colours after production CSS transformation and top-aligns profiles; independent follow-up review reported no actionable findings. Mobile checks remain deferred.

All 210 protected files, including four patient databases, match their baseline hashes. The existing frontend preview was updated while keeping previous assets and an archived build; no patient record, backend source, clinical-module source, renal dose engine or NCDC content was changed.

Detailed local evidence, review, preservation manifests, deployment metadata and rollback archive: review-evidence/main-antibiotic-profiles-20261029/. The earlier standalone and MagicPath antibiotic editions remain preserved; they are not the authoritative main-app integration target.
