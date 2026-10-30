# Global infection search

User-requested design: move Find an infection above Clinical group and search the entire library regardless of the selected group. Keep grouped browsing for an empty query; show group names on search results and explicitly label results as spanning all groups. Clicking a result updates the browse-group selection; changing the group clears search, as before. Preserve NCDC, supplementary reference content, original preview and all patient stores.

Implementation: change only selection/filtering and navigation markup in `CompleteNcdcLibrary.tsx`; add `globalInfectionSearch.test.tsx`. No dependencies, API, source or database changes.

- [x] Observe regression failures for cross-group names, multi-group context matches and control ordering; exact cystitis versus substring match also observed RED.
- [x] Implement global matching, exact-name priority and group-labelled results, preserving context clearing.
- [x] Focused20tests passed; full frontend1,568passed/three existing skips. Typecheck/build and desktop-browser search/group checks passed; preservation manifest verified.
- [x] Published source checkpoint `ac67462` at existing candidate origin5247 with prior build retained; original5246 unchanged.

Verification focus: no duplicates; accurate group count versus global-search count; case/whitespace normalization; no stale treatment/supplement after unmatched search; selecting a group clears global search. This is a small navigation correction implementing the user's explicit design, not a change to clinical guidance.

Desktop verified Bronchitis while Cardiovascular Syndromes remained selected, result group labels, Cystitis exact-name priority and group selection clearing the query. The preview is left on that bronchitis example. Screenshot and RED/GREEN/full-suite/typecheck/build logs: `review-evidence/infection-library/global-search-20261025/`.

Final preservation:389baseline files unchanged; only the candidate index was intentionally replaced after adding new hashed assets. Previous candidate index/full build retained in `previous-build/`. NCDC JSON/PDF/figures, supplementary catalogue, original5246assets and signing material remain unchanged. Both patient databases retain SHA256 `cb3d6abdad8b3f91fd32a1eeca7890917e8cfb08c34f5fbcceae0283a22c0b14`, integrity ok,209fact revisions/four command rows. No patient entries saved. Mobile checks remain deferred. No backend changes or migrations.
