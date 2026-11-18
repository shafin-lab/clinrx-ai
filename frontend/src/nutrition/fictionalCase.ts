export const scope = {domain:"M17",patient:"synthetic-m17-p1",encounter:"synthetic-m17-e1",repository:"m17-fictional-nutrition"} as const;
export const records = {
  dietitian: ['Dietitian assessment · NUT-171410 · Revision 1', '17 Nov 2026, 14:10 IST. Reduced intake by patient report. Current measured weight 74 kg with oedema documented. Dietitian used reported pre-admission weight 70 kg with factors of 25–30 kcal/kg/day and 1.2–1.5 g protein/kg/day to record targets of 1,750–2,100 kcal/day and 84–105 g protein/day.'],
  order: ['Nutrition order · EN-161530 · Revision 1', 'Order recorded 16 Nov, 15:30 IST. Window totals from the active formula order: 1,200 mL enteral formula at 1.5 kcal/mL and 0.075 g protein/mL. Oral intake deferred pending swallow review. No parenteral nutrition order in this encounter.'],
  intake: ['Nutrition intake chart · IN-180600 · Revision 1', '17 Nov 06:00 to 18 Nov 06:00 IST. Prescribed 1,200 mL formula. Delivered 920 mL, equivalent to 1,380 kcal and 69 g protein using the order composition. No oral intake or parenteral nutrition administration recorded.'],
  nursing: ['Nursing record · NS-180530 · Revision 1', '17 Nov: enteral feed paused at 18:00 for imaging and restarted at 22:00. 18 Nov 05:30: no emesis documented overnight, abdomen soft. Swallow assessment remains pending.'],
  lab: ['Electrolyte report · LAB-180500 · Final · Revision 1', '18 Nov 2026, specimen collected 05:00 IST and verified 05:45 IST. Phosphate 0.72 mmol/L, magnesium 0.80 mmol/L, potassium 3.8 mmol/L.'],
  review: ['Dietitian review · REV-180910 · Revision 1', '18 Nov, 09:10 IST. Mira Desai documented delivery below prescription. At the 16:00 reassessment, reconcile post-restart delivery, check repeat electrolytes and follow swallow assessment status.']
} as const;
export const tabs = {"overview": "Overview", "assessment": "Assessment & targets", "delivery": "Support & intake", "review": "Tolerance & review"} as const;
