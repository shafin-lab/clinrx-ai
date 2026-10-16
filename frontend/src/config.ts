// Defaults copied from the checked-in app.demo.patient_state.manifest (v1).
export const demo = {
  patient: import.meta.env.VITE_PATIENT_ID || 'synthetic-p1',
  encounter: import.meta.env.VITE_ENCOUNTER_ID || 'synthetic-e1',
  start: import.meta.env.VITE_REVIEW_START || '2026-10-08T08:00:00+00:00',
  end: import.meta.env.VITE_REVIEW_END || '2026-10-08T10:00:00+00:00',
  releasedExample: import.meta.env.VITE_RELEASED_EXAMPLE || '00000000-0000-4000-8000-00000000c901',
  withheldExample: import.meta.env.VITE_WITHHELD_EXAMPLE || '00000000-0000-4000-8000-00000000c902',
  base: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
};
